#!/usr/bin/env bash
# Real HDFS + YARN MapReduce smoke test.
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

hdfs dfs -mkdir -p /bda/smoke/input
cat > /tmp/bda-words.txt <<'EOF'
sales intelligence hadoop mapreduce
hadoop hive mongodb
sales revenue product revenue
hive analytics sales
mapreduce reducer mapper
EOF
hdfs dfs -put -f /tmp/bda-words.txt /bda/smoke/input/words.txt
hdfs dfs -rm -r -f /bda/smoke/output >/dev/null

hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.4.3.jar" \
  wordcount /bda/smoke/input /bda/smoke/output

echo
echo "== YARN application =="
yarn application -list -appStates ALL 2>/dev/null | tail -3 || true
echo
echo "== output =="
hdfs dfs -cat /bda/smoke/output/part-r-00000
echo "SMOKE_MR_OK"
