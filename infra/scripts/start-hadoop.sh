#!/usr/bin/env bash
# Start HDFS + YARN + JobHistory, then create the BDA directories.
# Bounded waits: never hang the calling shell.
set -uo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

mkdir -p "$HADOOP_LOG_DIR" "$HADOOP_PID_DIR" \
  "$BDA_HOME/infra/data"/yarn/{local,logs}

start() {
  local name="$1"; shift
  if jps -l 2>/dev/null | grep -q "$name"; then
    echo "$name already running"
  else
    # setsid detaches the daemon from the wsl.exe session; otherwise WSL
    # kills it when the invoking shell exits.
    setsid "$@" >/dev/null 2>&1 || true
  fi
}

start NameNode hdfs --daemon start namenode
sleep 3
start DataNode hdfs --daemon start datanode
start ResourceManager yarn --daemon start resourcemanager
start NodeManager yarn --daemon start nodemanager
start JobHistoryServer mapred --daemon start historyserver

echo "waiting for HDFS..."
hdfs_ready=0
for i in $(seq 1 45); do
  if timeout 10 hdfs dfs -ls / >/dev/null 2>&1; then hdfs_ready=1; break; fi
  sleep 1
done
if [ "$hdfs_ready" -ne 1 ]; then
  echo "ERROR: HDFS did not become ready" >&2
  exit 1
fi

timeout 30 hdfs dfs -mkdir -p /bda/sales/input /bda/sales/fact /bda/smoke \
  /user/hive/warehouse /tmp/hive >/dev/null 2>&1 || true
timeout 30 hdfs dfs -chmod -R 777 /bda /user/hive/warehouse /tmp/hive >/dev/null 2>&1 || true

echo "waiting for YARN NodeManager..."
yarn_ready=0
for i in $(seq 1 30); do
  if timeout 10 yarn node -list 2>/dev/null | grep -q RUNNING; then yarn_ready=1; break; fi
  sleep 2
done
timeout 10 yarn node -list 2>/dev/null | tail -5 || true
if [ "$yarn_ready" -ne 1 ]; then
  echo "WARN: no RUNNING NodeManager yet; check ResourceManager logs" >&2
fi

echo
jps
echo "START_HADOOP_OK"
