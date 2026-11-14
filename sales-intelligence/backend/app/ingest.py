"""Transaction persistence: manual entry, bulk insert, paged listing."""

import re
import uuid
from datetime import datetime, timedelta

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import BulkWriteError, DuplicateKeyError

from . import db
from .schemas import TransactionIn, to_utc

SORT_FIELDS = {
    "timestamp": "timestamp",
    "revenue": "revenue",
    "quantity": "quantity",
    "product_name": "product_name",
    "region": "region",
    "category": "category",
}


def _start(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else to_utc(value)


def _end(value: str | datetime) -> datetime:
    """A bare date means the whole day, so the upper bound is exclusive."""
    if isinstance(value, datetime):
        return value
    start = to_utc(value)
    return start + timedelta(days=1) if len(value.strip()) == 10 else start


def new_transaction_id() -> str:
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


def transaction_doc(payload: TransactionIn, source: str) -> dict:
    stamp = payload.timestamp
    return {
        "transaction_id": payload.transaction_id or new_transaction_id(),
        "product_id": payload.product_id,
        "product_name": payload.product_name,
        "category": payload.category,
        "quantity": payload.quantity,
        "unit_price": round(float(payload.unit_price), 2),
        "revenue": round(payload.quantity * float(payload.unit_price), 2),
        "region": payload.region,
        "timestamp": stamp,
        "timestamp_ms": int(stamp.timestamp() * 1000),
        "source": source,
        "batch_id": None,
        "processed": False,
        "processed_at": None,
        "created_at": db.now(),
    }


def add_transaction(payload: TransactionIn) -> dict:
    doc = transaction_doc(payload, source="manual")
    db.get_db()[db.TRANSACTIONS].insert_one(doc)
    doc.pop("_id", None)
    return doc


class DuplicateTransaction(Exception):
    def __init__(self, transaction_id: str):
        super().__init__(f"transaction_id {transaction_id} already exists")
        self.transaction_id = transaction_id


def insert_many(docs: list[dict]) -> tuple[int, list[dict], list[dict]]:
    """Insert with per-row reporting. Duplicates never abort the whole upload."""
    if not docs:
        return 0, [], []
    collection = db.get_db()[db.TRANSACTIONS]
    try:
        result = collection.insert_many(docs, ordered=False)
        return len(result.inserted_ids), [], []
    except BulkWriteError as exc:
        duplicates = []
        errors = []
        for err in exc.details.get("writeErrors", []):
            doc = err.get("op", {})
            entry = {"transaction_id": doc.get("transaction_id"), "error": err.get("errmsg", "")}
            if err.get("code") == 11000:
                duplicates.append(entry)
            else:
                errors.append(entry)
        inserted = exc.details.get("nInserted", 0)
        return inserted, duplicates, errors


def list_transactions(
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    region: str | None = None,
    product_id: str | None = None,
    category: str | None = None,
    processed: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "-timestamp",
) -> dict:
    query: dict = {}
    if search:
        safe = re.escape(search.strip())
        query["$or"] = [
            {"transaction_id": {"$regex": safe, "$options": "i"}},
            {"product_id": {"$regex": safe, "$options": "i"}},
            {"product_name": {"$regex": safe, "$options": "i"}},
        ]
    if region:
        query["region"] = region
    if product_id:
        query["product_id"] = product_id
    if category:
        query["category"] = category
    if processed is not None:
        query["processed"] = processed
    if date_from or date_to:
        window: dict = {}
        if date_from:
            window["$gte"] = _start(date_from)
        if date_to:
            window["$lt"] = _end(date_to)
        query["timestamp"] = window

    descending = sort.startswith("-")
    field = SORT_FIELDS.get(sort.lstrip("-"), "timestamp")
    direction = DESCENDING if descending else ASCENDING

    page = max(1, page)
    page_size = min(100, max(1, page_size))
    collection = db.get_db()[db.TRANSACTIONS]
    total = collection.count_documents(query)
    cursor = (
        collection.find(query, {"_id": 0})
        .sort(field, direction)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": list(cursor),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


def stats() -> dict:
    collection = db.get_db()[db.TRANSACTIONS]
    total = collection.count_documents({})
    pending = collection.count_documents({"processed": False})
    return {"total": total, "pending": pending, "processed": total - pending}
