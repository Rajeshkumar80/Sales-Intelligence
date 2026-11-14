#!/usr/bin/env bash
# Start FastAPI on 127.0.0.1:8000, detached from this WSL session.
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"
ROOT="$HOME/BDA-Projects/sales-intelligence"
LOG_DIR="$BDA_HOME/infra/logs/app"
RUN_DIR="$BDA_HOME/infra/run"
PID_FILE="$RUN_DIR/sales-backend.pid"
mkdir -p "$LOG_DIR" "$RUN_DIR"

if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/8000' 2>/dev/null; then
  echo "Backend already listening on http://127.0.0.1:8000"
  exit 0
fi
if [ ! -x "$BDA_HOME/.venv/bin/uvicorn" ]; then
  echo "ERROR: $BDA_HOME/.venv/bin/uvicorn not found" >&2
  exit 1
fi

cd "$ROOT/backend"
setsid nohup "$BDA_HOME/.venv/bin/uvicorn" app.main:app \
  --host 127.0.0.1 --port 8000 --workers 1 \
  > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$PID_FILE"

for _ in $(seq 1 40); do
  if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/8000' 2>/dev/null; then
    echo "Backend: http://127.0.0.1:8000  (docs /docs, health /api/health)"
    exit 0
  fi
  sleep 1
done

echo "ERROR: backend did not start; last log lines:" >&2
tail -30 "$LOG_DIR/backend.log" >&2
exit 1
