"""CSV exports. Cells starting with a formula trigger are prefixed with an apostrophe."""

import csv
import io

from . import analytics, db, ingest

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def _render(header: list[str], rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe(cell) for cell in row])
    return buffer.getvalue()


def transactions_csv(**filters) -> str:
    result = ingest.list_transactions(page=1, page_size=100, **filters)
    rows = []
    page = 1
    while result["items"] and page <= 200:  # 20k rows max for a browser download
        rows.extend(result["items"])
        page += 1
        result = ingest.list_transactions(page=page, page_size=100, **filters)
    return _render(
        ["transaction_id", "product_id", "product_name", "category", "quantity", "unit_price",
         "revenue", "region", "timestamp", "source", "processed", "batch_id"],
        [[t["transaction_id"], t["product_id"], t["product_name"], t["category"], t["quantity"],
          t["unit_price"], t["revenue"], t["region"], t["timestamp"].isoformat(), t["source"],
          t["processed"], t.get("batch_id")] for t in rows],
    )


def analytics_csv(dataset: str, **filters) -> str:
    if dataset not in {"products", "daily", "monthly", "regional", "category", "hive"}:
        raise ValueError(f"unknown dataset: {dataset}")
    data = analytics.overview(**filters)
    if dataset == "products":
        return _render(
            ["product_id", "product_name", "revenue", "quantity", "orders"],
            [[p["product_id"], p["product_name"], p["revenue"], p["quantity"], p["orders"]]
             for p in data["all_products"]],
        )
    if dataset == "daily":
        return _render(["date", "revenue", "quantity", "orders"],
                       [[d["date"], d["revenue"], d["quantity"], d["orders"]] for d in data["daily"]])
    if dataset == "monthly":
        return _render(["month", "revenue", "quantity", "orders"],
                       [[m["month"], m["revenue"], m["quantity"], m["orders"]] for m in data["monthly"]])
    if dataset == "regional":
        return _render(["region", "revenue", "quantity", "orders"],
                       [[r["region"], r["revenue"], r["quantity"], r["orders"]] for r in data["region"]])
    if dataset == "category":
        return _render(["category", "revenue", "quantity"],
                       [[c["category"], c["revenue"], c["quantity"]] for c in data["category"]])
    if dataset == "hive":
        snapshot = analytics.latest_snapshot()
        rows = snapshot["hive_results"] if snapshot else []
        return _render(["section", "key", "label", "revenue", "quantity", "orders"],
                       [[r["section"], r["key"], r["label"], r["revenue"], r["quantity"], r["orders"]]
                        for r in rows])
    raise ValueError(f"unknown dataset: {dataset}")
