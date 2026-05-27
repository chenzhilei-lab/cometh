#!/bin/bash
set -euo pipefail

# === COMETH Training Monitor (runs on 3090 server) ===
# Keeps CNN/PINN training alive, auto-restarts on crash.
# Usage: nohup bash monitor.sh &

PROC_KEY="python.*train.py"
START_CMD="cd /root/sj-tmp/cometh && nohup python3 train.py > /root/sj-tmp/cometh/train_cnn.log 2>&1 &"
LOG_FILE="/root/sj-tmp/cometh/monitor.log"
INTERVAL=10
MAX_RESTART=5
COOLDOWN=30

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

is_running() {
    pgrep -f "$PROC_KEY" | grep -vE 'grep|monitor' >/dev/null 2>&1
}

restart_count=0

log "===== Monitor started ====="
log "Match: $PROC_KEY"
log "Restart: $START_CMD"

while true; do
    if is_running; then
        restart_count=0
        pids=$(pgrep -f "$PROC_KEY" | grep -vE 'grep|monitor' | tr '\n' ' ')
        log "OK PID: $pids"
    else
        restart_count=$((restart_count + 1))
        log "DOWN ($restart_count/$MAX_RESTART)"

        if [ $restart_count -gt $MAX_RESTART ]; then
            log "FATAL: max restart reached, manual intervention needed"
            exit 1
        fi

        log "Restarting..."
        bash -c "$START_CMD"
        log "Restarted, cooldown ${COOLDOWN}s"
        sleep $COOLDOWN
    fi
    sleep $INTERVAL
done
