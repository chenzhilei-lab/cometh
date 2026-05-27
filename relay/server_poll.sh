#!/bin/bash
# GitHub Command Relay — Polling Daemon (runs on 3090 server)
# Usage: nohup bash relay/server_poll.sh &
# Reads relay/cmd_queue.txt, executes new commands, pushes results to GitHub.

REPO_DIR="/root/sj-tmp/cometh-relay"
QUEUE_FILE="$REPO_DIR/relay/cmd_queue.txt"
LOG_DIR="$REPO_DIR/relay/log"
DONE_FILE="$REPO_DIR/relay/.last_done"
INTERVAL=30  # seconds between polls

mkdir -p "$LOG_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Relay daemon started. Polling every ${INTERVAL}s."

while true; do
    cd "$REPO_DIR" || { echo "ERROR: cannot cd to $REPO_DIR"; sleep $INTERVAL; continue; }

    git pull origin main -q 2>/dev/null

    if [ ! -f "$QUEUE_FILE" ]; then
        sleep $INTERVAL
        continue
    fi

    touch "$DONE_FILE"

    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" == \#* ]] && continue

        # Parse: [TIMESTAMP] CMD_ID | command
        body="${line#*\] }"
        cmd_id="${body%% | *}"
        cmd="${body#* | }"

        if [ -z "$cmd_id" ] || [ -z "$cmd" ]; then
            continue
        fi

        # Skip if already executed
        if grep -qFx "$cmd_id" "$DONE_FILE"; then
            continue
        fi

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Executing: $cmd_id"
        logfile="$LOG_DIR/${cmd_id}.log"
        {
            echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
            echo "=== Command: $cmd ==="
            bash -c "$cmd" 2>&1
            echo "=== EXIT: $? ==="
        } > "$logfile" 2>&1

        echo "$cmd_id" >> "$DONE_FILE"
    done < "$QUEUE_FILE"

    # Push results back
    git add relay/log/ relay/.last_done 2>/dev/null
    git commit -m "relay: $cmd_id done" 2>/dev/null
    git push origin main -q 2>/dev/null

    sleep $INTERVAL
done
