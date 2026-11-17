# M2-05 — Concurrent case-stage updates and audit-log integrity

**Investigation date:** 2026-11-17  
**GitHub issue:** [#97 — Investigate concurrent case stage updates and audit-log integrity](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/97)  
**Follow-up implementation:** [#98 — Prevent concurrent case-stage lost updates with PostgreSQL row locking](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/98)  
**Scope:** `edit_case_stage()` and its `AuditLog` writes in the Flask / SQLAlchemy backend  
**Status:** Investigation complete; implementation of the fix tracked separately

## Executive summary

An isolated PostgreSQL investigation reproduced a **lost update and misleading audit history** when two independent SQLAlchemy sessions changed the **same case stage** concurrently. Both service calls reported success (`200`), but the later commit overwrote a previously committed stage change. The resulting audit events each claimed the same initial stage, masking an effective transition that violated the configured workflow.

A separate failure-injection experiment showed that the case-stage update and its audit-log insertion **rolled back together** when the audit insertion violated a database constraint. This confirms transaction atomicity for the tested failure; it does **not** resolve concurrent decision-making.

**Conclusion:** Preserve the existing case/audit transaction boundary. Address the proven concurrent stage-update race in the follow-up implementation issue, without broadening this change to status, tasks, notes, document uploads or stale frontend forms.

## Existing behavior and hypothesis

The current service (`app/services/cases.py`) calls `edit_case_stage(new_stage, case_id, user_id)` and, in simplified terms:

1. Loads the `Case` and acting `User` with the SQLAlchemy session.
2. Checks the case and user, then validates `new_stage` using `ALLOWED_STAGE_TRANSITIONS`.
3. Queues an audit record through `add_log()` (`app/services/audit_log.py`).
4. Changes the in-memory `Case.case_stage`, sets `updated_by`, and commits the session.

`add_log()` adds an `AuditLog` ORM object to the same session; it does not commit independently.

Relevant configured transitions (`app/config/constants.py`):

```python
"edits": ["pending_submission", "review"],
"pending_submission": ["submitted"],
```

**Hypothesis:** Two sessions can each read `edits`, validate different allowed target stages and later commit conflicting updates. Each audit record would describe the stage observed before the other session committed.

## Isolation and test safety

The investigation was performed against an **isolated PostgreSQL performance database** only:

| Control | Value / result |
|---|---|
| Database | `client_intake_perf` |
| Restricted database role | `client_perf_user` |
| Database identity check | `current_database()` and `current_user` checked before writes |
| Test records | Disposable synthetic cases (`1006`, `1007`, `1008`) |
| Existing seeded performance records | Not intentionally modified |
| Normal API service / original DB | Not used by the probes |
| Cleanup | Script output confirmed deletion of cases `1007` and `1008` and their audit logs; case `1006` was cleaned up in the manual SQL exercise |

The Python probes use the real service function, but **do not send HTTP requests or exercise JWT authentication, routing or frontend behavior**. They temporarily replace the imported `add_log()` function **in the probe process only** to coordinate execution or inject a failure; no application source file is edited.

These scripts are *manual diagnostic tools*, not production endpoints, server tasks or ordinary CI tests. Keep them outside `app/`. If preserving them in version control for repeatability, use a separate explicitly manual directory, such as `experiments/m2-05/`, with database safety checks intact. Do not run them against the original application database.

## Experiment 1 — Direct PostgreSQL lost update

**Purpose:** Establish a basic read/validate/write interleaving before testing the Flask service.

Two `psql` sessions opened transactions on disposable case **#1006**, initially at `edits`:

1. Transaction A read `edits` and read it again.
2. Transaction B updated the row to `pending_submission` and committed.
3. Transaction A updated the same row to `review` and committed, without checking that the stage was still `edits`.
4. The final `SELECT` returned **`review`**.

**Finding:** In this controlled sequence, B's committed value was overwritten by A's later update. The direct SQL statements did not include a condition checking the original stage and did not exercise the API's audit logging or stage validation. This experiment illustrates the failure mechanism; it does not alone prove a service defect.

## Experiment 2 — Concurrent updates through the real service

**Probe:** `m2_05_concurrent_stage_probe.py` (manual, standalone)  
**Disposable case:** **#1007**, initial stage `edits`  
**Actors:** Two active users (`user_id` values `1` and `6` in the recorded output)  
**Execution:** Separate Flask application contexts and SQLAlchemy scoped sessions; `threading.Event` coordinates the interleaving rather than relying on sleeps.

### Controlled order

1. Staff A calls `edit_case_stage("review", ...)`, reads `edits`, validates the request, and queues an audit row.
2. A is paused immediately after `add_log()` and **before assigning the stage and committing**.
3. Staff B calls `edit_case_stage("pending_submission", ...)`, validates the same initial `edits` stage and commits successfully.
4. A resumes and commits its previously validated `review` update.
5. A fresh database observation reads the final case stage and audit records.

### Observed output

```text
Staff B committed: edits -> pending_submission

--- Observations ---
Service statuses: {'B': 200, 'A': 200}
Final stage: review
Audit entries (in insertion order):
  user=6 edits -> pending_submission
  user=1 edits -> review
NOTE: This probes service logic, not HTTP routing/authentication.

Cleaned up disposable case 1007 and its audit logs
```

### Interpretation

Both operations received service-level success responses. Yet the persisted stage was `review`, even though the preceding committed stage was `pending_submission`. The configured workflow does **not** allow `pending_submission → review`.

The audit history also records two separate changes **from `edits`**, rather than representing the actual committed sequence. This is a reproducible **lost update, effective workflow-rule violation and misleading audit history** for this service-level interleaving.

The probe did not independently verify the database's active transaction isolation setting; the behavior is consistent with the usual PostgreSQL `READ COMMITTED` pattern and application-side stale ORM state. This was not an HTTP integration test.

## Experiment 3 — Audit failure and transaction atomicity

**Probe:** `m2_05_atomicity_probe.py` (manual, standalone)  
**Disposable case:** **#1008**, initial stage `edits`

The probe temporarily substitutes `add_log()` with a function that inserts an `AuditLog` with `action=None`, violating the `audit_log.action` **NOT NULL** constraint when the SQLAlchemy session commits. The case-stage service handles the resulting `IntegrityError` and rolls the session back.

### Observed output

```text
--- Observations ---
Service HTTP-equivalent status: 500 (expected: 500)
Persisted stage: edits (expected: edits)
Audit entries: 0 (expected: 0)
PASS: Case update and audit insertion rolled back together.

Cleaned up disposable case 1008 and its audit logs
```

**Finding:** Under this injected database failure, neither the case-stage change nor a partial audit record persisted. The service's case/audit changes were **atomic for the tested error condition**. This is not a general guarantee that every possible error is handled correctly.

## Findings and engineering interpretation

| Concern | Evidence | Result |
|---|---|---|
| Lost update | Two sessions commit competing case-stage changes | **Reproduced** |
| Workflow integrity | Final effective change is `pending_submission → review`, not an allowed transition | **Violated in controlled interleaving** |
| Audit accuracy | Both audit events report `old_value=edits` | **Misleading** |
| Case/audit atomicity on an audit INSERT failure | Invalid audit action forces commit failure; stage and audit both absent | **Passed tested scenario** |
| HTTP/API routing concurrency | Probe calls service directly | **Not tested** |
| Long-lived stale browser forms | No frontend request/version precondition experiment | **Not tested** |
| Other updates (case status/type/assignments), notes, tasks, documents | Outside experiment | **Not tested** |

**Core distinction:** Atomicity means the case mutation and its audit write succeed or fail together in one transaction. It does **not** ensure that two independent transactions validate business rules against a fresh, serialized view of the same case.

## Recommended follow-up — #98

Address **case-stage updates only**:

- Acquire a PostgreSQL row-level lock on the target case *before* reading and checking its current stage; keep it through validation and commit/rollback. In SQLAlchemy, evaluate `select(Case).where(...).with_for_update()` instead of the initial unprotected `db.session.get()`.
- Reproduce the original conflict with a PostgreSQL-specific regression test **before** the fix, then verify that the second transaction validates the updated stage and does not create a false audit event.
- Verify unrelated cases can still be updated concurrently. Handle lock duration, timeouts and error paths deliberately.
- Retain the existing atomic audit/case commit.

A row lock protects **overlapping server-side transactions**. It does **not** by itself detect a browser that submits a form based on a case fetched 20 minutes earlier. Client-visible resource versions / optimistic concurrency are a separate future design decision, as are idempotency keys.

## Evidence and reproducibility boundaries

- Direct SQL experiment: two manually coordinated `psql` terminals and final case-stage observation.
- Service concurrency probe: `m2_05_concurrent_stage_probe.py`, using a pause at the audit-log hook to guarantee the interleaving.
- Atomicity probe: `m2_05_atomicity_probe.py`, injecting a database constraint failure.
- Observed terminal output was captured during the investigation. Preserve screenshots privately if needed; they are not embedded in this document.
- Raw probe source is **not embedded in this report**. If the repository requires exact automated reproduction, review and add the scripts under a dedicated manual `experiments/` directory or create safe PostgreSQL integration tests as part of #98. Without the probe source, the report documents the method and observed evidence but is not a fully self-contained replay artifact.
- Do not report this as a successful HTTP concurrency test; the measured statuses are returned by the service calls, not by real HTTP clients.

## Completion checklist

- [x] Investigated existing stage-transition and audit transaction flow.
- [x] Verified isolated PostgreSQL database identity and role before writes.
- [x] Reproduced direct SQL lost update.
- [x] Reproduced concurrent service-stage lost update and incorrect audit history.
- [x] Verified case/audit rollback under injected audit insertion failure.
- [x] Removed disposable test records according to probe output.
- [x] Created follow-up implementation issue [#98](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/98).
- [ ] Commit this report (and, if chosen, safely stored manual probe source).
- [ ] Run project test suite and verify CI for the documentation/investigation PR.
- [ ] Review and merge investigation PR with `Closes #97`.

**Scope reminder:** No concurrency-control implementation or original running service deployment is part of this investigation.
