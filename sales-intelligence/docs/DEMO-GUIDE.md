# Demo guide and viva notes

## Before the demo (5 minutes)

```bash
cd ~/BDA-Projects
./infra/scripts/start-hadoop.sh
./infra/scripts/start-hive.sh
./sales-intelligence/scripts/start-backend.sh
./sales-intelligence/scripts/start-frontend.sh
./infra/scripts/status.sh
curl -s http://127.0.0.1:8000/api/health?deep=true | python3 -m json.tool
```

- Open <http://127.0.0.1:5173> and <http://127.0.0.1:8000/docs>.
- Keep <http://127.0.0.1:8088> (YARN) and <http://127.0.0.1:19888> (JobHistory)
  open in separate tabs.
- Confirm `.env` has a valid Atlas password and the current IP is allowed in
  Atlas. Never show the `.env` contents on screen.
- Optional clean state: drop the `bda_sales` demo data only if you intend to
  re-seed; the E2E suite uses a separate `bda_sales_e2e` database.

## Suggested 12-minute script

1. **Architecture (1 min).** Show the README diagram: React → FastAPI →
   MongoDB Atlas; FastAPI stages a batch to HDFS; Java MapReduce runs on YARN;
   Hive builds the ORC fact cube; the dashboard reads pre-aggregated rows.
   State clearly: single-node pseudo-distributed, real YARN containers.
2. **Health (30 s).** `/api/health?deep=true`: Mongo ok, Hadoop binaries and jar
   present, Hive ok.
3. **Manual ingestion (1 min).** Data Ingestion → add a transaction. Then add the
   same `transaction_id` again and show the 409 duplicate error.
4. **CSV upload (1.5 min).** Upload `datasets/sample_sales_10k.csv` or a small
   file containing one invalid row and one duplicate. Show the per-row report
   (inserted / duplicates / invalid) and the transaction table.
5. **Simulator (30 s).** Start with interval 2 s and batch 10; watch the pending
   count grow; stop it.
6. **Hadoop job (3 min).** Jobs → set rows per batch 12000 → Process now. Walk
   through the live stages: claim → hdfs → mapreduce → hive_fact →
   hive_aggregates → reconcile. Switch to the YARN UI and show the application
   and containers. Open JobHistory if time allows.
7. **Dashboard (2 min).** Overview shows the five KPIs and charts computed from
   the cube. Analytics: change region/category/date filters; show the charts
   update from Mongo aggregation over Hive rows. Transactions: search, sort,
   paginate, filter processed/pending.
8. **Hive vs MR (1 min).** Hive Analytics: six sections and the reconciliation
   card. Point out `mr_revenue`, `hive_revenue`, delta, tolerance, match.
9. **Reports (30 s).** Download products/daily CSV; open it. Mention
   formula-injection protection.
10. **Settings (30 s).** Show execution mode, Hive/HDFS paths, limits and binary
    health. Confirm no credentials are displayed.

## Exact commands used during the demo

```bash
# health
curl -s http://127.0.0.1:8000/api/health?deep=true | python3 -m json.tool

# manual transaction
curl -s -X POST http://127.0.0.1:8000/api/sales/transactions \
  -H 'Content-Type: application/json' \
  -d '{"transaction_id":"VIVA-1","product_id":"P-1001","product_name":"Wireless Keyboard","category":"Electronics","quantity":2,"unit_price":42.50,"region":"North","timestamp":"2026-11-11T09:30:00Z"}'

# 10k CSV
curl -s -F "file=@sales-intelligence/datasets/sample_sales_10k.csv" \
  http://127.0.0.1:8000/api/sales/transactions/upload

# run the pipeline (batch larger than pending rows)
curl -s -X POST http://127.0.0.1:8000/api/sales/process \
  -H 'Content-Type: application/json' -d '{"batch_size":12000}'

# poll
curl -s http://127.0.0.1:8000/api/sales/processing/status | python3 -m json.tool

# reconciliation
curl -s http://127.0.0.1:8000/api/sales/analytics/reconciliation | python3 -m json.tool

# exports
curl -s -o products.csv "http://127.0.0.1:8000/api/sales/reports/export/products.csv"
```

## Viva questions and answers

**1. Is this real Hadoop or a simulation?**
Real Apache Hadoop 3.4.3 on HDFS and YARN. `SalesDriver` is submitted with
`hadoop jar`; map/reduce tasks run in YARN containers. The single-node
pseudo-distributed mode is stated honestly in the UI and docs.

