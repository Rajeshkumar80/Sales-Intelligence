"""Batch pipeline: claim -> HDFS -> MapReduce -> Hive cube -> reconcile -> snapshot."""

import csv
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from pymongo import ReplaceOne
from pymongo.errors import DuplicateKeyError, PyMongoError

from . import config, db, hadoop, hive, ingest

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sales-pipeline")
_job_lock = threading.Lock()
ACTIVE = {"QUEUED", "RUNNING"}


class AlreadyRunning(RuntimeError):
    def __init__(self, job_id: str | None):
        super().__init__(f"a sales pipeline job is already running: {job_id or 'unknown'}")
        self.job_id = job_id


class PipelineError(RuntimeError):
    pass


def _jobs():
    return db.get_db()[db.JOBS]


def acquire_lock(job_id: str) -> None:
    locks = db.get_db()[db.LOCKS]
    try:
        locks.insert_one({"_id": db.PIPELINE_LOCK_ID, "job_id": job_id, "acquired_at": db.now()})
        return
    except DuplicateKeyError:
        pass
    stale = locks.find_one({"_id": db.PIPELINE_LOCK_ID})
    cutoff = db.now() - timedelta(minutes=30)
    if stale and stale.get("acquired_at", db.now()) < cutoff:
        locks.replace_one({"_id": db.PIPELINE_LOCK_ID}, {"_id": db.PIPELINE_LOCK_ID, "job_id": job_id,
                                                          "acquired_at": db.now()})
        return
    raise AlreadyRunning(stale.get("job_id") if stale else None)


def release_lock() -> None:
    db.get_db()[db.LOCKS].delete_one({"_id": db.PIPELINE_LOCK_ID})


def start(batch_size: int | None = None) -> dict:
    size = int(batch_size or config.BATCH_SIZE)
    with _job_lock:
        running = _jobs().find_one({"status": {"$in": list(ACTIVE)}}, {"job_id": 1})
        if running:
            raise AlreadyRunning(running.get("job_id"))
        batch_id = f"sales-{db.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
        job_id = f"job-{secrets.token_hex(6)}"
        acquire_lock(job_id)
        doc = {
            "job_id": job_id,
            "batch_id": batch_id,
            "status": "QUEUED",
            "batch_size": size,
            "started_at": db.now(),
            "finished_at": None,
            "duration_ms": None,
            "stages": [],
            "logs": [],
            "error": None,
            "metrics": {},
            "execution_mode": "HDFS + YARN MapReduce + Hive on MR (pseudo-distributed)",
        }
        _jobs().insert_one(dict(doc))
        _executor.submit(_run, job_id, batch_id, size)
    return doc


def _log(job_id: str, message: str, level: str = "INFO") -> None:
    entry = {"ts": db.now(), "level": level, "message": message}
    _jobs().update_one({"job_id": job_id}, {"$push": {"logs": {"$each": [entry], "$slice": -200}}})


def _stage_start(job_id: str, name: str) -> None:
    entry = {"name": name, "status": "RUNNING", "started_at": db.now(), "finished_at": None, "details": {}}
    _jobs().update_one({"job_id": job_id}, {"$push": {"stages": entry}})
    _log(job_id, f"stage {name} started")


def _stage_end(job_id: str, name: str, status: str, details: dict | None = None) -> None:
    _jobs().update_one(
        {"job_id": job_id, "stages.name": name},
        {"$set": {"stages.$.status": status, "stages.$.finished_at": db.now(),
                  "stages.$.details": details or {}}},
    )
    _log(job_id, f"stage {name} {status.lower()}")


def claim_transactions(batch_id: str, limit: int) -> list[dict]:
    collection = db.get_db()[db.TRANSACTIONS]
    query = {"processed": False, "batch_id": None}
    docs = list(collection.find(query).sort("timestamp", 1).limit(limit))
    if not docs:
        raise PipelineError("no unprocessed transactions to claim")
    ids = [doc["_id"] for doc in docs]
    result = collection.update_many(
        {"_id": {"$in": ids}, "processed": False, "batch_id": None},
        {"$set": {"batch_id": batch_id, "claimed_at": db.now()}},
    )
    if result.modified_count != len(ids):
        collection.update_many({"_id": {"$in": ids}, "processed": False}, {"$set": {"batch_id": None}})
        raise PipelineError("batch claim raced with another writer; retry")
    return docs


