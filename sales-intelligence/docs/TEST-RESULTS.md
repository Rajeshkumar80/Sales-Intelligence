# Test results

**Date:** 2026-11-14
**Host:** Windows 11 + WSL2 Ubuntu 24.04.5, 7.4 GB WSL RAM
**Stack:** Java 17.0.21, Hadoop 3.4.3, Hive 4.1.0, MongoDB Atlas, Python 3.12.3, Node 24.22.2

Every suite below was re-run on 2026-11-14 against the live stack: real Atlas,
HDFS, a YARN NodeManager, MapReduce containers and HiveServer2.

## Automated suites

| # | Suite | Command | Result |
|---|---|---|---|
| 1 | Backend unit | `backend$ ../../.venv/bin/pytest -q` | **12 passed, 1 skipped**, 1 third-party warning, 9.43 s |
| 2 | Java MapReduce | `mapreduce-java$ mvn clean package` | **4 passed** (2 mapper, 2 reducer), 0 failed; BUILD SUCCESS in 11.9 s |
| 3 | Frontend typecheck | `frontend$ npm run typecheck` | **passed** |
| 4 | Frontend production build | `frontend$ npm run build` | **passed**; JS 708.86 kB (198.42 kB gzip), CSS 28.98 kB (5.41 kB gzip) |
| 5 | Dataset round-trip | `scripts/generate-dataset.py` | **passed**; 10,000 rows, revenue 3,034,634.23, 16 products |
| 6 | E2E (19 tests) | see below | **19 passed in 294.46 s** (4:54), 2026-11-14 |

The one skipped test is the E2E module, which is skipped in the default unit run
and executed separately with `BDA_E2E=1`. The warning is Starlette's deprecated
`anyio.abc.BlockingPortal` alias, not application code.

Vite warns that the JS chunk is larger than 500 kB. This is a demo dashboard with
Recharts bundled; it is a warning, not a failure, and does not affect
correctness.

The MapReduce manifest was checked after the rebuild: it contains
`Manifest-Version`, `Created-By` and `Build-Jdk-Spec` only — **no `Main-Class`**,
so `hadoop jar <jar> edu.bda.sales.SalesDriver <in> <out>` passes arguments
correctly. Jar size: 8.2 KB.

## Hadoop / Hive smoke evidence

| Check | Evidence |
|---|---|
| YARN node | `yarn node -list` → **1 RUNNING NodeManager**, 0 running containers at idle |
| MR on YARN | `job_1794414863657_0004` on `datasets/tiny_sales.tsv` |
| MR correctness | output byte-identical to `datasets/expected_product_revenue.tsv` |
| MR counters | product_rows=8, malformed_rows=0, invalid_rows=0 |
| HiveServer2 | deep health `hive.status = ok`; `SELECT 1`, `SHOW TABLES`, `DESCRIBE sales_fact_daily` OK |
| Hive-on-MR insert | `sales_fact_daily PARTITION (batch_id='smoke')` succeeded; partition dropped |
| Hive tables | `transactions_raw`, `sales_fact_daily` exist in `bda_sales` |
| HDFS layout | `/bda/sales/input`, `/bda/sales/revenue` and `/bda/sales/fact` contain per-batch directories for the baseline and later batches |

## End-to-end suite (19 tests)

Command:

```bash
cd ~/BDA-Projects/sales-intelligence/backend
source ~/BDA-Projects/infra/env.sh
BDA_E2E=1 MONGODB_DB=bda_sales_e2e ../../.venv/bin/pytest tests/test_e2e.py -m e2e -x -s
```

Result: **19 passed, 1 warning in 294.46 s**. The suite uses a dedicated
`bda_sales_e2e` database and unique product IDs, spans two dates and two months,
and compares every layer with independently computed expected values. It drops
the test database and the Hive batch partition afterwards. Demo data in
`bda_sales` is untouched.

