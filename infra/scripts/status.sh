#!/usr/bin/env bash
# Read-only service status summary.
set -uo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

echo "== Java =="
java -version 2>&1 | head -1
echo
echo "== Hadoop daemons =="
jps | grep -E 'NameNode|DataNode|ResourceManager|NodeManager|JobHistoryServer' || echo "none"
echo
echo "== HDFS =="
hdfs dfs -ls / 2>&1 | head -8 || true
echo
echo "== YARN nodes =="
yarn node -list 2>&1 | tail -4 || true
echo
echo "== HiveServer2 port 10000 =="
if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/10000' 2>/dev/null; then echo "open"; else echo "closed"; fi
echo
echo "== Backend / frontend ports =="
for p in 8000 5173; do
  if timeout 1 bash -c "exec 3<>/dev/tcp/127.0.0.1/$p" 2>/dev/null; then echo "$p open"; else echo "$p closed"; fi
done
echo
echo "== Memory =="
free -h | head -2
