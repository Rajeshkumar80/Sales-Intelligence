#!/usr/bin/env bash
# Restart HiveServer2 (config changes require a restart).
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

if [ -f "$HIVE_PID_DIR/hiveserver2.pid" ]; then
  pid=$(cat "$HIVE_PID_DIR/hiveserver2.pid")
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$HIVE_PID_DIR/hiveserver2.pid"
fi
pkill -f 'org.apache.hive.service.server.HiveServer2' 2>/dev/null || true
echo "HiveServer2 stopped"