def write_staging(batch_id: str, docs: list[dict]) -> int:
    path = hadoop.staging_path(batch_id)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for doc in docs:
            writer.writerow([
                doc["transaction_id"], doc["product_id"], doc["product_name"], doc["category"],
                doc["quantity"], f"{doc['unit_price']:.2f}", doc["region"], doc["timestamp_ms"],
            ])
    return path.stat().st_size


def _run(job_id: str, batch_id: str, batch_size: int) -> None:
    started = db.now()
    _jobs().update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}})
    claimed: list[dict] = []
    try:
        _stage_start(job_id, "claim")
        claimed = claim_transactions(batch_id, batch_size)
        _stage_end(job_id, "claim", "SUCCEEDED", {"transactions": len(claimed)})

        _stage_start(job_id, "hdfs")
        hdfs_size = write_staging(batch_id, claimed)
        hadoop.hdfs_mkdir(f"{config.HDFS_INPUT}/batch_id={batch_id}")
        hadoop.hdfs_put(hadoop.staging_path(batch_id), f"{config.HDFS_INPUT}/batch_id={batch_id}/data.tsv")
        hive.add_partition(batch_id)
        _stage_end(job_id, "hdfs", "SUCCEEDED", {"bytes": hdfs_size})

        _stage_start(job_id, "mapreduce")
        mr = hadoop.run_mr(batch_id)
        rows = hadoop.read_mr_output(batch_id)
        _store_mr(batch_id, rows, job_id)
        _stage_end(job_id, "mapreduce", "SUCCEEDED", {"products": len(rows), **mr["counters"]})

        _stage_start(job_id, "hive_fact")
        hive.build_fact(batch_id)
        fact = hive.fact_rows(batch_id)
        _store_fact(batch_id, fact, job_id)
        _stage_end(job_id, "hive_fact", "SUCCEEDED", {"fact_rows": len(fact)})

        _stage_start(job_id, "hive_aggregates")
        aggregates = hive.aggregates(batch_id)
        _stage_end(job_id, "hive_aggregates", "SUCCEEDED", {"sections": len(aggregates)})

        _stage_start(job_id, "reconcile")
        reconciliation = _reconcile(mr_rows=rows, aggregates=aggregates)
        _store_snapshot(batch_id, job_id, mr, aggregates, reconciliation)
        _stage_end(job_id, "reconcile", "SUCCEEDED", reconciliation)

        db.get_db()[db.TRANSACTIONS].update_many(
            {"batch_id": batch_id, "processed": False},
            {"$set": {"processed": True, "processed_at": db.now()}},
        )
        db.get_db()[db.BATCHES].insert_one({
            "_id": batch_id, "job_id": job_id, "transactions": len(claimed),
            "completed_at": db.now(), "reconciliation_ok": reconciliation["match"],
        })
        _finish(job_id, started, "SUCCEEDED", {
            "transactions": len(claimed), "products": len(rows), "fact_rows": len(fact),
            "revenue": reconciliation["mr_revenue"],
        })
    except Exception as exc:  # noqa: BLE001 - job must always end in a terminal state
        _log(job_id, f"pipeline failed: {exc}", "ERROR")
        _jobs().update_one({"job_id": job_id}, {"$set": {"error": str(exc)[:1000]}})
        _rollback(batch_id, job_id)
        _finish(job_id, started, "FAILED", {})
    finally:
        release_lock()


def _rollback(batch_id: str, job_id: str) -> None:
    try:
        database = db.get_db()
        database[db.TRANSACTIONS].update_many(
            {"batch_id": batch_id, "processed": False}, {"$set": {"batch_id": None}}
        )
        database[db.MR_PRODUCT].delete_many({"batch_id": batch_id})
        database[db.FACT_DAILY].delete_many({"batch_id": batch_id})
        database[db.SNAPSHOTS].delete_many({"_id": batch_id})
        hive.drop_batch(batch_id)
        hadoop.hdfs_rm(f"{config.HDFS_REVENUE}/batch_id={batch_id}")
        job = _jobs().find_one({"job_id": job_id}, {"stages": 1}) or {}
        for stage in job.get("stages", []):
            if stage["status"] == "RUNNING":
                _stage_end(job_id, stage["name"], "FAILED")
    except Exception as exc:  # best effort cleanup, never mask the original error
        _log(job_id, f"rollback issue: {exc}", "WARN")


