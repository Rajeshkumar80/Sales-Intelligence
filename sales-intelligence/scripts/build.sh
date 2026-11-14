#!/usr/bin/env bash
# Build the MapReduce jar and the production frontend bundle.
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"
ROOT="$HOME/BDA-Projects/sales-intelligence"

cd "$ROOT/mapreduce-java"
mvn -q clean package
echo "MapReduce jar: $ROOT/mapreduce-java/target/sales-mapreduce.jar"

cd "$ROOT/frontend"
npm run build
echo "Frontend bundle: $ROOT/frontend/dist"

echo BUILD_OK