| # | Test | What it proves | Result |
|---|---|---|---|
| 1 | `test_01_health_and_dependencies` | Atlas, Hadoop jar, Hive reachable | passed |
| 2 | `test_02_manual_transaction` | manual insert, revenue computed, pending state | passed |
| 3 | `test_03_duplicate_transaction_rejected` | unique index returns 409 | passed |
| 4 | `test_04_csv_upload_reports_rows` | 3 inserted, 1 duplicate, 1 invalid reported | passed |
| 5 | `test_05_csv_missing_columns_rejected` | strict CSV schema, 400 | passed |
| 6 | `test_06_transaction_listing_search_sort_pagination` | search/sort/filter/pagination | passed |
| 7 | `test_07_pipeline_start_and_busy_conflict` | 202 start, 409 while active | passed |
| 8 | `test_08_pipeline_completes_all_stages` | six stages succeed, 4 rows / 3 products | passed |
| 9 | `test_09_mapreduce_totals_match_expected` | reducer revenue/quantity/orders per product | passed |
| 10 | `test_10_hive_snapshot_matches_expected` | six Hive sections match expected values | passed |
| 11 | `test_11_reconciliation_matches` | MR = Hive within tolerance, exact counts | passed |
| 12 | `test_12_overview_kpis_and_dimensions` | KPIs, daily/monthly, category/region, options | passed |
| 13 | `test_13_revenue_endpoint_and_filters` | product and date-range filters | passed |
| 14 | `test_14_top_products_order` | top products sorted by revenue | passed |
| 15 | `test_15_regional_analytics` | regional totals and orders | passed |
| 16 | `test_16_sales_trends` | daily/monthly trends, invalid period 400 | passed |
| 17 | `test_17_exports` | seven CSV exports, headers/row counts | passed |
| 18 | `test_18_reprocessing_is_idempotent` | no pending rows → FAILED, no double count | passed |
| 19 | `test_19_simulator_and_job_history` | simulator generates rows, history intact | passed |

## Baseline pipeline evidence

Baseline batch: **10,000 transactions**.

| Item | Evidence |
|---|---|
| Job | `job-23b3f1c040e7`, all six stages `SUCCEEDED`, 278 s |
| Batch | `sales-20261114-130747-60331d` |
| MapReduce | 16 product rows, 0 malformed, 0 invalid |
| Hive fact | 5,413 fact rows in `sales_fact_daily` |
| Reconciliation | MR = Hive; delta `-0.0`; tolerance `$0.17`; 16 products |
| Revenue | `$3,034,634.23` |
| Quantity | `21,154` |
| Transactions | `10,000` |
| Products | `16` |

A later 10-row batch (`job-82a265c7c0fe`, 248 s) also completed all six stages,
which is why the live database contains slightly more than the 10,000-row
baseline.

## Live demo snapshot (2026-11-14)

| Item | Value |
|---|---|
| MongoDB transactions | 10,040 total · 10,010 processed · 30 pending |
| Overview revenue | `$3,038,289.26` |
| Overview quantity | `21,176` |
| Overview transactions | `10,010` |
| Overview products | `16` |
| Average order value | `$303.53` |
| Latest reconciliation batch | `sales-20261114-155405-36f5af` |
| Latest reconciliation | match = true, delta = `0.0`, tolerance = `0.08`, MR = Hive = `$3,655.03`, 7 products, 22 units, 10 orders |
| Job history | `job-82a265c7c0fe` SUCCEEDED 248 s · `job-23b3f1c040e7` SUCCEEDED 278 s |

The 30 pending rows were produced by the simulator and are intentionally waiting
for the next batch. They are not included in the overview KPIs, which read the
materialised Hive cube.

## Manual UI verification

Chrome against the live Vite app (<http://127.0.0.1:5173>):

- **All eight pages render with real data** — Overview, Sales Analytics,
  Transactions, Data Ingestion, Hadoop Jobs, Hive Analytics, Reports and Settings.
  No console errors were reported.
- **Theme** — dark background is pure black (`#000000`), light background is
  `#fafafa`; the toggle switches and persists the preference in `localStorage`.
- **Sales Analytics filters** — selecting region `North` changed the KPIs to
  `$587,511.59` revenue, `4,173` units and `1,958` transactions; `Reset filters`
  restored `$3,038,289.26`, `21,176` and `10,010`.
- **Transactions** — search `P-1001` returned 25 matching rows on page 1 of 28;
  `Next` moved to page 2; sorting by `Revenue` reordered the table.
- **Hadoop Jobs** — both jobs render with the six-stage timeline
  (Claim rows → HDFS write → MapReduce job → Hive fact table → Hive aggregates →
  Reconciliation).
- **Hive Analytics** — latest batch, MapReduce output rows and the green
  reconciliation card render from the snapshot.
- **Settings** — runtime configuration renders immediately; the deep Hive health
  check completes without blocking the page; no credentials are displayed.
- **Ingestion and Reports** — manual form, CSV upload, simulator controls and
  export cards render; their API behaviour is covered by the E2E suite.

Screenshots: `docs/screenshots/overview.jpg`, `analytics.jpg`,
`transactions.jpg`, `jobs.jpg`, `hive-analytics.jpg`.

## Known warnings and limits

- Vite chunk-size warning: expected with Recharts in a single demo bundle.
- Starlette deprecation warning: third-party test client alias, not app code.
- Single-node pseudo-distributed Hadoop on WSL2; not a multi-machine cluster.
- The checked-in dataset is synthetic and demo-sized (10,000 rows).
