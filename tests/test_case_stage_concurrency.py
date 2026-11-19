"""M2-06: opt-in PostgreSQL regression test for concurrent stage updates.

Manual execution ONLY against isolated client_intake_perf as client_perf_user.
Set RUN_PG_CONCURRENCY=1, DATABASE_URL, and JWT_SECRET_KEY before running.
This test calls the real service, not the HTTP route. It does NOT run on SQLite.
"""

import os
from threading import Event, Thread
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from app import create_app
from app.extensions.extensions import db
from app.models.models import AuditLog, Case, Client, User
import app.services.cases as case_service

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PG_CONCURRENCY") != "1",
    reason="Opt-in PostgreSQL experiment: set RUN_PG_CONCURRENCY=1",
)

EXPECTED_DB = "client_intake_perf"
EXPECTED_ROLE = "client_perf_user"


def assert_perf_database():
    if db.engine.dialect.name != "postgresql":
        raise RuntimeError("Only PostgreSQL is supported by this test")
    database, role = db.session.execute(
        text("SELECT current_database(), current_user")
    ).one()
    if (database, role) != (EXPECTED_DB, EXPECTED_ROLE):
        raise RuntimeError(f"Unsafe database connection: {database} / {role}")


def test_concurrent_case_stage_update_preserves_workflow(monkeypatch):
    app = create_app()
    marker = "m2_06_" + uuid4().hex[:16]
    case_id = None
    staff_a_id = staff_b_id = None
    threads = []
    errors = []
    statuses = {}
    b_pid = {}

    a_is_paused = Event()
    release_a = Event()
    b_connection_ready = Event()
    b_validated_old_stage = Event()

    original_add_log = case_service.add_log

    def coordinate_at_audit_log(log):
        # This point occurs AFTER the service has checked allowed transitions.
        original_add_log(log)
        if log["user_id"] == staff_a_id:
            a_is_paused.set()
            if not release_a.wait(timeout=20):
                raise TimeoutError("Staff A was not released")
        elif log["user_id"] == staff_b_id:
            b_validated_old_stage.set()

    # Patch ONLY this test process; original application code stays intact.
    monkeypatch.setattr(case_service, "add_log", coordinate_at_audit_log)

    try:
        with app.app_context():
            assert_perf_database()  # Guard before the first write.
            staff_ids = db.session.scalars(
                select(User.user_id)
                .where(User.is_active.is_(True))
                .order_by(User.user_id)
                .limit(2)
            ).all()
            client_id = db.session.scalar(
                select(Client.client_id).order_by(Client.client_id).limit(1)
            )
            if len(staff_ids) < 2 or client_id is None:
                raise RuntimeError("Performance DB needs two active users and a client")
            staff_a_id, staff_b_id = staff_ids
            case = Case(
                case_type="FOIA",
                case_status=marker,
                case_stage="edits",
                client_id=client_id,
            )
            db.session.add(case)
            db.session.flush()
            case_id = case.case_id
            db.session.commit()
            print(f"Created disposable case {case_id} in isolated performance DB")

        def worker_a():
            try:
                with app.app_context():
                    assert_perf_database()
                    _, status = case_service.edit_case_stage(
                        "review", case_id, staff_a_id
                    )
                    statuses["A"] = status
            except Exception as exc:
                errors.append(("A", exc))
                a_is_paused.set()

        def worker_b():
            try:
                with app.app_context():
                    assert_perf_database()
                    # Keep this connection in the session for the service call.
                    # Its backend PID lets the coordinator observe a PG lock wait.
                    b_pid["value"] = db.session.scalar(text("SELECT pg_backend_pid()"))
                    b_connection_ready.set()
                    _, status = case_service.edit_case_stage(
                        "pending_submission", case_id, staff_b_id
                    )
                    statuses["B"] = status
            except Exception as exc:
                errors.append(("B", exc))
                b_connection_ready.set()

        a = Thread(target=worker_a, name="m2-06-staff-a", daemon=True)
        threads.append(a)
        a.start()
        assert a_is_paused.wait(10), "Staff A did not reach post-validation hook"
        assert not errors, errors

        b = Thread(target=worker_b, name="m2-06-staff-b", daemon=True)
        threads.append(b)
        b.start()
        assert b_connection_ready.wait(10), "Staff B did not establish a connection"
        assert not errors, errors

        # Coordinator proceeds when either:
        # - OLD CODE: B validated the stale stage (reaching add_log), or
        # - FIXED CODE: PostgreSQL reports B waiting on A's case-row lock.
        # No thread waits for the OTHER thread to commit before A is released.
        observed = None
        deadline = monotonic() + 12
        while monotonic() < deadline:
            if errors:
                break
            if b_validated_old_stage.is_set():
                observed = "B validated old stage before A committed"
                break
            with app.app_context():
                assert_perf_database()
                event = db.session.scalar(
                    text("SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid"),
                    {"pid": b_pid["value"]},
                )
                db.session.rollback()
            if event == "Lock":
                observed = "B waiting on PostgreSQL row lock"
                break
            b_validated_old_stage.wait(0.05)

        assert observed, f"Could not establish ordering; errors: {errors}"
        print("Coordination observed:", observed)
        release_a.set()
        for worker in threads:
            worker.join(timeout=15)
        assert all(not worker.is_alive() for worker in threads), "Worker did not finish"
        assert not errors, errors

        with app.app_context():
            assert_perf_database()
            db.session.expire_all()
            stored_case = db.session.get(Case, case_id)
            logs = db.session.scalars(
                select(AuditLog)
                .where(AuditLog.case_id == case_id)
                .order_by(AuditLog.log_id)
            ).all()
            print("Service statuses:", statuses)
            print("Final stage:", stored_case.case_stage)
            print("Audit entries:", [(x.old_value, x.new_value) for x in logs])

            # Desired post-fix behavior. These assertions should FAIL on main.
            assert statuses == {"A": 200, "B": 400}
            assert stored_case.case_stage == "review"
            assert len(logs) == 1
            assert logs[0].user_id == staff_a_id
            assert (logs[0].old_value, logs[0].new_value) == ("edits", "review")

    finally:
        release_a.set()  # Even if an assertion or worker crashes.
        for worker in threads:
            worker.join(timeout=15)
        if case_id is not None and all(not worker.is_alive() for worker in threads):
            with app.app_context():
                assert_perf_database()
                db.session.rollback()
                db.session.remove()
                case = db.session.get(Case, case_id)
                if case is not None and case.case_status == marker:
                    db.session.execute(
                        delete(AuditLog).where(AuditLog.case_id == case_id)
                    )
                    db.session.execute(
                        delete(Case).where(
                            Case.case_id == case_id,
                            Case.case_status == marker,
                        )
                    )
                    db.session.commit()
                    print(f"Cleaned up disposable case {case_id}")
                elif case is not None:
                    db.session.rollback()
                    raise RuntimeError("Cleanup refused: case marker did not match")
        elif case_id is not None:
            print(f"WARNING: worker active; manual cleanup required for case {case_id}")
