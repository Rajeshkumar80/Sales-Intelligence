#!/usr/bin/env bash
# Ad-hoc YARN smoke test for the MapReduce jar (tiny fixture).
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

cd "$HOME/BDA-Projects/sales-intelligence"
BATCH="manual-smoke"
IN="/bda/sales/input/batch_id=$BATCH"
OUT="/bda/sales/revenue/batch_id=$BATCH"

hdfs dfs -rm -r -f "$OUT" >/dev/null 2>&1 || true
hadoop jar mapreduce-java/target/sales-mapreduce.jar edu.bda.sales.SalesDriver "$IN" "$OUT"
echo "--- MR output ---"
hdfs dfs -cat "$OUT/part-r-00000"
