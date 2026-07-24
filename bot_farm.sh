#!/bin/bash
# Granja de bots - Lanza N bots en paralelo

NUM_BOTS=${1:-5}
MODE=${2:-clear}

echo "[*] Lanzando $NUM_BOTS bots en modo $MODE..."

for i in $(seq 1 $NUM_BOTS); do
    if [ "$MODE" == "stealth" ]; then
        python3 bot/bot_stealth.py > logs/bot_${i}.log 2>&1 &
    else
        python3 bot/bot_clear.py > logs/bot_${i}.log 2>&1 &
    fi
    echo "[+] Bot $i iniciado (PID: $!)"
    sleep 1
done

echo "[*] $NUM_BOTS bots ejecutandose en segundo plano"
echo "[*] Logs en: ./logs/"
EOF
