#!/usr/bin/env bash
# Stop YARN first, then HDFS.
set -uo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

mapred --daemon stop historyserver 2>/dev/null || true
yarn --daemon stop nodemanager 2>/dev/null || true
yarn --daemon stop resourcemanager 2>/dev/null || true
hdfs --daemon stop datanode 2>/dev/null || true
hdfs --daemon stop namenode 2>/dev/null || true
sleep 2
echo "remaining Hadoop processes:"
jps | grep -E 'NameNode|DataNode|ResourceManager|NodeManager|JobHistoryServer' || echo "none"
echo "STOP_HADOOP_OK"
