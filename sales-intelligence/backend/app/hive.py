"""HiveServer2 access through beeline. One beeline call per logical query set."""

import csv
import io
import tempfile
from pathlib import Path

from . import config
from .hadoop import HadoopError, _run


def run_sql(script: str, timeout: int = 1800) -> list[list[str]]:
    config.STAGING_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, dir=config.STAGING_DIR) as handle:
        handle.write(script)
        sql_file = Path(handle.name)
    try:
        output = _run(
            [
                str(config.BEELINE_BIN),
                "-u",
                config.HIVE_URL,
                "-n",
                "rajesh",
                "--silent=true",
                # csv2 leaves commas unquoted, which corrupts names like "Bookshelf, 5 Tier"
                "--outputformat=tsv2",
                "--showHeader=false",
                "-f",
                str(sql_file),
            ],
            timeout=timeout,
        )
    finally:
        sql_file.unlink(missing_ok=True)

    rows = []
    for line in output.splitlines():
        if not line.strip() or line.startswith("SLF4J") or line.startswith("Warning:"):
            continue
        rows.append(next(csv.reader([line], delimiter="\t")))
    return rows


def add_partition(batch_id: str) -> None:
    run_sql(f"ALTER TABLE {config.HIVE_DB}.transactions_raw ADD IF NOT EXISTS PARTITION (batch_id='{batch_id}') "
            f"LOCATION '{config.HDFS_INPUT}/batch_id={batch_id}';\n", timeout=300)


def build_fact(batch_id: str) -> None:
    """Materialise the (date, product, category, region) cube as a Hive-on-MR job."""
    sql = f"""
SET hive.exec.dynamic.partition=true;
INSERT INTO TABLE {config.HIVE_DB}.sales_fact_daily PARTITION (batch_id='{batch_id}')
SELECT from_unixtime(CAST(timestamp_ms / 1000 AS BIGINT), 'yyyy-MM-dd') AS sale_date,
       product_id,
       max(product_name) AS product_name,
       category,
       region,
       sum(quantity * unit_price) AS revenue,
       sum(quantity) AS quantity,
       count(1) AS orders
FROM {config.HIVE_DB}.transactions_raw
WHERE batch_id = '{batch_id}'
GROUP BY from_unixtime(CAST(timestamp_ms / 1000 AS BIGINT), 'yyyy-MM-dd'), product_id, category, region;
"""
    run_sql(sql, timeout=2400)


SECTIONS = ("product", "category", "region", "daily", "monthly", "total")


def aggregates(batch_id: str) -> list[dict]:
    """Product / category / region / daily / monthly / total aggregates in one query."""
    base = f"FROM {config.HIVE_DB}.sales_fact_daily WHERE batch_id = '{batch_id}'"
    parts = [
        f"SELECT 'product' AS section, product_id AS k, max(product_name) AS label, "
        f"sum(revenue) AS revenue, sum(quantity) AS quantity, sum(orders) AS orders {base} GROUP BY product_id",
        f"SELECT 'category', category, category, sum(revenue), sum(quantity), sum(orders) {base} GROUP BY category",
        f"SELECT 'region', region, region, sum(revenue), sum(quantity), sum(orders) {base} GROUP BY region",
        f"SELECT 'daily', sale_date, sale_date, sum(revenue), sum(quantity), sum(orders) {base} GROUP BY sale_date",
        f"SELECT 'monthly', substr(sale_date, 1, 7), substr(sale_date, 1, 7), sum(revenue), sum(quantity), sum(orders) "
        f"{base} GROUP BY substr(sale_date, 1, 7)",
        f"SELECT 'total', 'ALL', 'ALL', sum(revenue), sum(quantity), sum(orders) {base}",
    ]
    rows = run_sql(";\n".join(parts) + ";\n")
    result = []
    for row in rows:
        if len(row) != 6 or row[0] not in SECTIONS:
            continue
        result.append(
            {
                "section": row[0],
                "key": row[1],
                "label": row[2],
                "revenue": _num(row[3]),
                "quantity": _num(row[4]),
                "orders": _num(row[5]),
            }
        )
    return result


def fact_rows(batch_id: str) -> list[dict]:
    rows = run_sql(
        f"SELECT sale_date, product_id, product_name, category, region, revenue, quantity, orders "
        f"FROM {config.HIVE_DB}.sales_fact_daily WHERE batch_id = '{batch_id}';\n"
    )
    result = []
    for row in rows:
        if len(row) != 8:
            continue
        result.append(
            {
                "sale_date": row[0],
                "product_id": row[1],
                "product_name": row[2],
                "category": row[3],
                "region": row[4],
                "revenue": _num(row[5]),
                "quantity": _num(row[6]),
                "orders": _num(row[7]),
            }
        )
    return result


def drop_batch(batch_id: str) -> None:
    try:
        run_sql(
            f"ALTER TABLE {config.HIVE_DB}.sales_fact_daily DROP IF EXISTS PARTITION (batch_id='{batch_id}');\n"
            f"ALTER TABLE {config.HIVE_DB}.transactions_raw DROP IF EXISTS PARTITION (batch_id='{batch_id}');\n",
            timeout=300,
        )
    except HadoopError:
        pass  # best-effort cleanup of a failed batch


def _num(value: str) -> float:
    text = (value or "").strip()
    if text in ("", "NULL", "\\N"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def hive_alive() -> bool:
    try:
        return bool(run_sql("SELECT 1;\n", timeout=120))
    except (HadoopError, OSError):
        return False
