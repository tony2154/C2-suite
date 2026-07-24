#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd bot
echo "[*] Iniciando Bot CLEAR..."
python3 bot_clear.py
EOF