def _finish(job_id: str, started, status: str, metrics: dict) -> None:
    finished = db.now()
    _jobs().update_one(
        {"job_id": job_id},
        {"$set": {
            "status": status,
            "finished_at": finished,
            "duration_ms": int((finished - started).total_seconds() * 1000),
            "metrics": metrics,
        }},
    )


def _store_mr(batch_id: str, rows: list[dict], job_id: str) -> None:
    collection = db.get_db()[db.MR_PRODUCT]

    collection.bulk_write([
        ReplaceOne({"_id": f"{batch_id}:{row['product_id']}"},
                   {**row, "_id": f"{batch_id}:{row['product_id']}", "batch_id": batch_id, "job_id": job_id},
                   upsert=True)
        for row in rows
    ])


def _store_fact(batch_id: str, rows: list[dict], job_id: str) -> None:
    collection = db.get_db()[db.FACT_DAILY]
    collection.bulk_write([
        ReplaceOne(
            {"_id": f"{batch_id}:{row['sale_date']}:{row['product_id']}:{row['category']}:{row['region']}"},
            {**row, "_id": f"{batch_id}:{row['sale_date']}:{row['product_id']}:{row['category']}:{row['region']}",
             "batch_id": batch_id, "job_id": job_id},
            upsert=True,
        )
        for row in rows
    ])


def _reconcile(mr_rows: list[dict], aggregates: list[dict]) -> dict:
    total = next((row for row in aggregates if row["section"] == "total"), None)
    hive_revenue = float(total["revenue"]) if total else 0.0
    hive_quantity = int(total["quantity"]) if total else 0
    hive_orders = int(total["orders"]) if total else 0
    mr_revenue = round(sum(row["revenue"] for row in mr_rows), 2)
    mr_quantity = sum(row["quantity"] for row in mr_rows)
    mr_orders = sum(row["orders"] for row in mr_rows)
    tolerance = round(0.01 * max(1, len(mr_rows)) + 0.01, 2)
    delta_revenue = round(mr_revenue - hive_revenue, 4)
    return {
        "match": abs(delta_revenue) <= tolerance and mr_quantity == hive_quantity and mr_orders == hive_orders,
        "tolerance": tolerance,
        "mr_revenue": mr_revenue,
        "hive_revenue": round(hive_revenue, 2),
        "delta_revenue": delta_revenue,
        "mr_quantity": mr_quantity,
        "hive_quantity": hive_quantity,
        "mr_orders": mr_orders,
        "hive_orders": hive_orders,
        "products": len(mr_rows),
    }


def _store_snapshot(batch_id: str, job_id: str, mr: dict, aggregates: list[dict], reconciliation: dict) -> None:
    db.get_db()[db.SNAPSHOTS].replace_one(
        {"_id": batch_id},
        {
            "_id": batch_id,
            "batch_id": batch_id,
            "job_id": job_id,
            "generated_at": db.now(),
            "mr_counters": mr["counters"],
            "hive_results": aggregates,
            "reconciliation": reconciliation,
        },
        upsert=True,
    )


def latest_job() -> dict | None:
    doc = _jobs().find_one({}, {"_id": 0}, sort=[("started_at", -1)])
    return doc


def get_job(job_id: str) -> dict | None:
    return _jobs().find_one({"job_id": job_id}, {"_id": 0})


def list_jobs(limit: int = 20, status: str | None = None) -> list[dict]:
    query = {"status": status} if status else {}
    return list(_jobs().find(query, {"_id": 0, "logs": 0}).sort("started_at", -1).limit(min(limit, 100)))


def recover_after_restart() -> None:
    """Fail jobs orphaned by a crashed API process and free their claims."""
    database = db.get_db()
    for job in database[db.JOBS].find({"status": {"$in": list(ACTIVE)}}):
        database[db.JOBS].update_one(
            {"job_id": job["job_id"]},
            {"$set": {"status": "FAILED", "error": "API restarted while job was running",
                      "finished_at": db.now()}},
        )
        if job.get("batch_id"):
            database[db.TRANSACTIONS].update_many(
                {"batch_id": job["batch_id"], "processed": False}, {"$set": {"batch_id": None}}
            )
    database[db.LOCKS].delete_many({"_id": db.PIPELINE_LOCK_ID})
