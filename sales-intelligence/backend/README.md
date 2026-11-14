# Backend — FastAPI

Synchronous FastAPI service (one uvicorn worker) that owns ingestion, batch
orchestration, Hive access and analytics.

## Setup

```bash
cd ~/BDA-Projects/sales-intelligence/backend
cp .env.example .env
chmod 600 .env
# set MONGODB_PASSWORD in .env
```

Dependencies live in the project venv (`~/BDA-Projects/.venv`), installed from
`requirements.txt`.

## Run

```bash
source ~/BDA-Projects/infra/env.sh
../scripts/start-backend.sh
# or foreground:
../../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

OpenAPI: <http://127.0.0.1:8000/docs>

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | `.env` loading, Atlas URI, HDFS/Hive paths, limits |
| `db.py` | lazy Mongo client, collections, indexes, UTC clock |
| `schemas.py` | Pydantic request models and UTC normalisation |
| `catalog.py` | 16-product catalog shared by simulator and dataset generator |
| `ingest.py` | manual insert, bulk insert with per-row duplicate reporting, paging |
| `csv_import.py` | strict header/row validation, BOM handling, limits |
| `simulator.py` | background generator thread (start/stop/status) |
| `hadoop.py` | HDFS and `hadoop jar` wrappers, counters, output reader |
| `hive.py` | beeline SQL runner, partition DDL, fact build, aggregates |
| `pipeline.py` | claim → HDFS → MR → Hive → reconcile → snapshot, lock, rollback |
| `analytics.py` | Mongo aggregation over the Hive fact cube, filter options |
| `export.py` | CSV rendering with formula-injection neutralisation |
| `main.py` | routes, error shape, CORS, startup recovery |

## Tests

```bash
source ~/BDA-Projects/infra/env.sh
../../.venv/bin/pytest                  # unit (12)
BDA_E2E=1 MONGODB_DB=bda_sales_e2e ../../.venv/bin/pytest tests/test_e2e.py -m e2e -x -s
```

Unit tests use dummy credentials and never contact Atlas. The E2E suite needs a
real Atlas user, running HDFS/YARN and HiveServer2; it drops and recreates only
`bda_sales_e2e`.

## Error contract

```json
{"detail": {"code": "DUPLICATE_TRANSACTION_ID", "message": "...", "fields": []}}
```

Validation errors return HTTP 422 with the same shape. Database and Hadoop
failures return 503/500 with a readable message; secrets are never echoed.
