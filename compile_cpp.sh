#!/bin/bash
cd "$(dirname "$0")/bot/bot_cpp"
echo "[*] Compilando bot C++..."
make clean 2>/dev/null || true
make
echo "[+] Compilacion completada"
EOF
