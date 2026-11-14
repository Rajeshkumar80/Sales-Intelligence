#!/usr/bin/env bash
# Start the Vite dev server on 127.0.0.1:5173, detached from this WSL session.
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"
ROOT="$HOME/BDA-Projects/sales-intelligence"
LOG_DIR="$BDA_HOME/infra/logs/app"
RUN_DIR="$BDA_HOME/infra/run"
PID_FILE="$RUN_DIR/sales-frontend.pid"
mkdir -p "$LOG_DIR" "$RUN_DIR"

if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5173' 2>/dev/null; then
  echo "Frontend already listening on http://127.0.0.1:5173"
  exit 0
fi
if [ ! -f "$ROOT/frontend/node_modules/vite/bin/vite.js" ]; then
  echo "ERROR: frontend dependencies missing. Run: cd $ROOT/frontend && npm install" >&2
  exit 1
fi

cd "$ROOT/frontend"
setsid nohup node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 \
  > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$PID_FILE"

for _ in $(seq 1 30); do
  if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5173' 2>/dev/null; then
    echo "Frontend: http://127.0.0.1:5173"
    exit 0
  fi
  sleep 1
done

echo "ERROR: frontend did not start; last log lines:" >&2
tail -30 "$LOG_DIR/frontend.log" >&2
exit 1