**2. What exactly does the mapper emit?**
Key `product_id`; value `(product_name, quantity × unit_price, quantity, 1)`.
Malformed and invalid rows increment custom counters instead of disappearing.

**3. What does the reducer do?**
Shuffle/sort groups values by product ID; the reducer sums revenue, quantity and
order count, rounds product revenue to 2 decimals, and writes TSV.

**4. Why is there no combiner?**
The reducer is already associative and the demo batches are small. A combiner
could reduce shuffle traffic and would be the next optimisation, but it would
not change correctness.

**5. Why does the jar have no `Main-Class`?**
With a manifest `Main-Class`, `hadoop jar sales-mapreduce.jar
edu.bda.sales.SalesDriver …` treats the class name as an application argument.
Removing the manifest entry keeps the standard Hadoop invocation working.

**6. Why Hive if MapReduce already computes revenue?**
MR answers per-product totals. Hive answers multi-dimensional questions
(date × product × category × region) and materialises an ORC cube, so dashboard
filters do not rerun a job. The two results are reconciled for trust.

**7. External vs managed Hive tables?**
Both tables are external, so Hive does not own the data directory and dropping a
table cannot delete the raw files. Partitions are registered per batch.

**8. Why partition by `batch_id`?**
One partition per pipeline run makes inserts, drops and failure cleanup
isolated and idempotent. A failed batch drops only its own partition.

**9. What is the fact-cube grain?**
`(sale_date, product_id, category, region)`, with revenue, quantity and order
count as measures. This supports all required filters without raw scans.

**10. How is double counting prevented?**
Unique transaction index; atomic batch claim with `batch_id=null`; one batch per
Hive partition; deterministic analytics IDs with upsert; `processed=true` only
after the whole pipeline succeeds; failed batches release their claim.

**11. What happens if the API restarts mid-job?**
Startup recovery marks RUNNING jobs FAILED, releases their claimed rows and
clears the pipeline lock. The rows are retryable; partial MR/fact/snapshot
writes are removed by rollback.

**12. Why can MR and Hive totals differ by a cent?**
The reducer rounds per product; Hive sums unrounded fact revenue. Reconciliation
uses `0.01 × product_count + 0.01` tolerance and requires exact quantity/order
matches. The delta is shown, not hidden.

**13. Why MongoDB Atlas and not local MongoDB?**
The assignment requires MongoDB integration and Atlas was chosen. The backend
fails loudly if credentials/network are wrong; it does not silently fall back to
a local database.

**14. How are credentials protected?**
Only in `backend/.env` (gitignored, mode 600). The URI is constructed at call
time, the password is URL-encoded, and no endpoint or log returns it. The
frontend calls relative `/api` paths through Vite, so no secret is in the
bundle.

**15. Why does the dashboard not query Hive on every click?**
Hive-on-MR has multi-second latency. The pipeline copies Hive's fact rows into
MongoDB; dashboard filters are Mongo aggregation pipelines over pre-aggregated
rows. Hive remains the computation engine, not the interactive serving layer.

**16. What is genuinely distributed here?**
HDFS blocks, YARN scheduling and separate map/reduce JVMs on one host. It is not
a multi-machine cluster; scale-out would add DataNode/NodeManager hosts.

**17. How do you know the dashboard numbers are not fake?**
Every endpoint reads Mongo collections written by the pipeline. The E2E suite
ingests known rows, runs the pipeline, and compares MR/Hive/API results with
independently computed expected values. Empty states appear before any batch.

**18. What are the main limitations?**
Pseudo-distributed single node; Derby metastore with one writer; no auth on the
local demo API; Hive latency means the cube is materialised per batch; no
multi-tenant security. These are stated in the README.

## Likely failure questions

- **"What if Atlas is down?"** `/api/health` reports degraded; ingestion and
  pipeline endpoints return 503 with a readable error. No silent local fallback.
- **"What if Hive is down?"** Pipeline fails at `hive_fact`; rollback releases
  the batch; job detail shows the failing stage and error.
- **"What if the same CSV is uploaded twice?"** Every row is reported as a
  duplicate; inserted count is 0; no data is double counted.
- **"Can you prove YARN ran it?"** YARN UI application ID, JobHistory job, MR
  counters in the job stage, and the `part-r-00000` file in HDFS.
