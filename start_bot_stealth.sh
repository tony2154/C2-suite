#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd bot
echo "[*] Iniciando Bot STEALTH..."
echo "[*] Python: $(which python3)"
echo "[*] Directorio: $(pwd)"
python3 -u bot_stealth.py 2>&1 | tee /tmp/bot_stealth.log
echo "[*] Bot terminó con código: ${PIPESTATUS[0]}"
