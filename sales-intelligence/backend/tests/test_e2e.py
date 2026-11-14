"""19 end-to-end tests against real Atlas, HDFS/YARN and Hive.

Run with a dedicated database so demo data is never touched:

    BDA_E2E=1 MONGODB_DB=bda_sales_e2e pytest tests/test_e2e.py -m e2e -x -s
"""

import csv
import io
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

import pytest

if os.getenv("BDA_E2E") != "1":
    pytest.skip("E2E needs BDA_E2E=1 and a running Hadoop/Hive/Atlas stack", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, hadoop, hive  # noqa: E402
from app.main import app  # noqa: E402

pytestmark = pytest.mark.e2e

TAG = f"E2E{uuid.uuid4().hex[:6].upper()}"
CATEGORY = f"E2E Category {TAG}"
NORTH = f"E2E North {TAG}"
SOUTH = f"E2E South {TAG}"
PRODUCTS = {
    "A": (f"P-{TAG}-A", f"E2E Widget A {TAG}"),
    "B": (f"P-{TAG}-B", f"E2E Widget B, {TAG}"),  # comma guards beeline csv parsing
    "C": (f"P-{TAG}-C", f"E2E Widget C {TAG}"),
}
TIMEOUT = 900


@pytest.fixture(scope="module")
def ctx():
    assert config.MONGO_DB == "bda_sales_e2e", "Refusing to run E2E outside bda_sales_e2e"
    db.get_db().client.drop_database(config.MONGO_DB)
    db.ensure_indexes()
    state = {"ledger": [], "batch_id": None, "job_id": None}
    try:
        with TestClient(app) as client:
            state["client"] = client
            yield state
    finally:
        if state["batch_id"]:
            for cleanup in (
                lambda: hive.drop_batch(state["batch_id"]),
                lambda: hadoop.hdfs_rm(f"{config.HDFS_INPUT}/batch_id={state['batch_id']}"),
                lambda: hadoop.hdfs_rm(f"{config.HDFS_REVENUE}/batch_id={state['batch_id']}"),
            ):
                try:
                    cleanup()
                except Exception as exc:  # cleanup must not hide test results
                    print(f"[cleanup] {exc}")
        db.get_db().client.drop_database(config.MONGO_DB)


def transaction(key: str, txn_id: str, quantity: int, price: float, region: str,
                date: str, hour: int = 10) -> dict:
    product_id, product_name = PRODUCTS[key]
    return {
        "transaction_id": txn_id,
        "product_id": product_id,
        "product_name": product_name,
        "category": CATEGORY,
        "quantity": quantity,
        "unit_price": price,
        "region": region,
        "timestamp": f"{date}T{hour:02d}:00:00Z",
    }


def remember(ctx, payload: dict) -> None:
    ctx["ledger"].append({
        **payload,
        "timestamp": datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")),
        "revenue": payload["quantity"] * payload["unit_price"],
    })


def totals(rows):
    revenue = round(sum(row["quantity"] * row["unit_price"] for row in rows), 2)
    orders = len(rows)
    return {
        "revenue": revenue,
        "quantity": sum(row["quantity"] for row in rows),
        "orders": orders,
        "products": len({row["product_id"] for row in rows}),
        "average": round(revenue / orders, 2) if orders else 0.0,
    }


def by_product(rows):
    result = defaultdict(lambda: {"revenue": 0.0, "quantity": 0, "orders": 0})
    for row in rows:
        bucket = result[row["product_id"]]
        bucket["revenue"] += row["quantity"] * row["unit_price"]
        bucket["quantity"] += row["quantity"]
        bucket["orders"] += 1
    return {key: {**value, "revenue": round(value["revenue"], 2)} for key, value in result.items()}


def grouped(rows, key):
    result = defaultdict(lambda: {"revenue": 0.0, "quantity": 0, "orders": 0})
    for row in rows:
        bucket = result[key(row)]
        bucket["revenue"] += row["quantity"] * row["unit_price"]
        bucket["quantity"] += row["quantity"]
        bucket["orders"] += 1
    return {name: {**value, "revenue": round(value["revenue"], 2)} for name, value in result.items()}


def wait_for_job(client, job_id, statuses=("SUCCEEDED", "FAILED"), timeout=TIMEOUT):
    deadline = time.time() + timeout
    job = None
    while time.time() < deadline:
        job = client.get(f"/api/sales/jobs/{job_id}").json()
        if job.get("status") in statuses:
            return job
        time.sleep(3)
    pytest.fail(f"job {job_id} did not finish in {timeout}s: {job}")


def test_01_health_and_dependencies(ctx):
    body = ctx["client"].get("/api/health?deep=true").json()
    assert body["components"]["mongodb"]["status"] == "ok"
    assert body["components"]["hadoop"]["jar_built"] is True
    assert body["components"]["hive"]["status"] == "ok"
    assert body["status"] == "ok"


def test_02_manual_transaction(ctx):
    payload = transaction("A", f"{TAG}-M1", 2, 12.50, NORTH, "2026-09-30")
    response = ctx["client"].post("/api/sales/transactions", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["revenue"] == 25.0
    assert body["processed"] is False and body["source"] == "manual"
    remember(ctx, payload)


def test_03_duplicate_transaction_rejected(ctx):
    payload = transaction("A", f"{TAG}-M1", 2, 12.50, NORTH, "2026-09-30")
    response = ctx["client"].post("/api/sales/transactions", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DUPLICATE_TRANSACTION_ID"


def test_04_csv_upload_reports_rows(ctx):
    rows = [
        transaction("B", f"{TAG}-C1", 3, 10.00, NORTH, "2026-09-30"),
        transaction("B", f"{TAG}-C2", 1, 9.00, SOUTH, "2026-10-01"),
        transaction("C", f"{TAG}-C3", 4, 5.00, SOUTH, "2026-10-01"),
    ]
    invalid = transaction("A", f"{TAG}-BAD", 0, 12.50, NORTH, "2026-10-01")
    duplicate = transaction("A", f"{TAG}-M1", 2, 12.50, NORTH, "2026-09-30")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows + [invalid, duplicate]:
        writer.writerow(row)
    response = ctx["client"].post(
        "/api/sales/transactions/upload",
        files={"file": ("e2e.csv", buffer.getvalue().encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["rows_total"] == 5
    assert report["inserted"] == 3
    assert report["invalid"] == 1
    assert report["duplicates"] == 1
    assert report["duplicate_details"][0]["transaction_id"] == f"{TAG}-M1"
    for row in rows:
        remember(ctx, row)


def test_05_csv_missing_columns_rejected(ctx):
    response = ctx["client"].post(
        "/api/sales/transactions/upload",
        files={"file": ("bad.csv", b"transaction_id,product_id\nT1,P-1\n", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_CSV"


def test_06_transaction_listing_search_sort_pagination(ctx):
    client = ctx["client"]
    listing = client.get("/api/sales/transactions", params={"search": TAG, "page_size": 2}).json()
    assert listing["total"] == 4
    assert listing["pages"] == 2 and len(listing["items"]) == 2
    page_two = client.get("/api/sales/transactions",
                          params={"search": TAG, "page_size": 2, "page": 2}).json()
    assert len(page_two["items"]) == 2
    assert not ({item["transaction_id"] for item in listing["items"]}
                & {item["transaction_id"] for item in page_two["items"]})

    south = client.get("/api/sales/transactions", params={"category": CATEGORY, "region": SOUTH}).json()
    assert south["total"] == 2
    ordered = client.get("/api/sales/transactions", params={"search": TAG, "sort": "-revenue"}).json()
    assert ordered["items"][0]["transaction_id"] == f"{TAG}-C1"
    pending = client.get("/api/sales/transactions", params={"search": TAG, "processed": "false"}).json()
    assert pending["total"] == 4


def test_07_pipeline_start_and_busy_conflict(ctx):
    client = ctx["client"]
    first = client.post("/api/sales/process", json={"batch_size": 100})
    assert first.status_code == 202, first.text
    ctx["job_id"] = first.json()["job_id"]
    ctx["batch_id"] = first.json()["batch_id"]
    second = client.post("/api/sales/process", json={"batch_size": 100})
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "PIPELINE_BUSY"


def test_08_pipeline_completes_all_stages(ctx):
    job = wait_for_job(ctx["client"], ctx["job_id"])
    if job["status"] != "SUCCEEDED":
        print("logs:", job.get("logs"))
    assert job["status"] == "SUCCEEDED", job.get("error")
    stage_names = [stage["name"] for stage in job["stages"]]
    assert stage_names == ["claim", "hdfs", "mapreduce", "hive_fact", "hive_aggregates", "reconcile"]
    assert all(stage["status"] == "SUCCEEDED" for stage in job["stages"])
    assert job["metrics"]["transactions"] == len(ctx["ledger"]) == 4
    assert job["metrics"]["products"] == 3
    assert job["duration_ms"] > 0


def test_09_mapreduce_totals_match_expected(ctx):
    body = ctx["client"].get("/api/sales/analytics/mr-results").json()
    assert body["batch_id"] == ctx["batch_id"]
    expected = by_product(ctx["ledger"])
    items = {item["product_id"]: item for item in body["items"] if item["product_id"] in expected}
    assert set(items) == set(expected)
    for product_id, exp in expected.items():
        assert items[product_id]["quantity"] == exp["quantity"]
        assert items[product_id]["orders"] == exp["orders"]
        assert abs(items[product_id]["revenue"] - exp["revenue"]) <= 0.01
    revenues = [item["revenue"] for item in body["items"] if item["product_id"] in expected]
    assert revenues == sorted(revenues, reverse=True)


def test_10_hive_snapshot_matches_expected(ctx):
    snapshot = ctx["client"].get("/api/sales/analytics/hive-results").json()["snapshot"]
    assert snapshot["batch_id"] == ctx["batch_id"]
    assert snapshot["mr_counters"] == {"product_rows": 4, "malformed_rows": 0, "invalid_rows": 0}
    sections = defaultdict(dict)
    for row in snapshot["hive_results"]:
        sections[row["section"]][row["key"]] = row

    expected_products = by_product(ctx["ledger"])
    for product_id, exp in expected_products.items():
        row = sections["product"][product_id]
        assert row["quantity"] == exp["quantity"] and row["orders"] == exp["orders"]
        assert abs(row["revenue"] - exp["revenue"]) <= 0.01

    total = totals(ctx["ledger"])
    assert sections["total"]["ALL"]["quantity"] == total["quantity"]
    assert sections["total"]["ALL"]["orders"] == total["orders"]
    assert abs(sections["total"]["ALL"]["revenue"] - total["revenue"]) <= 0.01
    assert sections["category"][CATEGORY]["quantity"] == total["quantity"]
    assert sections["region"][NORTH]["orders"] == 2
    assert sections["region"][SOUTH]["orders"] == 2
    assert abs(sections["daily"]["2026-09-30"]["revenue"] - 55.0) <= 0.01
    assert abs(sections["daily"]["2026-10-01"]["revenue"] - 29.0) <= 0.01
    assert abs(sections["monthly"]["2026-09"]["revenue"] - 55.0) <= 0.01
    assert abs(sections["monthly"]["2026-10"]["revenue"] - 29.0) <= 0.01


def test_11_reconciliation_matches(ctx):
    body = ctx["client"].get("/api/sales/analytics/reconciliation").json()
    rec = body["reconciliation"]
    expected = totals(ctx["ledger"])
    assert body["batch_id"] == ctx["batch_id"]
    assert rec["match"] is True
    assert rec["products"] == 3
    assert abs(rec["mr_revenue"] - expected["revenue"]) <= 0.01
    assert abs(rec["hive_revenue"] - expected["revenue"]) <= 0.01
    assert abs(rec["delta_revenue"]) <= rec["tolerance"]
    assert rec["mr_quantity"] == rec["hive_quantity"] == expected["quantity"]
    assert rec["mr_orders"] == rec["hive_orders"] == expected["orders"]


def test_12_overview_kpis_and_dimensions(ctx):
    client = ctx["client"]
    body = client.get("/api/sales/analytics/overview", params={"category": CATEGORY}).json()
    expected = totals(ctx["ledger"])
    assert body["has_data"] is True
    assert abs(body["kpis"]["total_revenue"] - expected["revenue"]) <= 0.01
    assert body["kpis"]["total_transactions"] == expected["orders"]
    assert body["kpis"]["total_products"] == expected["products"]
    assert body["kpis"]["total_quantity"] == expected["quantity"]
    assert abs(body["kpis"]["average_order_value"] - expected["average"]) <= 0.01
    assert [point["date"] for point in body["daily"]] == ["2026-09-30", "2026-10-01"]
    assert [point["month"] for point in body["monthly"]] == ["2026-09", "2026-10"]
    assert len(body["category"]) == 1 and body["category"][0]["category"] == CATEGORY
    assert {row["region"] for row in body["region"]} == {NORTH, SOUTH}
    assert len(body["top_products"]) == 3 and len(body["all_products"]) == 3

    options = client.get("/api/sales/analytics/options").json()
    assert CATEGORY in options["categories"]
    assert {NORTH, SOUTH}.issubset(set(options["regions"]))
    assert set(PRODUCTS[key][0] for key in PRODUCTS).issubset(
        {item["product_id"] for item in options["products"]})
    assert {"2026-09-30", "2026-10-01"}.issubset(set(options["dates"]))


def test_13_revenue_endpoint_and_filters(ctx):
    client = ctx["client"]
    product_id = PRODUCTS["A"][0]
    body = client.get("/api/sales/analytics/revenue", params={"product_id": product_id}).json()
    assert body["kpis"]["total_transactions"] == 1
    assert body["kpis"]["total_revenue"] == 25.0
    assert body["daily"] == [{"date": "2026-09-30", "revenue": 25.0, "quantity": 2, "orders": 1}]

    day = client.get("/api/sales/analytics/revenue", params={
        "category": CATEGORY, "date_from": "2026-10-01", "date_to": "2026-10-01",
    }).json()
    assert day["kpis"]["total_transactions"] == 2
    assert day["kpis"]["total_quantity"] == 5
    assert abs(day["kpis"]["total_revenue"] - 29.0) <= 0.01


def test_14_top_products_order(ctx):
    body = ctx["client"].get("/api/sales/analytics/top-products", params={"category": CATEGORY}).json()
    expected = by_product(ctx["ledger"])
    ids = [row["product_id"] for row in body["items"]]
    assert ids == sorted(expected, key=lambda pid: (-expected[pid]["revenue"], pid))
    assert abs(body["items"][0]["revenue"] - 39.0) <= 0.01


def test_15_regional_analytics(ctx):
    body = ctx["client"].get("/api/sales/analytics/regional", params={"category": CATEGORY}).json()
    regions = {row["region"]: row for row in body["items"]}
    expected = grouped(ctx["ledger"], lambda row: row["region"])
    assert set(regions) == set(expected)
    for region, exp in expected.items():
        assert regions[region]["quantity"] == exp["quantity"]
        assert regions[region]["orders"] == exp["orders"]
        assert abs(regions[region]["revenue"] - exp["revenue"]) <= 0.01


def test_16_sales_trends(ctx):
    client = ctx["client"]
    daily = client.get("/api/sales/analytics/trends",
                       params={"period": "daily", "category": CATEGORY}).json()
    assert daily["period"] == "daily"
    assert [point["date"] for point in daily["items"]] == ["2026-09-30", "2026-10-01"]
    monthly = client.get("/api/sales/analytics/trends",
                         params={"period": "monthly", "category": CATEGORY}).json()
    assert [point["month"] for point in monthly["items"]] == ["2026-09", "2026-10"]
    bad = client.get("/api/sales/analytics/trends", params={"period": "weekly"})
    assert bad.status_code == 400
    assert bad.json()["detail"]["code"] == "INVALID_PERIOD"


def test_17_exports(ctx):
    client = ctx["client"]
    cases = {
        "transactions": (12, 4),
        "products": (5, 3),
        "daily": (4, 2),
        "monthly": (4, 2),
        "regional": (4, 2),
        "category": (3, 1),
        "hive": (6, 11),
    }
    for dataset, (columns, rows) in cases.items():
        response = client.get(f"/api/sales/reports/export/{dataset}.csv",
                              params={"category": CATEGORY})
        assert response.status_code == 200, (dataset, response.text)
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        parsed = list(csv.reader(io.StringIO(response.text)))
        assert len(parsed[0]) == columns, dataset
        assert len(parsed) - 1 == rows, dataset
    missing = client.get("/api/sales/reports/export/unknown.csv")
    assert missing.status_code == 404


def test_18_reprocessing_is_idempotent(ctx):
    client = ctx["client"]
    stats = client.get("/api/sales/transactions/stats").json()
    assert stats == {"total": 4, "pending": 0, "processed": 4}

    second = client.post("/api/sales/process", json={"batch_size": 100})
    assert second.status_code == 202
    job = wait_for_job(client, second.json()["job_id"])
    assert job["status"] == "FAILED"
    assert "no unprocessed transactions" in job["error"]

    database = db.get_db()
    assert database[db.BATCHES].count_documents({}) == 1
    assert database[db.MR_PRODUCT].count_documents({"batch_id": ctx["batch_id"]}) == 3
    assert database[db.FACT_DAILY].count_documents({"batch_id": ctx["batch_id"]}) == 4
    assert database[db.SNAPSHOTS].count_documents({}) == 1

    body = client.get("/api/sales/analytics/overview", params={"category": CATEGORY}).json()
    assert abs(body["kpis"]["total_revenue"] - 84.0) <= 0.01

    history = client.get("/api/sales/jobs", params={"limit": 10}).json()["items"]
    assert len(history) == 2
    assert {item["status"] for item in history} == {"SUCCEEDED", "FAILED"}


def test_19_simulator_and_job_history(ctx):
    client = ctx["client"]
    started = client.post("/api/sales/simulator/start",
                          json={"interval_seconds": 1, "batch_size": 5}).json()
    assert started["running"] is True
    time.sleep(2.5)
    status = client.get("/api/sales/simulator/status").json()
    assert status["running"] is True
    assert status["generated"] >= 5 and status["ticks"] >= 1
    stopped = client.post("/api/sales/simulator/stop").json()
    assert stopped["running"] is False

    database = db.get_db()
    generated = list(database[db.TRANSACTIONS].find({"source": "simulator"}))
    assert len(generated) >= 5
    for row in generated:
        assert row["quantity"] >= 1 and row["unit_price"] > 0
        assert row["category"] and row["region"]
    assert database[db.TRANSACTIONS].count_documents({"processed": False}) >= 5

    history = client.get("/api/sales/jobs", params={"limit": 20}).json()["items"]
    assert len(history) == 2
