#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$SKILL_DIR/server.pid"
LOG_FILE="$SKILL_DIR/server.log"

if [[ "${1:-}" == "--restart" ]]; then
  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
  pkill -f "$SKILL_DIR/server.py" 2>/dev/null || true
  sleep 1
fi

if ! curl -sf "http://127.0.0.1:4200/" >/dev/null 2>&1; then
  nohup python "$SKILL_DIR/server.py" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  for _ in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:4200/" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi
