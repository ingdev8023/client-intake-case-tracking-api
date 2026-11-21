# M2-06 — PostgreSQL row locking for concurrent case-stage updates

**Date of verification:** 2026-11-20  
**Issue:** [#98 — Prevent concurrent case-stage lost updates with PostgreSQL row locking](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/98)  
**Preceding investigation:** [#97 — M2-05 concurrent updates and audit integrity](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/97)  
**Implementation branch reviewed:** `realibility/98-case-stage-row-lock` (HEAD `e27a507` at review time)  
**Scope:** `edit_case_stage()` in `app/services/cases.py`; opt-in PostgreSQL tests in `tests/test_case_stage_concurrency.py`  
**State:** Implementation and local PostgreSQL validation complete; PR review, CI and deployment remain separate steps.

## Executive summary

The M2-05 investigation reproduced a lost update in the case-stage service. Two concurrent callers each validated a transition against the same initial stage (`edits`), both reported service-level success, and the later commit overwrote an already committed transition. Audit rows recorded two changes from `edits`, even though the actual final sequence violated the configured stage-transition rules.

M2-06 adds a PostgreSQL **row-level locking read** (`SELECT ... FOR UPDATE`) before stage validation. The lock is held in the database transaction through the stage update and audit-log commit (or released on rollback). Under a controlled two-worker test, a competing transition on the **same case** waited for PostgreSQL's lock, then was rejected against the newly committed stage. A separate test confirmed that changing **different cases** can proceed independently.

**Observed validation:** two opt-in PostgreSQL concurrency tests passed; a regular suite run with the opt-in unset completed with **53 passed, 2 skipped**; the earlier audit-failure injection probe still confirmed that case and audit changes roll back together. These are **service-level** tests, not real HTTP concurrency tests or production-load measurements.

## 1. Defect established by M2-05

Relevant workflow rules in `app/config/constants.py`:

```python
"edits": ["pending_submission", "review"],
"pending_submission": ["submitted"],
```

Before the fix, the service loaded the case with `db.session.get(Case, case_id)`, validated its current stage, queued an `AuditLog`, modified the `Case`, and committed. Independent requests could read and validate the same old stage before either request committed.

**Controlled RED test (before the fix):**

| Observation | Result |
|---|---|
| Staff A planned | `edits → review` |
| Staff B planned | `edits → pending_submission` |
| Actual service statuses | `{'B': 200, 'A': 200}` |
| Expected statuses | `{'A': 200, 'B': 400}` |
| Assertion | Failed, as designed |

This was not a malformed SQL transaction: individual case/audit writes were committed together. The defect was that competing business decisions were validated against stale state. For the observed commit order, the effective second transition was `pending_submission → review`, which is not allowed.

## 2. Focused implementation

The relevant implementation on the M2-06 branch is:

```python
user = db.session.get(User, user_id)
if user is None:
    return jsonify({"error": "User not found"}), 404
if not user.is_active:
    return jsonify({"error": "User not active"}), 403
if not new_stage:
    return jsonify({"error": "No stage to update"}), 400

case = db.session.scalar(
    select(Case)
    .where(Case.case_id == case_id)
    .with_for_update()
    .execution_options(populate_existing=True)
)
```

The code then validates `case.case_stage` against `ALLOWED_STAGE_TRANSITIONS`. Invalid-stage, disallowed-transition, and missing/deleted-case branches explicitly call `db.session.rollback()` before returning, releasing any held row lock. For accepted transitions, `add_log(...)` adds the audit object to the **same SQLAlchemy session**; the service updates `Case.case_stage` and `updated_by`, then invokes **one `db.session.commit()`**. Its existing `IntegrityError` handler rolls back.

### What the pieces accomplish

- **`select(Case).where(Case.case_id == case_id)`** targets the one case whose stage is being changed.
- **`.with_for_update()`** emits a PostgreSQL locking read. For the target row, conflicting locking/updating transactions wait until the current transaction ends. It is not a table-wide mutex, and ordinary MVCC `SELECT` readers are not generally blocked.
- **`.execution_options(populate_existing=True)`** refreshes state even if the ORM identity map already contains that `Case`; it is not itself a locking mechanism.
- **Transaction duration matters:** the lock belongs to the PostgreSQL transaction, **not** the Python thread or Flask object. `COMMIT` or `ROLLBACK` releases it.
- **Preserved atomicity:** case mutation and audit record still commit together; no separate audit commit or new table/version column was introduced.

The lookup of the acting user and the check for a missing stage happen before acquiring the case lock. This avoids taking a case lock for those rejected requests. Explicit rollback is particularly important for rejection paths *after* the locking read.

## 3. Verification design

**Test file:** `tests/test_case_stage_concurrency.py`  
**Opt-in:** `RUN_PG_CONCURRENCY=1`  
**Database:** PostgreSQL `client_intake_perf`, role `client_perf_user`, checked via `current_database()` and `current_user` before writes  
**Data:** disposable synthetic cases with unique `m2_06_...` marker and guarded cleanup  
**Isolation:** independent worker threads each enter a Flask application context, allowing separate Flask-SQLAlchemy session scopes and PostgreSQL transactions.

The test temporarily patches the `add_log` reference **inside its own process** to establish a controlled scheduling point *after validation but before case assignment/commit*. It does not edit the deployed application or send requests through the route/JWT layer. `threading.Event` signals and timeouts coordinate the workers; `time.monotonic()` provides a deadline for the PostgreSQL lock-wait observation in the same-case test.

### Test A — Competing updates to the same case

1. Worker A reads and locks a disposable case in stage `edits`, validates `review`, queues an audit row, then pauses before commit.
2. Worker B attempts `pending_submission` for the **same case**.
3. The coordinator observes B waiting on a PostgreSQL lock through `pg_stat_activity.wait_event_type = 'Lock'` (rather than waiting for B to finish while A remains paused).
4. The coordinator releases A, which commits `edits → review`.
5. B proceeds, sees `review`, and rejects `review → pending_submission` as invalid.
6. The test checks statuses, persisted state, a single accurate audit record and cleanup.

**GREEN result (disposable case #1018, Nov 20):**

```text
Coordination observed: B waiting on PostgreSQL row lock
Service statuses: {'B': 400, 'A': 200}
Final stage: review
Audit entries: [('edits', 'review')]
Cleaned up disposable case 1018
PASSED
```

The reported `400` follows the **existing invalid-stage-transition API service contract**. This test does **not** implement a stale-client `409 Conflict` precondition protocol.

### Test B — Different cases remain independent

1. Worker A locks **Case 1**, validates `edits → review`, and pauses while holding that lock.
2. Worker B updates **Case 2** to `pending_submission`.
3. The coordinator asserts B **finishes successfully before** releasing A; merely asserting both eventually finish would not be enough to detect overly broad serialization.
4. A resumes, commits, and the test checks each case's final state and audit row.

**GREEN result (disposable cases #1019 and #1020, Nov 20):**

```text
Service statuses: {'B': 200, 'A': 200}
Final stage case 1 review
Final stage case 2 pending_submission
Audit entries: [('edits', 'review')]
Audit entries: [('edits', 'pending_submission')]
Cleaned up disposable cases: [1019, 1020]
PASSED
```

### Test C — Case/audit transaction atomicity

The pre-existing M2-05 manual probe, `experiments/m2_05_atomicity_probe.py`, injected an invalid audit row (`action=None`, violating a NOT NULL constraint). After the locking change, the service returned `500`-equivalent, the stage remained `edits`, and no audit row persisted. Cleanup of disposable case #1012 was confirmed. This verifies atomic rollback **for the tested failure**, not all conceivable failures.

### Latest recorded test commands and outcomes

```bash
# Only with the isolated PostgreSQL DB and restricted role configured:
export RUN_PG_CONCURRENCY=1
python -m pytest tests/test_case_stage_concurrency.py -v -s
# Observed: 2 passed in 0.20s

unset RUN_PG_CONCURRENCY
python -m pytest tests -q
# Observed: 53 passed, 2 skipped in 18.03s
```

The regular test suite uses an in-memory SQLite fixture. SQLite is not evidence that PostgreSQL `FOR UPDATE` behaves correctly. The two PostgreSQL concurrency tests are deliberately skipped unless explicitly opted in. The current GitHub Actions workflow runs `python -m pytest tests -v` with Python 3.12; a normal CI run therefore verifies the regular suite **but does not execute these PostgreSQL-specific concurrency cases**.

## 4. Interpretation and trade-offs

**Verified for this scenario:** a competing write to the same case is serialized at the database row; the second service call validates the current stage, rejects the now-invalid transition and creates no misleading audit row. Two different case rows can be updated independently.

**Cost/risks:** a transaction holding the row lock can make competing updates wait. Keep the critical section short: no network calls, user interaction, uploads or long computations inside the lock. Future work may need explicit policies for lock timeouts, deadlocks, transient PostgreSQL errors and retry behavior; the current service's explicit exception handler catches `IntegrityError`, not every possible database operational failure. Deadlocks are possible when transactions acquire **multiple** locks in inconsistent order, although this focused path currently locks a single case row.

**`populate_existing=True`** refreshes ORM state in a session; the concurrency guarantee comes from the **database lock plus validation in the same transaction**. A bare second `SELECT` without locking would leave a race window.

## 5. Scope limits and unverified claims

- Tested **service logic**, not concurrent HTTP/JWT requests or the React frontend.
- Locking currently applies only to **case-stage changes**. Case status, type, assignments, tasks, notes and documents are not covered by this issue.
- Row locking addresses **overlapping database transactions**, not a browser submitting a form based on a record opened many minutes earlier. An explicit resource-version/`If-Match` contract remains a possible future feature.
- No idempotency-key or duplicate-request handling was implemented; that is a separate concern.
- The tests use disposable data in an isolated PostgreSQL database; they do not establish performance, throughput, lock-wait latency under production load, or production deployment readiness.
- The existing general tests cover valid and invalid stage changes. A focused review/test of every missing/deleted-case and database-operational-error path should be completed before final merge if required by issue acceptance criteria.
- Repeated multi-run stress/property testing has not been reported; the results are reproducible controlled schedules, not a full concurrency proof under arbitrary interleavings.

## 6. Deployment boundary and rollback

The code is on the implementation branch, not automatically installed into the originally running application. **Do not** confuse updating the detached performance worktree with deploying the normal Gunicorn/systemd service on port `8000`.

Before deploying this fix to the original service, separately:

1. Review PR and GitHub Actions result. Run the opt-in PostgreSQL tests again using the isolated performance DB; ensure no credentials appear in PR logs.
2. Confirm the live service's current commit, environment and database role; record the existing known-good commit as the rollback target.
3. Deploy the reviewed commit using the established deployment runbook and restart only the intended service during a planned window. No schema migration is introduced by this change.
4. Smoke-test `/health`, `/ready`, authentication, accepted/invalid stage transitions and case audit history; check Gunicorn/systemd logs for database errors and unexpected lock waits.
5. If the deployment fails, restore the prior known-good application commit and restart the service; verify readiness and key API paths. Rollback of application code does not automatically revert business transactions already committed.

These are **proposed deployment checks**, not actions already performed.

## 7. Completion checklist for issue #98

- [x] Failing RED PostgreSQL service-level regression test captured before locking change.
- [x] Lock the case row before reading/validating current stage; release on commit/rollback.
- [x] GREEN: conflicting same-case transition rejected; single accurate audit record.
- [x] GREEN: updates to distinct cases complete independently.
- [x] Injected audit-failure probe still passes after the change.
- [x] Regular suite: 53 passed / 2 skipped with PostgreSQL opt-in disabled.
- [x] Two PostgreSQL tests: 2 passed with opt-in enabled on isolated DB.
- [x] Disposable cases cleaned up according to test output.
- [ ] Review focused error cases and timeout/deadlock handling expectations.
- [ ] Commit this engineering report, open PR with `Closes #98`, verify GitHub Actions, review and merge.
- [ ] Separately plan and verify normal-service deployment (not part of this PR's automatic effect).

## References

- [M2-05 investigation report](m2-05-concurrency-investigation.md)
- [SQLAlchemy 2.0 — SELECT ... FOR UPDATE](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.GenerativeSelect.with_for_update)
- [SQLAlchemy ORM — Refreshing / populating existing objects](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html#populate-existing)
- [PostgreSQL — Explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL — Transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL — Monitoring database activity](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)
- [Python — `threading`](https://docs.python.org/3/library/threading.html)
- [Python — `time.monotonic()`](https://docs.python.org/3/library/time.html#time.monotonic)
