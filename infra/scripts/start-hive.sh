#!/usr/bin/env bash
# Start HiveServer2 and apply the idempotent DDL.
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

mkdir -p "$HIVE_LOG_DIR" "$HIVE_PID_DIR" \
  "$BDA_HOME/infra/data/hive/scratch" "$BDA_HOME/infra/data/hive/resources"

if hdfs dfs -ls / >/dev/null 2>&1; then
  hdfs dfs -mkdir -p /user/hive/warehouse /tmp/hive
  hdfs dfs -chmod 777 /user/hive/warehouse /tmp/hive
else
  echo "ERROR: HDFS is not running. Start Hadoop first." >&2
  exit 1
fi

if [ -f "$HIVE_PID_DIR/hiveserver2.pid" ] && kill -0 "$(cat "$HIVE_PID_DIR/hiveserver2.pid")" 2>/dev/null; then
  echo "HiveServer2 already running (pid $(cat "$HIVE_PID_DIR/hiveserver2.pid"))"
else
  setsid nohup hive --service hiveserver2 > "$HIVE_LOG_DIR/hiveserver2.out" 2>&1 &
  echo $! > "$HIVE_PID_DIR/hiveserver2.pid"
  echo "HiveServer2 starting (pid $(cat "$HIVE_PID_DIR/hiveserver2.pid"))"
fi

ready=0
for i in $(seq 1 90); do
  if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/10000' 2>/dev/null; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "ERROR: HiveServer2 did not open port 10000" >&2
  tail -40 "$HIVE_LOG_DIR/hiveserver2.out" || true
  exit 1
fi

beeline -u jdbc:hive2://127.0.0.1:10000/default -n rajesh --silent=true \
  --outputformat=csv2 --showHeader=false -f "$HIVE_CONF_DIR/hive-ddl.sql"
echo "START_HIVE_OK"
