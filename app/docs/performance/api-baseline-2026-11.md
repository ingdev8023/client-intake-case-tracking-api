# M2-01 — API Performance Baseline

**Project:** Client Intake & Case Tracking API  
**Date:** November 2026  
**Status:** Completed — Initial baseline  
**Related issue:** [#89](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/89)

## 1. Objective

Establish an initial performance baseline for the Flask API under controlled HTTP workloads.

Measure:
- Throughput (requests per second).
- Average response time.
- p50, p95, and p99 latency.
- HTTP request failures.
- Server resource utilization.

The objective is to establish a reference for future performance comparisons, **not to determine maximum server capacity**.

## 2. Test Environment

| Component | Configuration |
|---|---|
| Operating system | Ubuntu 26.04 LTS |
| Hardware | Intel Core i5, 5th generation |
| RAM | 8 GB installed |
| Application | Flask |
| Application server | Gunicorn — 2 workers |
| Reverse proxy | Nginx |
| Database | PostgreSQL |
| Load-testing tool | Locust |
| Load generator | Windows laptop |
| Connection | Local network (LAN) |
| Dataset | 3 case records |

**Request path:**

Windows laptop → LAN → Nginx → Gunicorn → Flask → PostgreSQL (where applicable).

Cloudflare Tunnel and Vite were not part of the measured HTTP request path.

## 3. Test Methodology

Two workloads were evaluated.

**Workload A — Health Check**
- Endpoint: `GET /health`
- No authentication required.
- No database query.
- Virtual users: 1, 5, and 10.

**Workload B — Authenticated Case Retrieval**
- Login once per virtual user using `POST /login`.
- Reuse the received JWT.
- Repeatedly request `GET /cases?page=1&limit=10`.
- Virtual users: 1, 5, and 10.
- Dedicated test account.

**Common configuration:**
- Locust wait time: 1–3 seconds.
- Conservative load generation.
- Independent runs for each concurrency level.
- No write operations performed during load testing.

Run durations varied, so results are primarily compared using throughput and response-time distributions.

## 4. Results

### 4.1 Health Check Baseline

| Metric | 1 user | 5 users | 10 users |
|---|---:|---:|---:|
| Requests | 93 | 852 | 1,519 |
| RPS | 0.50 | 2.43 | 4.87 |
| p50 | 13 ms | 15 ms | 15 ms |
| p95 | 50 ms | 77 ms | 60 ms |
| Failures | 0 | 0 | 0 |

### 4.2 Authenticated Case Retrieval

Metrics below refer only to `GET /cases`; startup login requests are excluded.

| Metric | 1 user | 5 users (initial) | 5 users (repeat) | 10 users |
|---|---:|---:|---:|---:|
| Requests | 261 | 1,300 | 951 | 2,552 |
| RPS | 0.49 | 2.44 | 2.42 | 4.87 |
| Average | 40.5 ms | 63.2 ms | 39.2 ms | 40.7 ms |
| p50 | 37 ms | 46 ms | 37 ms | 38 ms |
| p95 | 63 ms | 120 ms | 54 ms | 61 ms |
| p99 | 83 ms | 260 ms | 82 ms | 88 ms |
| Failures | 0 | 0 | 0 | 0 |

### 4.3 Resource Observations

- A temporary CPU increase was observed during the initial authentication phase.
- CPU utilization was substantially lower during steady-state case retrieval.
- No obvious RAM exhaustion or sustained system-wide CPU saturation was observed.
- These observations were taken from `htop` snapshots, not continuous monitoring.

## 5. Analysis

### Throughput

Observed throughput increased approximately proportionally with the number of virtual users.

This reflects the configured workload and does not represent maximum server throughput.

### Latency

Median latency remained relatively stable across the one-, five-, and ten-user authenticated workloads.

The first five-user run showed higher tail latency, with a p95 of 120 ms. A repeated five-user experiment produced a p95 of 54 ms.

The cause of the original slowdown was not identified. The repeated experiment did not reproduce it.

### Reliability

No HTTP request failures were recorded in these experiments.

This establishes successful operation under the tested conditions, not a general guarantee of reliability.

## 6. Limitations

1. The database contained only three cases, making the dataset too small to represent a mature production application.
2. The `/cases` endpoint returned at most ten records per request.
3. Only a small number of concurrency levels were evaluated.
4. The tests generated roughly 0.5 requests per second per virtual user.
5. Experiment durations varied.
6. Network and operating-system variability were not fully isolated.
7. Tests did not evaluate maximum capacity, sustained high load, or database performance with large datasets.

## 7. Conclusions

The initial performance baseline indicates that:

- All tested requests completed without reported failures.
- Throughput increased with the generated workload.
- Typical `/cases` latency remained relatively stable.
- The initial five-user latency anomaly was not reproduced.
- No persistent resource saturation was identified.

**No immediate performance optimization is justified by these results.**

The baseline can be used to evaluate future changes to the API, database, and deployment infrastructure.

## 8. Future Work

**Separate issue — Isolated performance environment and test data**

- Configure an isolated database for performance experiments.
- Apply existing database migrations.
- Build a reproducible seed process using synthetic data.
- Repeat benchmark experiments with larger datasets.
- Investigate query plans using PostgreSQL `EXPLAIN ANALYZE` where measurements justify it.

Redis, caching, and worker tuning should be evaluated against measured needs rather than introduced without evidence.

## 9. Reproducing the Tests

**Locust script:** `load_tests/locustfile.py`

Example command:

```bash
python -m locust -f load_tests/locustfile.py \
  --host http://SERVER_LAN_IP \
  --headless -u 5 -r 1 -t 3m
```

For the authenticated workload, configure `LOAD_TEST_EMAIL` and `LOAD_TEST_PASSWORD` as environment variables before execution.

Only run load tests against systems and datasets designated for testing. Do not commit authentication credentials or tokens.

---

**Result:** Baseline established. Further performance investigation requires a more representative dataset.