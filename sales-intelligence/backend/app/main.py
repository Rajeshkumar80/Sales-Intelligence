"""Sales Intelligence API. Every dashboard number comes from MongoDB, MR or Hive."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pymongo.errors import DuplicateKeyError, PyMongoError

from . import analytics, config, csv_import, db, export, hadoop, hive, ingest, pipeline, simulator
from .catalog import CATEGORIES, PRODUCTS, REGIONS
from .schemas import ProcessRequest, SimulatorStart, TransactionIn

_hive_cache: dict = {"checked": 0.0, "alive": False}


def _hive_health(max_age: float = 60.0) -> bool:
    if time.time() - _hive_cache["checked"] > max_age:
        _hive_cache["alive"] = hive.hive_alive()
        _hive_cache["checked"] = time.time()
    return _hive_cache["alive"]


def _init_state() -> None:
    try:
        db.ensure_indexes()
        pipeline.recover_after_restart()
    except (PyMongoError, config.ConfigError) as exc:  # API must still boot for diagnostics
        print(f"[startup] MongoDB not ready: {exc}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _init_state()
    yield


app = FastAPI(title="BDA Sales Intelligence API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(part) for part in err.get("loc", ()) if part != "body"),
         "message": err.get("msg", "")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "fields": fields}},
    )


def _fail(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message}})


@app.get("/api/health")
def health(deep: bool = False) -> dict:
    mongo = db.mongo_status()
    infra = hadoop.env_ready()
    if deep:
        hive_state = "ok" if _hive_health(max_age=5) else "unavailable"
    else:
        hive_state = "unchecked"
    ok = mongo.get("status") == "ok" and infra["jar_built"]
    return {
        "status": "ok" if ok else "degraded",
        "components": {
            "mongodb": mongo,
            "hive": {"status": hive_state, "url": config.HIVE_URL},
            "hadoop": infra,
        },
        "server_time": db.now().isoformat(),
    }


@app.get("/api/mongo/status")
def mongo_status() -> dict:
    return db.mongo_status()


# ---------------------------------------------------------------- ingestion
@app.post("/api/sales/transactions", status_code=201)
def create_transaction(payload: TransactionIn):
    try:
        return ingest.add_transaction(payload)
    except DuplicateKeyError:
        return _fail(409, "DUPLICATE_TRANSACTION_ID",
                     f"transaction_id {payload.transaction_id} already exists")
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))


@app.get("/api/sales/transactions")
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    region: str | None = None,
    category: str | None = None,
    processed: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = "-timestamp",
):
    try:
        return ingest.list_transactions(
            page=page, page_size=page_size, search=search, region=region, category=category,
            processed=processed, date_from=date_from, date_to=date_to, sort=sort,
        )
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))


@app.get("/api/sales/transactions/stats")
def transaction_stats():
    try:
        return ingest.stats()
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))


@app.get("/api/sales/transactions/template.csv")
def csv_template() -> Response:
    body = (
        "transaction_id,product_id,product_name,category,quantity,unit_price,region,timestamp\n"
        "TXN-EXAMPLE-1,P-1001,Wireless Keyboard,Electronics,2,42.50,North,2026-11-11T09:30:00Z\n"
    )
    return Response(body, media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="sales-template.csv"'})


@app.post("/api/sales/transactions/upload")
async def upload_csv(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        parsed = csv_import.parse_csv(raw)
    except ValueError as exc:
        return _fail(400, "INVALID_CSV", str(exc))
    try:
        inserted, duplicates, write_errors = ingest.insert_many(parsed["rows"])
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))
    return {
        "filename": file.filename,
        "rows_total": len(parsed["rows"]) + len(parsed["errors"]),
        "inserted": inserted,
        "duplicates": len(duplicates),
        "invalid": len(parsed["errors"]),
        "duplicate_details": duplicates[:50],
        "invalid_details": parsed["errors"][:100],
        "write_errors": write_errors[:50],
    }


# ---------------------------------------------------------------- simulator
@app.get("/api/sales/catalog")
def catalog() -> dict:
    return {
        "products": [
            {"product_id": pid, "product_name": name, "category": category, "unit_price": price}
            for pid, name, category, price in PRODUCTS
        ],
        "regions": REGIONS,
        "categories": CATEGORIES,
    }


@app.post("/api/sales/simulator/start")
def simulator_start(payload: SimulatorStart):
    return simulator.simulator.start(payload.interval_seconds, payload.batch_size)


@app.post("/api/sales/simulator/stop")
def simulator_stop():
    return simulator.simulator.stop()


@app.get("/api/sales/simulator/status")
def simulator_status():
    return simulator.simulator.status()


# ---------------------------------------------------------------- pipeline
@app.post("/api/sales/process", status_code=202)
def process(payload: ProcessRequest | None = None):
    try:
        job = pipeline.start(payload.batch_size if payload else None)
    except pipeline.AlreadyRunning as exc:
        return _fail(409, "PIPELINE_BUSY", f"job {exc.job_id} is already running")
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))
    return {"job_id": job["job_id"], "batch_id": job["batch_id"], "status": job["status"]}


@app.get("/api/sales/processing/status")
def processing_status():
    latest = pipeline.latest_job()
    return {"running": bool(latest and latest["status"] in pipeline.ACTIVE), "job": latest}


@app.get("/api/sales/jobs")
def jobs(limit: int = Query(20, ge=1, le=100), status: str | None = None):
    return {"items": pipeline.list_jobs(limit=limit, status=status)}


@app.get("/api/sales/jobs/{job_id}")
def job_detail(job_id: str):
    job = pipeline.get_job(job_id)
    if not job:
        return _fail(404, "JOB_NOT_FOUND", f"job {job_id} does not exist")
    return job


# ---------------------------------------------------------------- analytics
def _filters(date_from: str | None, date_to: str | None, product_id: str | None,
             category: str | None, region: str | None) -> dict:
    return {"date_from": date_from, "date_to": date_to, "product_id": product_id,
            "category": category, "region": region}


@app.get("/api/sales/analytics/overview")
def analytics_overview(date_from: str | None = None, date_to: str | None = None,
                       product_id: str | None = None, category: str | None = None,
                       region: str | None = None):
    try:
        return analytics.overview(**_filters(date_from, date_to, product_id, category, region))
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))


@app.get("/api/sales/analytics/revenue")
def analytics_revenue(date_from: str | None = None, date_to: str | None = None,
                      product_id: str | None = None, category: str | None = None,
                      region: str | None = None):
    data = analytics.overview(**_filters(date_from, date_to, product_id, category, region))
    return {"kpis": data["kpis"], "daily": data["daily"], "monthly": data["monthly"]}


@app.get("/api/sales/analytics/top-products")
def analytics_top_products(date_from: str | None = None, date_to: str | None = None,
                           product_id: str | None = None, category: str | None = None,
                           region: str | None = None):
    data = analytics.overview(**_filters(date_from, date_to, product_id, category, region))
    return {"items": data["top_products"]}


@app.get("/api/sales/analytics/regional")
def analytics_regional(date_from: str | None = None, date_to: str | None = None,
                       product_id: str | None = None, category: str | None = None,
                       region: str | None = None):
    data = analytics.overview(**_filters(date_from, date_to, product_id, category, region))
    return {"items": data["region"]}


@app.get("/api/sales/analytics/categories")
def analytics_categories(date_from: str | None = None, date_to: str | None = None,
                         product_id: str | None = None, category: str | None = None,
                         region: str | None = None):
    data = analytics.overview(**_filters(date_from, date_to, product_id, category, region))
    return {"items": data["category"]}


@app.get("/api/sales/analytics/trends")
def analytics_trends(
    period: str = "daily",
    date_from: str | None = None,
    date_to: str | None = None,
    product_id: str | None = None,
    category: str | None = None,
    region: str | None = None,
):
    if period not in ("daily", "monthly"):
        return _fail(400, "INVALID_PERIOD", "period must be daily or monthly")
    data = analytics.overview(**_filters(date_from, date_to, product_id, category, region))
    return {"period": period, "items": data[period]}


@app.get("/api/sales/analytics/mr-results")
def mr_results():
    return analytics.mr_products()


@app.get("/api/sales/analytics/hive-results")
def hive_results():
    snapshot = analytics.latest_snapshot()
    if not snapshot:
        return {"snapshot": None}
    return {"snapshot": snapshot}


@app.get("/api/sales/analytics/reconciliation")
def reconciliation():
    snapshot = analytics.latest_snapshot()
    return {"reconciliation": snapshot.get("reconciliation") if snapshot else None,
            "batch_id": snapshot.get("batch_id") if snapshot else None}


@app.get("/api/sales/analytics/options")
def analytics_options():
    return analytics.filter_options()


# ---------------------------------------------------------------- reports
@app.get("/api/sales/reports/export/{dataset}.csv")
def export_report(
    dataset: str,
    date_from: str | None = None,
    date_to: str | None = None,
    product_id: str | None = None,
    category: str | None = None,
    region: str | None = None,
    search: str | None = None,
    processed: bool | None = None,
):
    filters = _filters(date_from, date_to, product_id, category, region)
    try:
        if dataset == "transactions":
            body = export.transactions_csv(search=search, processed=processed, **filters)
        else:
            body = export.analytics_csv(dataset, **filters)
    except ValueError as exc:
        return _fail(404, "UNKNOWN_DATASET", str(exc))
    except (PyMongoError, config.ConfigError) as exc:
        return _fail(503, "DATABASE_UNAVAILABLE", str(exc))
    return Response(
        body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="sales-{dataset}.csv"'},
    )


# ---------------------------------------------------------------- settings
@app.get("/api/settings")
def settings():
    return {
        "batch_size": config.BATCH_SIZE,
        "simulator": {"interval_seconds": config.SIMULATOR_INTERVAL, "batch_size": config.SIMULATOR_BATCH},
        "csv": {"max_mb": config.CSV_MAX_BYTES // (1024 * 1024), "max_rows": config.CSV_MAX_ROWS},
        "hive": {"url": config.HIVE_URL, "database": config.HIVE_DB},
        "hdfs": {"input": config.HDFS_INPUT, "revenue": config.HDFS_REVENUE},
        "execution_mode": "single-node pseudo-distributed Hadoop (YARN containers)",
        "infra": hadoop.env_ready(),
    }
