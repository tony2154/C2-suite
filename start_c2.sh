#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd c2_server
echo "[*] Iniciando ShadowC2 Server..."
echo "[*] Panel: http://localhost:8000"
python3 app.py
EOF
