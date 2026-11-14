# API reference

Base URL: `http://127.0.0.1:8000`. Interactive schema: `/docs`,
`/openapi.json`. All timestamps are UTC ISO-8601.

Error shape:

```json
{"detail": {"code": "PIPELINE_BUSY", "message": "job … is already running", "fields": []}}
```

## Health and configuration

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health?deep=true` | Mongo status, Hadoop binaries/jar, optional Hive check |
| GET | `/api/mongo/status` | ping, database, collections, transaction estimate |
| GET | `/api/settings` | effective limits, Hive/HDFS paths, execution mode; no secrets |

## Ingestion

| Method | Path | Notes |
|---|---|---|
| POST | `/api/sales/transactions` | manual transaction, 201; duplicate → 409 |
| GET | `/api/sales/transactions` | paged search/filter/sort |
| GET | `/api/sales/transactions/stats` | total / pending / processed |
| GET | `/api/sales/transactions/template.csv` | upload template |
| POST | `/api/sales/transactions/upload` | multipart `file`; per-row duplicate/invalid report |
| GET | `/api/sales/catalog` | 16 products, 6 categories, 5 regions |

Query parameters for the list:

`page` (≥1), `page_size` (1–100), `search` (transaction ID, product ID or
name), `region`, `category`, `processed` (true/false), `date_from`, `date_to`
(bare date includes the whole day), `sort` (`timestamp`, `revenue`, `quantity`,
`product_name`, `region`, `category`; prefix `-` for descending).

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/api/sales/transactions \
  -H 'Content-Type: application/json' \
  -d '{"transaction_id":"DEMO-1","product_id":"P-1001","product_name":"Wireless Keyboard","category":"Electronics","quantity":2,"unit_price":42.50,"region":"North","timestamp":"2026-11-11T09:30:00Z"}'

curl -s -F "file=@datasets/sample_sales_10k.csv" \
  http://127.0.0.1:8000/api/sales/transactions/upload
```

Upload response:

```json
{
  "filename": "sales.csv", "rows_total": 100, "inserted": 95,
  "duplicates": 3, "invalid": 2,
  "duplicate_details": [{"transaction_id": "T1", "error": "…"}],
  "invalid_details": [{"row": 7, "error": "quantity: …", "raw": "T7"}],
  "write_errors": []
}
```

## Simulator

| Method | Path | Body |
|---|---|---|
| POST | `/api/sales/simulator/start` | `{"interval_seconds": 5, "batch_size": 20}` (optional) |
| POST | `/api/sales/simulator/stop` | — |
| GET | `/api/sales/simulator/status` | running, interval, batch size, generated, ticks, last error |

## Hadoop pipeline

| Method | Path | Notes |
|---|---|---|
| POST | `/api/sales/process` | `{"batch_size": 5000}` optional; 202 + `job_id`; 409 if busy |
| GET | `/api/sales/processing/status` | `{running, job}` for the latest job |
| GET | `/api/sales/jobs?limit=20&status=SUCCEEDED` | history without logs |
| GET | `/api/sales/jobs/{job_id}` | stages, details, metrics and logs |

Job stages: `claim`, `hdfs`, `mapreduce`, `hive_fact`, `hive_aggregates`,
`reconcile`. Status values: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`.

## Analytics (pre-aggregated Hive cube)

All analytics endpoints accept `date_from`, `date_to` (`YYYY-MM-DD`),
`product_id`, `category`, `region`.

| Method | Path | Response |
|---|---|---|
| GET | `/api/sales/analytics/overview` | KPIs + daily/monthly/category/region/top-10/all products |
| GET | `/api/sales/analytics/revenue` | KPIs + daily/monthly |
| GET | `/api/sales/analytics/top-products` | top 10 by revenue |
| GET | `/api/sales/analytics/regional` | revenue/quantity/orders per region |
| GET | `/api/sales/analytics/categories` | revenue/quantity per category |
| GET | `/api/sales/analytics/trends?period=daily\|monthly` | trend series only |
| GET | `/api/sales/analytics/mr-results` | latest batch MR product totals |
| GET | `/api/sales/analytics/hive-results` | latest snapshot with six sections |
| GET | `/api/sales/analytics/reconciliation` | match, tolerance, both totals, deltas |
| GET | `/api/sales/analytics/options` | distinct regions/categories/products/dates |

KPI fields: `total_revenue`, `total_transactions`, `total_products`,
`total_quantity`, `average_order_value`. `total_transactions` is the sum of the
fact-cube `orders`, i.e. raw transactions, not fact-row count.

Example:

```bash
curl -s "http://127.0.0.1:8000/api/sales/analytics/overview?category=Electronics&region=North&date_from=2026-08-13&date_to=2026-11-10"
```

## Reports

`GET /api/sales/reports/export/{dataset}.csv`

| Dataset | Columns |
|---|---|
| `transactions` | transaction_id, product_id, product_name, category, quantity, unit_price, revenue, region, timestamp, source, processed, batch_id |
| `products` | product_id, product_name, revenue, quantity, orders |
| `daily` | date, revenue, quantity, orders |
| `monthly` | month, revenue, quantity, orders |
| `regional` | region, revenue, quantity, orders |
| `category` | category, revenue, quantity |
| `hive` | section, key, label, revenue, quantity, orders |

`transactions` also accepts `search` and `processed`. Cells beginning with
`=`, `+`, `-`, `@`, tab or carriage return are prefixed with an apostrophe to
prevent CSV formula injection.

```bash
curl -s -o products.csv \
  "http://127.0.0.1:8000/api/sales/reports/export/products.csv?category=Furniture"
```
