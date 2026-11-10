# M2-02 — Authenticated Pagination Performance Results

**Project:** Client Intake & Case Tracking API  
**Date:** 2026-11-09  
**Issue:** [#91](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/91)  
**Setup/runbook:** [Isolated performance environment](performance-environment-m2-02.md)  
**Data:** [Comparison CSV](pagination-benchmark-2026-11-09.csv)  
**Earlier baseline:** [M2-01](api-baseline-2026-11.md)

## Objective and method

Determine how `GET /cases` latency changes when (A) retrieving ten cases, (B) retrieving 100 cases, and (C) retrieving ten cases from page 50.

- **Test data:** 500 synthetic clients; 100 staff accounts and one performance admin; 1,000 cases; 1,000 case-user assignments. 434 clients and all 100 staff had assigned cases.
- **Application:** Flask, SQLAlchemy, PostgreSQL; two Gunicorn sync workers on Ubuntu 26.04 LTS (Intel i5 5th gen / 8 GB RAM).
- **Connection:** Locust on Windows → SSH local forward `127.0.0.1:18001` → isolated Ubuntu Gunicorn `127.0.0.1:8001` → Flask/PostgreSQL. Nginx and Cloudflare were not in this request path.
- **Load:** 10 virtual users, nominally 3 minutes per run; saved Locust HTMLs each report 2m59s. Each Locust virtual user authenticates once with the **same synthetic admin identity**. Statistics below include only GET requests, excluding `POST /login`.
- **Think time:** script defaults to a random 1–3 seconds between tasks. The HTML exports do *not* record `PERF_WAIT_MIN` / `PERF_WAIT_MAX` overrides, so the precise effective setting cannot be independently verified from reports alone.

## Results — GET /cases

| Metric | A: page=1, limit=10 | B: page=1, limit=100 | C: page=50, limit=10 |
|---|---:|---:|---:|
| GET requests | 841 | 670 | 834 |
| GET failures | 0 | 0 | 0 |
| Mean | 103.25 ms | 647.63 ms | 98.75 ms |
| Median (P50) | 97 ms | 580 ms | 90 ms |
| P95 | 160 ms | 1,200 ms | 180 ms |
| P99 | 280 ms | 1,400 ms | 270 ms |
| Maximum | 532 ms | 1,946 ms | 407 ms |
| GET throughput | 4.68 req/s | 3.72 req/s | 4.63 req/s |
| Mean response body | 7,590 bytes | 75,069 bytes | 7,585 bytes |

All three reports additionally show ten successful `POST /login` requests per run and no login failures. In total, **2,345 GET requests succeeded without reported failures**.

## Interpretation

1. **Increasing page size from 10 to 100 increased average latency about 6.27×**, P95 7.5×, and response size about 9.89×. Observed GET throughput dropped about 20% under this workload. This is the clearest performance signal.
2. **Deep pagination did not show a clear penalty at this dataset size.** The average for page 50/limit 10 (98.75 ms) was close to page 1/limit 10 (103.25 ms), although its P95 was somewhat higher (180 vs 160 ms). This does *not* prove deeper pages are faster.
3. **Zero errors** is encouraging under these specific conditions, but not a production availability or maximum-capacity guarantee.

`GET /cases` currently performs a matching-record count, a sorted `LIMIT`/`OFFSET` query, and serializes clients and assigned users for each returned case. More JSON data and/or lazily loaded related ORM objects (possible N+1 queries) could explain much of the large-page latency. **These are hypotheses, not confirmed root causes.** No SQL statement counts, SQL timings, query plans, or serialization profiles were captured.

## Limitations

- Only 1,000 case rows; deeper offsets or different indexes may behave differently on much larger datasets.
- Synthetic users shared the same **login identity** for the load test; this isn't a multi-account authorization benchmark.
- A single read endpoint was exercised per run. No writes, searches, or navigation workflow.
- Throughput is strongly shaped by Locust's closed-user wait model; these runs are not a server saturation or capacity test.
- Runs were sequential without repeated trials or controlled caches, host utilization, and network variability.
- Both application databases share server hardware/PostgreSQL; full resource isolation was not achieved.
- M2-01 used a different LAN/Nginx path and only three cases, so its raw latencies are not a controlled apples-to-apples dataset-size comparison.

## Next issue: Investigate SQL work and N+1 behavior

Instrument per-request SQL **statement counts** and SQL execution duration for limits 10 and 100, avoiding sensitive query contents. Test whether `selectinload()` / `joinedload()` changes statement counts and response time. Inspect PostgreSQL read-only query plans (e.g., `EXPLAIN (ANALYZE, BUFFERS)`) when justified. If SQL time is not dominant, isolate JSON serialization time. Keep optimizations in a follow-up issue, not in #91.

## Primary evidence

Metrics above were read from the **GET rows** of the `requests_statistics` and percentile sections embedded in the three attached Locust HTML reports:

1. `Locust_2026-11-09-14h59_locustfile.py_http___127.0.0.1_18001.html` — page 1 / limit 10.
2. `Locust_2026-11-09-15h08_locustfile.py_http___127.0.0.1_18001.html` — page 1 / limit 100.
3. `Locust_2026-11-09-15h17_locustfile.py_http___127.0.0.1_18001.html` — page 50 / limit 10.

Review/sanitize raw HTML before optionally committing it. The accompanying CSV retains exact scenario identities and compact metrics for future charts/comparisons.
