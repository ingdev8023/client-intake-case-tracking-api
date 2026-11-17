# M2-04 — Eliminate N+1 queries in paginated `GET /cases`

**Date:** 2026-11-16  
**GitHub issue:** [#95 — Remove N+1 queries and validate HTTP performance](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/95)  
**Branch:** `perf/95-eager-load-cases`  
**Scope:** Flask / SQLAlchemy service for the authenticated `GET /cases` endpoint

## Executive summary

A previous profiling investigation ([#93](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/93)) identified an **N+1 relationship-loading pattern** when serializing case records with their related client and assigned users. Replacing per-case lazy loading with SQLAlchemy `selectinload()` reduced the number of statements required in a controlled 100-case ORM experiment from **190 to 4**. The real API was then updated, protected by a query-count regression test, and benchmarked through Gunicorn using Locust against an isolated PostgreSQL performance database. The largest measured HTTP improvement was for `page=1&limit=100`: **647.63 ms → 82.98 ms mean GET response time (87.2% lower)**, with no GET failures in the measured run.

These numbers describe **this workload and environment**. They are not a general production throughput or latency guarantee.

## Problem and evidence before the change

For 100 serialized cases, our SQL statement classifier measured:

| Query category | SQL statements |
|---|---:|
| Case count + page retrieval | 2 |
| Assigned-user relationship queries | 100 |
| Client relationship queries | 88 |
| Authentication/user lookup | 1 |
| **Total authenticated request** | **191** |

Most of the statements were triggered when serialization accessed `Case.assigned_users` and `Case.client` after initially fetching the cases. Some client records were reused through SQLAlchemy's session identity map; this did not eliminate the per-case collection loading. Query counts, **not just slow timings**, demonstrated the underlying problem.

## Implementation

The paginated query in `app/services/cases.py` now applies eager loading to both serialized relationships:

```python
from sqlalchemy.orm import selectinload

paginated_query = (
    query
    .order_by(Case.created_at.desc())
    .limit(limit)
    .offset((page - 1) * limit)
    .options(
        selectinload(Case.client),
        selectinload(Case.assigned_users),
    )
)
```

No intentional change to the serialization contract, authentication, filtering, counting, or pagination semantics. `selectinload()` batches relationship retrieval into additional queries, rather than issuing queries each time an unloaded relationship is visited during serialization.

## Controlled ORM validation — M2-03 evidence

A/B script: `load_tests/compare_loading.py`. Both strategies serialized the same 100 cases; the ORM session was cleared between runs and the serialized results were checked for equality. One warm-up pair was followed by five measured pairs in alternating order.

| Metric (median of 5 trials) | Lazy | Eager | Observed change |
|---|---:|---:|---:|
| SQL statements (excluding login) | 190 | 4 | 97.9% fewer |
| SQL execution instrumentation | 64.79 ms | 2.99 ms | 95.4% lower |
| Fetch + serialization elapsed | 153.42 ms | 11.05 ms | 92.8% lower; ~13.9× faster |

**Caution:** These measurements are internal ORM operations, not HTTP response times and not the primary results of this issue.

## Automated regression test

`tests/test_case_query_loading.py` creates **six cases with six distinct clients**, requests the actual authenticated endpoint and checks related client/assigned-user data, pagination counts, and a bounded SQL statement count:

```python
assert metrics["query_count"] <= 7, (
    f"N+1 regression: {metrics['query_count']} SQL statements"
)
```

The test passed with eager loading enabled. We explicitly ran a **negative control** by temporarily disabling `.options(...)`: the test correctly failed with **15 SQL statements** (`15 <= 7` was false). Eager loading was restored, and the test and entire local suite passed again. This shows the regression test can detect the relationship-loading problem, not merely assert an HTTP 200 response.

## HTTP performance test methodology

- **Database:** PostgreSQL `client_intake_perf`; restricted role `client_perf_user`; 1,000 synthetic cases, 500 clients, 100 synthetic staff users plus one performance administrator. **Original application database was not modified.**
- **Application:** independent detached Git worktree on the optimization branch; Gunicorn with two workers, binding only to `127.0.0.1:8001` on Ubuntu. The original service on port `8000` was left unchanged.
- **Client:** Locust on Windows, forwarding to the isolated endpoint over an SSH tunnel (`127.0.0.1:18001`); authenticated virtual users and GET requests.
- **Workload:** 10 simulated users, ~3 minutes per scenario, nominal 2 users/s spawn rate and 1–3 s think time. Each scenario ran as a separate test.
- **Endpoint scenarios:** `page=1&limit=10`, `page=1&limit=100`, `page=50&limit=10`.
- **Statistics:** GET-only mean, response-time percentiles, request count, throughput and failures; login requests should be analyzed separately.
- **Comparison caveat:** The original baseline and updated tests were conducted on different days. Keep observed changes distinct from controlled proof of maximum throughput or general production behavior.

## Complete before/after GET comparisons

The baseline values below come from earlier recorded Locust measurements. The new limit-10 and page-50 results were verified directly from Locust HTML reports uploaded on November 16, 2026; the optimized limit-100 result was analyzed from its previously supplied Locust report.

| Scenario | Baseline mean GET | Optimized mean GET | Mean reduction | Baseline P95 | Optimized P95 | New GET failures |
|---|---:|---:|---:|---:|---:|---:|
| `page=1&limit=10` | ~103 ms | **58.50 ms** | **43.2%** | ~160 ms | **130 ms** | 0 |
| `page=1&limit=100` | 647.63 ms | **82.98 ms** | **87.2%** | 1,200 ms | **110 ms** | 0 |
| `page=50&limit=10` | ~99 ms | **49.19 ms** | **50.3%** | ~180 ms | **84 ms** | 0 |

### Optimized request statistics

| Metric | Page 1 / limit 10 | Page 1 / limit 100 | Page 50 / limit 10 |
|---|---:|---:|---:|
| Mean GET | 58.50 ms | 82.98 ms | 49.19 ms |
| Median GET | 49 ms | 81 ms | 43 ms |
| P95 GET | 130 ms | 110 ms | 84 ms |
| P99 GET | 190 ms | 150 ms | 140 ms |
| Maximum GET | 291 ms | 193 ms | 228 ms |
| GET requests | 857 | 863 | 840 |
| GET requests per second | 4.77 | 4.79 | 4.67 |
| GET failures | 0 | 0 | 0 |

The new page-50 and page-1 limit-10 runs each lasted **2 minutes 59 seconds**. Both also included ten successful `POST /login` calls; these are **excluded** from the GET latency table above.

### Optimized HTML evidence

- `Locust_2026-11-16-15h28_locustfile.py_http___127.0.0.1_18001(2).html` — page 1, limit 10; started 2026-11-16 20:28:57 UTC.
- `Locust_2026-11-16-15h34_locustfile.py_http___127.0.0.1_18001.html` — page 50, limit 10; started 2026-11-16 20:34:01 UTC.
- The optimized `page=1&limit=100` HTML report was reviewed in the earlier benchmark discussion; preserve a local copy alongside these results.

**Evidence handling:** Raw HTML reports are not automatically included in this Markdown deliverable. Review reports for internal information before adding raw artifacts to the public repository.

## Interpretation

The strongest improvement is seen when returning 100 cases, where lazy relationship loading previously multiplied database round trips. The new average of ~83 ms compared to ~648 ms is consistent with the ORM profiling evidence and the addition of `selectinload()` to the actual request path. The two 10-case scenarios also improved substantially. This supports the conclusion that the data-access strategy was a material performance bottleneck.

In the ~3-minute Locust runs, GET throughput remained near 4.7–4.8 requests/second after optimization, reflecting the configured think time and user count. **These tests did not establish maximum server capacity.** The observed improvement in speed cannot be extrapolated directly to the throughput limit of the server.

A single run per scenario, sequential test timing, session/login overhead, background resource utilization, and possible cache warmth mean the reported percentage improvements should not be interpreted as exact guarantees. Further repeat trials or workload escalation would be separate performance studies.

## Safety and deployment boundaries

- The isolated performance PostgreSQL DB and least-privileged role are distinct from the original application DB and role.
- Performance Gunicorn is bound only to loopback `127.0.0.1:8001`; the original API/systemd/Nginx setup remains unchanged.
- No live service redeployment is required merely to merge performance tooling or documentation. Deploying the optimization to the normal service, when desired, is a separate explicit decision with smoke checks and rollback planning.

## Issue #95 completion checklist

- [x] Targeted `selectinload()` implementation for client and assigned users.
- [x] Regression test checks API response and query budget.
- [x] Negative-control test fails with N+1 restored, then optimization restored.
- [x] Local full test suite reported passing.
- [x] Isolated PostgreSQL/Gunicorn/SSH-tunnel benchmarks collected for all three pagination scenarios.
- [x] Baseline versus optimized HTTP measurements documented.
- [ ] Review optimization PR and GitHub Actions CI status.
- [ ] Confirm final branch is restored and up to date; merge PR with `Closes #95` after review.
- [ ] Decide separately whether/when to deploy to the original running API.

## References

- SQLAlchemy ORM Relationship Loading: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
- SQLAlchemy `selectinload()` explanation: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#select-in-loading
- SQLAlchemy Core Events: https://docs.sqlalchemy.org/en/20/core/events.html
- Locust documentation: https://docs.locust.io/
- Internal M2-03 profiling report: `app/docs/performance/m2-03-sqlalchemy-query-profiling.md`
