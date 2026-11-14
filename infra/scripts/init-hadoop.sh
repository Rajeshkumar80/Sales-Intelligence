#!/usr/bin/env bash
# One-time HDFS format + runtime directories.
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

BDA_DATA="$BDA_HOME/infra/data"
mkdir -p "$BDA_DATA"/hdfs/{name,data} "$BDA_DATA/hadoop-tmp" \
  "$BDA_DATA"/yarn/{local,logs} "$HADOOP_LOG_DIR" "$HADOOP_PID_DIR" \
  "$BDA_DATA"/hive/{metastore_db,scratch,resources} "$HIVE_LOG_DIR"

if [ ! -f "$BDA_DATA/hdfs/name/current/VERSION" ]; then
  echo "formatting NameNode..."
  hdfs namenode -format -nonInteractive
else
  echo "NameNode already formatted"
fi
echo "INIT_HADOOP_OK"
