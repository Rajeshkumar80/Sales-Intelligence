#!/usr/bin/env bash
# Stop the dashboard processes started by start-backend.sh / start-frontend.sh.
# Hadoop, YARN and Hive are stopped separately with infra/scripts/stop-hive.sh
# and infra/scripts/stop-hadoop.sh.
set -uo pipefail
. "$HOME/BDA-Projects/infra/env.sh"
RUN_DIR="$BDA_HOME/infra/run"

stop_one() {
  local label="$1" file="$2"
  if [ ! -f "$file" ]; then
    echo "$label: no pid file"
    return
  fi
  local pid
  pid="$(cat "$file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    echo "$label: stopped (pid $pid)"
  else
    echo "$label: stale pid file"
  fi
  rm -f "$file"
}

stop_one "Backend" "$RUN_DIR/sales-backend.pid"
stop_one "Frontend" "$RUN_DIR/sales-frontend.pid"
echo STOP_APPS_OK
