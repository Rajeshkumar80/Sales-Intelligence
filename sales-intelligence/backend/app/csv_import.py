"""CSV upload: strict header check, per-row validation, duplicate reporting."""

import csv
import io

from pydantic import ValidationError

from . import config, ingest
from .catalog import CATEGORIES, REGIONS
from .schemas import TransactionIn, to_utc

REQUIRED_COLUMNS = (
    "transaction_id",
    "product_id",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "region",
    "timestamp",
)


def parse_csv(raw: bytes) -> dict:
    if len(raw) > config.CSV_MAX_BYTES:
        raise ValueError(f"file exceeds {config.CSV_MAX_BYTES // (1024 * 1024)} MB limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("file must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("file is empty")
    headers = [h.strip() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    reader.fieldnames = headers

    valid: list[dict] = []
    errors: list[dict] = []
    for row_number, row in enumerate(reader, start=2):
        if row_number - 1 > config.CSV_MAX_ROWS:
            raise ValueError(f"file exceeds {config.CSV_MAX_ROWS} rows")
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue
        try:
            payload = TransactionIn(
                transaction_id=(row.get("transaction_id") or "").strip() or None,
                product_id=(row.get("product_id") or "").strip(),
                product_name=(row.get("product_name") or "").strip(),
                category=(row.get("category") or "").strip(),
                quantity=int((row.get("quantity") or "").strip()),
                unit_price=float((row.get("unit_price") or "").strip()),
                region=(row.get("region") or "").strip(),
                timestamp=to_utc((row.get("timestamp") or "").strip() or None),
            )
        except (ValidationError, ValueError) as exc:
            errors.append({"row": row_number, "error": _message(exc), "raw": row.get("transaction_id")})
            continue
        valid.append(ingest.transaction_doc(payload, source="csv"))

    return {"rows": valid, "errors": errors}


def _message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first.get("loc", ()))
        return f"{field}: {first.get('msg')}"
    return str(exc)


def known_values() -> dict:
    return {"regions": REGIONS, "categories": CATEGORIES}
