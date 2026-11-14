#!/usr/bin/env bash
# Initialize the Hive Derby metastore (once).
set -euo pipefail
. "$HOME/BDA-Projects/infra/env.sh"

# Do NOT pre-create metastore_db: embedded Derby refuses to create a database
# inside an existing directory (ERROR XBM0J).
mkdir -p "$BDA_HOME/infra/data/hive/scratch" \
  "$BDA_HOME/infra/data/hive/resources" "$HIVE_LOG_DIR" "$HIVE_PID_DIR"

if [ -f "$BDA_HOME/infra/data/hive/metastore_db/service.properties" ]; then
  echo "Hive metastore already initialized"
else
  schematool -dbType derby -initSchema
fi
echo "HIVE_INIT_OK"
