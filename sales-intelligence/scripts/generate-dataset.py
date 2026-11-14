#!/usr/bin/env python3
"""Generate a deterministic 10k sales sample and its independently computed expected aggregates.

The expected JSON is computed by reading the written CSV back, not from the
generation loop, then cross-checked against the generated rows.
"""

import csv
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from app.catalog import PRODUCTS, REGIONS  # noqa: E402

ROWS = 10_000
SEED = 42
DAYS = 90
END = datetime(2026, 11, 10, 23, 59, 59, tzinfo=timezone.utc)
OUT_CSV = PROJECT / "datasets/sample_sales_10k.csv"
OUT_EXPECTED = PROJECT / "datasets/expected_sample_aggregates.json"
HEADER = ["transaction_id", "product_id", "product_name", "category",
          "quantity", "unit_price", "region", "timestamp"]


def generate() -> list[dict]:
    rng = random.Random(SEED)
    start = END - timedelta(days=DAYS)
    rows = []
    for index in range(1, ROWS + 1):
        product_id, name, category, price = rng.choice(PRODUCTS)
        quantity = rng.choices([1, 2, 3, 4, 5, 8], weights=[45, 25, 15, 8, 5, 2])[0]
        unit_price = round(price * rng.uniform(0.95, 1.05), 2)
        # Business hours keep the daily chart readable; the date range stays fixed.
        stamp = start + timedelta(seconds=rng.randrange(DAYS * 86_400))
        stamp = stamp.replace(hour=rng.randint(8, 21), minute=rng.randint(0, 59), second=rng.randint(0, 59))
        rows.append({
            "transaction_id": f"SMP-{index:06d}",
            "product_id": product_id,
            "product_name": name,
            "category": category,
            "quantity": quantity,
            "unit_price": unit_price,
            "region": rng.choice(REGIONS),
            "timestamp": stamp,
        })
    return rows


def write_csv(rows: list[dict]) -> None:
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "timestamp": row["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ")})


def read_csv() -> list[dict]:
    rows = []
    with OUT_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append({
                **row,
                "quantity": int(row["quantity"]),
                "unit_price": float(row["unit_price"]),
                "timestamp": datetime.strptime(row["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
            })
    return rows


def aggregate(rows: list[dict]) -> dict:
    products: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "quantity": 0, "orders": 0, "product_name": ""})
    categories: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "quantity": 0})
    regions: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "quantity": 0, "orders": 0})
    daily: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "quantity": 0, "orders": 0})
    monthly: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "quantity": 0, "orders": 0})

    for row in rows:
        revenue = row["quantity"] * row["unit_price"]
        date = row["timestamp"].date().isoformat()
        month = date[:7]
        for bucket in (products[row["product_id"]], categories[row["category"]],
                       regions[row["region"]], daily[date], monthly[month]):
            bucket["revenue"] += revenue
            bucket["quantity"] += row["quantity"]
        for bucket in (products[row["product_id"]], regions[row["region"]], daily[date], monthly[month]):
            bucket["orders"] += 1
        products[row["product_id"]]["product_name"] = row["product_name"]

    product_rows = sorted(
        ({"product_id": key, **value, "revenue": round(value["revenue"], 2)} for key, value in products.items()),
        key=lambda item: (-item["revenue"], item["product_id"]),
    )
    return {
        "rows": len(rows),
        "total_transactions": len(rows),
        "total_quantity": sum(row["quantity"] for row in rows),
        "total_products": len(products),
        "total_revenue": round(sum(row["quantity"] * row["unit_price"] for row in rows), 2),
        "products": product_rows,
        "top_10_products": product_rows[:10],
        "categories": sorted(
            ({"category": key, **value, "revenue": round(value["revenue"], 2)} for key, value in categories.items()),
            key=lambda item: item["category"],
        ),
        "regions": sorted(
            ({"region": key, **value, "revenue": round(value["revenue"], 2)} for key, value in regions.items()),
            key=lambda item: item["region"],
        ),
        "daily": sorted(
            ({"date": key, **value, "revenue": round(value["revenue"], 2)} for key, value in daily.items()),
            key=lambda item: item["date"],
        ),
        "monthly": sorted(
            ({"month": key, **value, "revenue": round(value["revenue"], 2)} for key, value in monthly.items()),
            key=lambda item: item["month"],
        ),
    }


def main() -> None:
    write_csv(generate())
    read_back = read_csv()
    expected = aggregate(read_back)
    generated = aggregate(generate())
    assert expected == generated, "CSV round-trip changed the aggregates"
    expected.update({
        "source": OUT_CSV.name,
        "seed": SEED,
        "date_from": min(row["timestamp"] for row in read_back).date().isoformat(),
        "date_to": max(row["timestamp"] for row in read_back).date().isoformat(),
    })
    OUT_EXPECTED.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_CSV} ({OUT_CSV.stat().st_size} bytes, {expected['rows']} rows)")
    print(f"wrote {OUT_EXPECTED} (revenue {expected['total_revenue']:.2f}, "
          f"products {expected['total_products']}, dates {expected['date_from']}..{expected['date_to']})")


if __name__ == "__main__":
    main()
