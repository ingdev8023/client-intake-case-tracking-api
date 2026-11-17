"""M2-05: deterministic concurrent stage-change probe against isolated PostgreSQL.

Run from the repository root in an environment configured with DATABASE_URL for
client_intake_perf and JWT_SECRET_KEY. No changes to production source needed.

This runs the real edit_case_stage() service in separate Flask application
contexts (and hence separate Flask-SQLAlchemy scoped sessions). It is NOT an
HTTP concurrency test; authentication/route handling are outside this probe.
"""

from __future__ import annotations

from threading import Event, Thread
from uuid import uuid4

from sqlalchemy import delete, select, text

from app import create_app
from app.extensions.extensions import db
from app.models.models import AuditLog, Case, Client, User
import app.services.cases as case_service

EXPECTED_DATABASE = "client_intake_perf"
EXPECTED_USER = "client_perf_user"


def verify_database() -> None:
    database, user = db.session.execute(
        text("SELECT current_database(), current_user")
    ).one()
    print(f"Connection verified: {database} (role: {user})")
    if (database, user) != (EXPECTED_DATABASE, EXPECTED_USER):
        raise RuntimeError("STOP: connected to an unexpected database or role")


def main() -> None:
    app = create_app()
    marker = "m2_05_probe_" + uuid4().hex[:12]
    case_id: int | None = None
    worker: Thread | None = None

    a_reached_pause = Event()
    release_a = Event()
    cancel_a = Event()
    worker_errors: list[Exception] = []
    results: dict[str, int] = {}

    original_add_log = case_service.add_log

    try:
        # Setup: verify the *actual DB connection* before inserting anything.
        with app.app_context():
            verify_database()
            staff = db.session.scalars(
                select(User)
                .where(User.is_active.is_(True))
                .order_by(User.user_id)
                .limit(2)
            ).all()
            client = db.session.scalar(
                select(Client).order_by(Client.client_id).limit(1)
            )
            if len(staff) < 2 or client is None:
                raise RuntimeError("Need two active users and one synthetic client")

            staff_a_id, staff_b_id = (staff[0].user_id, staff[1].user_id)
            new_case = Case(
                case_type="FOIA",
                case_status=marker,  # unique marker for safe cleanup
                case_stage="edits",
                client_id=client.client_id,
            )
            db.session.add(new_case)
            db.session.flush()
            case_id = new_case.case_id
            db.session.commit()
            print(f"Disposable case created: {case_id} (stage: edits)")

        def pause_staff_a_after_validation(log: dict) -> None:
            # The real service queues an AuditLog here, then updates the case
            # and commits. No application-level change is made.
            original_add_log(log)
            if log["user_id"] == staff_a_id:
                a_reached_pause.set()
                if not release_a.wait(timeout=20):
                    raise TimeoutError("Staff A waited too long to resume")
                if cancel_a.is_set():
                    raise RuntimeError("Cancelled due to experiment error")

        # Monkeypatch only in this stand-alone Python process.
        case_service.add_log = pause_staff_a_after_validation

        def run_staff_a() -> None:
            try:
                with app.app_context():
                    verify_database()
                    _, status = case_service.edit_case_stage(
                        "review", case_id, staff_a_id
                    )
                    results["A"] = status
            except Exception as exc:
                worker_errors.append(exc)
                a_reached_pause.set()  # avoid hanging main on early failure

        worker = Thread(target=run_staff_a, name="staff-a")
        worker.start()
        if not a_reached_pause.wait(timeout=10):
            raise TimeoutError("Staff A never reached the pause point")
        if worker_errors:
            raise RuntimeError(f"Staff A failed early: {worker_errors}")

        # B sees the old stage because A has not committed (or flushed).
        # B commits while A is paused after its own stage validation.
        with app.app_context():
            verify_database()
            _, status = case_service.edit_case_stage(
                "pending_submission", case_id, staff_b_id
            )
            results["B"] = status
            if status != 200:
                raise RuntimeError(f"Staff B failed with HTTP-style status {status}")
            print("Staff B committed: edits -> pending_submission")

        release_a.set()
        worker.join(timeout=23)
        if worker.is_alive():
            raise TimeoutError("Staff A still running; cleanup deferred for safety")
        if worker_errors:
            raise RuntimeError(f"Staff A failed: {worker_errors}")

        with app.app_context():
            verify_database()
            stored = db.session.get(Case, case_id)
            entries = db.session.scalars(
                select(AuditLog)
                .where(AuditLog.case_id == case_id)
                .order_by(AuditLog.log_id)
            ).all()
            print("\n--- Observations ---")
            print(f"Service statuses: {results}")
            print(f"Final stage: {stored.case_stage}")
            print("Audit entries (in insertion order):")
            for log in entries:
                print(f"  user={log.user_id} {log.old_value} -> {log.new_value}")
            print("NOTE: This probes service logic, not HTTP routing/authentication.")
    finally:
        cancel_a.set()
        release_a.set()
        if worker is not None:
            worker.join(timeout=23)
        case_service.add_log = original_add_log

        if case_id is not None and (worker is None or not worker.is_alive()):
            with app.app_context():
                verify_database()
                owned_case = db.session.get(Case, case_id)
                if owned_case is not None and owned_case.case_status == marker:
                    try:
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
                        print(f"\nCleaned up disposable case {case_id} and its audit logs")
                    except Exception:
                        db.session.rollback()
                        print(f"Cleanup failed; inspect ONLY marked case {case_id}")
                        raise
                else:
                    print("Cleanup skipped: probe case missing or marker mismatch")
        elif case_id is not None:
            print(f"Manual cleanup required for case {case_id}: worker still active")


if __name__ == "__main__":
    main()
