# M2-03 — SQLAlchemy query profiling and N+1 investigation

**Project:** Client Intake & Case Tracking API  
**Phase:** M2 — Reliability, Redis & Performance  
**Issue:** [#93 — Profile SQLAlchemy queries and investigate `GET /cases` pagination latency](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/93)  
**Investigation date:** November 16, 2026  
**Status:** Evidence collected; diagnostic investigation documented. Full-suite CI, PR, and merge remain to be verified.  
**Prior experiment:** [M2-02 pagination benchmark](pagination-benchmark-2026-11-09.md)  
**Environment runbook:** [M2-02 isolated performance environment](performance-environment-m2-02.md)

## 1. Problem and objective

The M2-02 Locust experiment showed that, with ten simulated users, retrieving 100 cases took an average of **647.63 ms**, compared with **103.25 ms** for ten cases. This difference suggested an inefficient data-access or serialization path, but the load test did not identify its cause.

This investigation aimed to:

1. Count the SQL statements executed by authenticated `GET /cases` requests at several page sizes.
2. Determine which database relationships account for the extra statements.
3. Compare the current lazy-loading behavior against a test-only eager-loading alternative while preserving serialized output.
4. Separate observed facts from hypotheses about full HTTP and production performance.

**Outcome:** A clear N+1 relationship-loading pattern was observed in the current code. In a controlled ORM-only A/B experiment returning 100 cases, `selectinload()` reduced SQL statements from **190 to 4** and median operation time from **153.42 ms to 11.05 ms**. This result does **not** yet represent an HTTP benchmark or a deployed optimization.

## 2. Test environment and safety

| Component | Configuration |
|---|---|
| Application | Flask + SQLAlchemy 2.x |
| Database | PostgreSQL, `client_intake_perf` |
| Database role | `client_perf_user` |
| Data | 500 synthetic clients, 100 synthetic staff users, one test admin, 1,000 synthetic cases |
| Test checkout | `~/apps/client-intake-perf`, detached worktree tracking the M2-03 feature branch |
| Machine | Ubuntu 26.04 LTS; Intel Core i5, fifth generation; 8 GB RAM |
| Measurement path | Flask test client for request profiling; direct SQLAlchemy ORM for A/B comparison |
| Excluded | Existing systemd/Gunicorn service, Nginx, Cloudflare, SSH HTTP forwarding, and Locust |

Both profiling scripts perform a **database identity check** before measuring anything:

```python
identity = tuple(
    conn.execute(text("SELECT current_user, current_database()")).one()
)
if identity != ("client_perf_user", "client_intake_perf"):
    raise SystemExit(f"Wrong database: {identity}")
```

The A/B script retrieves cases and serializes them; it does not perform application-level writes. The previously running API on port `8000` and its database `client_intake_dev` were not targeted. Both databases still share host hardware and the same PostgreSQL installation; this is data/process isolation, **not** complete infrastructure isolation.

## 3. Why N+1 was suspected

In [`app/services/cases.py`](../../../app/services/cases.py), `get_cases()` issues a matching-case count, retrieves a sorted page of `Case` objects, and serializes each case:

```python
cases = db.session.scalars(paginated_query).all()
# ...
"items": [case.serialize() for case in cases]
```

In [`app/models/models.py`](../../../app/models/models.py), `Case.serialize()` traverses two relationships:

```python
"assigned_users": [user.serialize() for user in self.assigned_users],
"client": self.client.serialize() if self.client else None,
```

These relationships have no eager-loading strategy specified in the model or query, so accessing an unloaded relationship can trigger another SQL statement. The ORM session's identity map may avoid repeated *client* lookups when multiple cases share a client; unloaded *assigned-users collections* still require loading for each case in this workload.

The hypothesis was that increasing page size drives additional round trips to PostgreSQL, rather than merely increasing the cost of the main `LIMIT`/`OFFSET` query.

## 4. Profiling implementation

### Instrumentation

[`load_tests/query_profiler.py`](../../../load_tests/query_profiler.py) defines a `measure_sql(engine)` context manager. It registers `before_cursor_execute` and `after_cursor_execute` SQLAlchemy event listeners, counts completed statements, accumulates elapsed driver-execute time using `time.perf_counter()`, categorizes statement text by referenced tables, and removes listeners in `finally`.

The categories are `assigned_users`, `clients`, `users`, `cases`, and `other`. **This is a lightweight SQL-text heuristic** (for example, it recognizes `users_cases`); it is not a full SQL parser. No SQL parameters, passwords, JWTs, or full client records are printed.

The profiler was unit-tested with an in-memory SQLite engine: three `SELECT` statements counted inside the context manager; a fourth statement executed afterward did not change the count. The test also checks nonnegative elapsed time and categorization as `other`:

```bash
python -m pytest tests/test_query_profiler.py -v
```

**Observed:** the isolated unit test passed. A full backend pytest suite and GitHub Actions status for #93 are separate final checks.

### Authenticated request measurements

[`load_tests/profile_cases.py`](../../../load_tests/profile_cases.py) uses Flask's test client to log into the isolated test API, then measures one authenticated request for each of:

- `GET /cases?page=1&limit=10`
- `GET /cases?page=1&limit=100`
- `GET /cases?page=50&limit=10`

Before each scenario it calls `db.session.remove()` to discard the previous ORM session state. It validates HTTP `200`, the returned item count, and `total_items=1000`.

### Controlled ORM A/B experiment

[`load_tests/compare_loading.py`](../../../load_tests/compare_loading.py) executes an equivalent count-and-page retrieval followed by **the same `Case.serialize()` code**. Its two strategies differ only in relationship loading:

```python
# Current behavior: lazy loading
query = select(Case).where(Case.is_deleted.is_(False)).order_by(
    Case.created_at.desc()
).limit(100).offset(0)

# Test alternative: eager loading
query = query.options(
    selectinload(Case.client),
    selectinload(Case.assigned_users),
)
```

The script removes the ORM session between strategies; runs one warm-up pair followed by **five measured pairs**, alternating strategy order; and verifies output equality on every pair:

```python
assert results["lazy"]["items"] == results["eager"]["items"]
```

It reports SQL statement count, accumulated driver-execute time, and the elapsed time of the ORM operation, including fetching and serialization. The ORM A/B test intentionally excludes authentication and the HTTP request pipeline.

## 5. Results

### 5.1 Authenticated Flask test-client requests

A single set of measurements was collected after adding query categorization:

| Metric | Page 1, limit 10 | Page 1, limit 100 | Page 50, limit 10 |
|---|---:|---:|---:|
| HTTP status | 200 | 200 | 200 |
| Total SQL statements | **23** | **191** | **22** |
| Case-related statements | 2 | 2 | 2 |
| Assigned-user relationship statements | 10 | 100 | 10 |
| Client relationship statements | 10 | 88 | 9 |
| User/auth statements | 1 | 1 | 1 |
| Cumulative driver-execute time | 6.77 ms | 49.53 ms | 6.33 ms |
| Test-client request time | 22.70 ms | 120.28 ms | 15.59 ms |

For 100 returned cases, **188 of 191** statements were categorized as relationship loading: 100 assigned-user queries plus 88 client queries. The two main case queries did **not** multiply with page size. This strongly supports N+1 relationship loading. The number of client statements is smaller than the number of cases because some cases share clients already represented in the session.

The above is one diagnostic run, not a stable latency distribution; use the statement-count pattern as the stronger finding.

### 5.2 ORM-only A/B — five measured trials, 100 cases

| Trial | Lazy: statements | Lazy: SQL ms | Lazy: total ms | Eager: statements | Eager: SQL ms | Eager: total ms |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 190 | 55.89 | 131.33 | 4 | 2.34 | 8.42 |
| 2 | 190 | 64.79 | 153.42 | 4 | 3.02 | 11.19 |
| 3 | 190 | 64.19 | 151.65 | 4 | 2.93 | 10.69 |
| 4 | 190 | 69.19 | 175.53 | 4 | 3.10 | 11.34 |
| 5 | 190 | 72.37 | 173.00 | 4 | 2.99 | 11.05 |
| **Median** | **190** | **64.79** | **153.42** | **4** | **2.99** | **11.05** |

The A/B query counts are **one lower** than the authenticated request numbers because the A/B script does not run the user/authentication lookup inside the profiled section.

**Relative differences on this controlled ORM workload:**

- **97.9% fewer SQL statements** (190 → 4).
- **95.4% less cumulative driver-execute time** (64.79 ms → 2.99 ms; medians).
- **92.8% lower total ORM operation time**, approximately **13.9× faster** (153.42 ms → 11.05 ms; medians).
- **Serialized output equality passed** in each paired trial.

With eager loading, the four statements correspond to a count query, a paginated cases query, a grouped client query, and a grouped assigned-user query. This is the expected batching behavior of `selectinload()` for the measured 100-case workload.

## 6. Interpretation and limitations

**Confirmed:** the current listing/serialization path executes per-case related-object lookups. Eager loading removes most redundant round trips for this exact data shape without altering the serialized case dictionaries in the experiment.

**Not yet confirmed:** the size of the improvement in the complete authenticated endpoint under Gunicorn and Locust. The earlier M2-02 **647.63 ms** result is a concurrent HTTP load-test average over an SSH-forwarded network path; the **153.42 ms** figure here is a median for a local ORM-only operation. These are different measurements and should **not** be directly compared or subtracted.

Additional constraints:

- SQL event timings cover DB-driver execution callbacks, **not** all result fetching, ORM materialization, serialization, network overhead, or database server CPU time.
- Engine-level listeners are safe for the controlled single-process experiment but can include unrelated concurrent queries if used with multiple active requests.
- The trial count is small and the scenarios run on shared hardware. Caching, process scheduling, and synthetic-data distribution may affect elapsed times.
- The A/B script checks dictionary equality for 100 serialized cases, but does not yet exercise the full route and authorization behavior with eager loading.
- The synthetic dataset contains 1,000 cases; effectiveness on larger or differently structured datasets remains untested. `selectinload()` may use multiple batches at higher cardinality.
- The heuristic query classifier provides a useful table-level breakdown, not definitive ORM call-site tracing.

## 7. Reproduction — isolated environment only

### Windows development checkout

From the M2-03 branch:

```powershell
python -m pytest tests/test_query_profiler.py -v
# Commit and push profiler, tests, and scripts to perf/93-profile-cases-queries
```

### Ubuntu performance worktree

**Never switch the original deployed checkout or profile the original database.** In the *detached performance worktree*:

```bash
cd ~/apps/client-intake-perf
git status --short                   # must be clean before switching commits
git fetch origin
git switch --detach origin/perf/93-profile-cases-queries
source ../client-intake-case-tracking-api/.venv/bin/activate

read -rsp "Performance DB password: " PGPASSWORD; echo
export PGPASSWORD
export DATABASE_URL="postgresql+psycopg2://client_perf_user@127.0.0.1:5432/client_intake_perf"
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

The scripts explicitly verify `client_perf_user` and `client_intake_perf`. **Do not proceed** if the connection identity differs or the expected 1,000-case dataset is absent.

```bash
# Interactive performance-admin login; first diagnostic requests
python -m load_tests.profile_cases

# No HTTP authentication required; controlled ORM A/B, five measured trials
python -m load_tests.compare_loading

# Clean up test-shell secrets after finishing
unset PGPASSWORD DATABASE_URL JWT_SECRET_KEY
```

Do not paste database passwords or JWTs into terminal history, issue comments, CI logs, or this report. Stop test processes when done. No modification to Nginx, the original Gunicorn systemd service, or live database is necessary.

## 8. Conclusion and follow-up

**Issue #93 achieves its central diagnostic goal:** the performance cost seen at larger case page sizes is strongly associated with lazy-loaded `Case.client` and `Case.assigned_users` relationships. The A/B experiment demonstrates an effective *candidate* optimization (`selectinload`) under controlled, isolated conditions.

**Recommended separate implementation issue:**

1. Apply targeted eager loading to `GET /cases` (likely `selectinload(Case.client)` and `selectinload(Case.assigned_users)`), without changing endpoint response structure or authorization rules.
2. Add regression tests that verify related case data and query-count behavior with multiple clients and assigned users.
3. Measure the real HTTP endpoint again under the same Gunicorn, SSH tunnel, Locust, dataset, and concurrent-user conditions used in M2-02; record before/after P50, P95, requests/sec, and failures.
4. Check filtered cases, non-first pages, and normal error handling, and verify that the deployed service's original database is not modified during benchmarking.

**Do not** introduce Redis, caching, indexes, or additional Gunicorn workers to address an ORM query pattern already demonstrated in this workload.

### Completion checks for #93

- [x] Isolated performance target and database-role guard implemented.
- [x] SQL statement count and elapsed-time profiler added, with passing isolated unit test.
- [x] All three authenticated pagination scenarios measured and classified.
- [x] N+1 behavior supported by statement counts; no SQL parameters or credentials printed.
- [x] Five paired lazy/eager trials completed with output equality checks.
- [x] Investigation and reproduction steps documented in this report.
- [ ] Full backend pytest suite passed for final branch revision.
- [ ] GitHub Actions CI passed on the PR and review completed.
- [ ] PR merged into `main` with `Closes #93`.

## 9. Further reading

- [SQLAlchemy — Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
- [SQLAlchemy — `selectinload()` / Select IN Loading](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#select-in-loading)
- [SQLAlchemy — Core Events](https://docs.sqlalchemy.org/en/20/core/events.html)
- [Flask — Testing Applications](https://flask.palletsprojects.com/en/stable/testing/)
- [Python — `contextlib.contextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager)
