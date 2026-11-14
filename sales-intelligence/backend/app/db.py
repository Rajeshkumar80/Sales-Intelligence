"""MongoDB access. The client is created lazily so the API boots without Atlas."""

import threading
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError

from . import config

_client: MongoClient | None = None
_lock = threading.Lock()

TRANSACTIONS = "transactions"
MR_PRODUCT = "analytics_mr_product"
FACT_DAILY = "analytics_fact_daily"
SNAPSHOTS = "analytics_snapshot"
JOBS = "jobs"
LOCKS = "pipeline_locks"
BATCHES = "processed_batches"

PIPELINE_LOCK_ID = "sales-pipeline"


def now() -> datetime:
    return datetime.now(timezone.utc)


def get_db():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = MongoClient(
                    config.mongo_uri(),
                    serverSelectionTimeoutMS=8000,
                    connectTimeoutMS=8000,
                    tz_aware=True,
                )
    return _client[config.MONGO_DB]


def ensure_indexes() -> None:
    db = get_db()
    db[TRANSACTIONS].create_index([("transaction_id", ASCENDING)], unique=True, name="uniq_transaction")
    db[TRANSACTIONS].create_index([("processed", ASCENDING), ("batch_id", ASCENDING)], name="claimable")
    db[TRANSACTIONS].create_index([("timestamp", DESCENDING)], name="recent")
    db[TRANSACTIONS].create_index([("product_id", ASCENDING)], name="by_product")
    db[TRANSACTIONS].create_index([("region", ASCENDING)], name="by_region")
    db[MR_PRODUCT].create_index([("batch_id", ASCENDING)], name="by_batch")
    db[MR_PRODUCT].create_index([("revenue", DESCENDING)], name="by_revenue")
    db[FACT_DAILY].create_index(
        [("sale_date", ASCENDING), ("region", ASCENDING), ("product_id", ASCENDING)], name="cube_filter"
    )
    db[FACT_DAILY].create_index([("batch_id", ASCENDING)], name="by_batch")
    db[SNAPSHOTS].create_index([("generated_at", DESCENDING)], name="recent_snapshots")
    db[JOBS].create_index([("started_at", DESCENDING)], name="recent_jobs")
    db[JOBS].create_index([("status", ASCENDING)], name="by_status")
    db[LOCKS].create_index([("acquired_at", ASCENDING)], name="lock_age")


def mongo_status() -> dict:
    try:
        db = get_db()
        db.command("ping")
        return {
            "status": "ok",
            "database": db.name,
            "collections": sorted(db.list_collection_names()),
            "transactions": db[TRANSACTIONS].estimated_document_count(),
        }
    except (PyMongoError, config.ConfigError) as exc:
        return {"status": "error", "error": str(exc)}
