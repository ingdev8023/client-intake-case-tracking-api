"""M2-05: verify case-stage and audit-log rollback with injected audit failure.

Run only against disposable data in client_intake_perf as client_perf_user.
No production HTTP service is invoked and no source files are modified.
"""

from sqlalchemy import delete, func, select, text

from app import create_app
from app.extensions.extensions import db
from app.models.models import AuditLog, Case, Client, User
from app.services import cases as cases_service

EXPECTED_DATABASE = "client_intake_perf"
EXPECTED_ROLE = "client_perf_user"


def verify_connection():
    if db.engine.dialect.name != "postgresql":
        raise RuntimeError("Refusing to run: this experiment requires PostgreSQL")
    database, role = db.session.execute(
        text("SELECT current_database(), current_user")
    ).one()
    if (database, role) != (EXPECTED_DATABASE, EXPECTED_ROLE):
        raise RuntimeError(f"Refusing unsafe connection: {database} / {role}")
    print(f"Connection verified: {database} (role: {role})")


def broken_add_log(log_data):
    """Deliberately violate audit_log.action's NOT NULL constraint on commit."""
    db.session.add(
        AuditLog(
            case_id=log_data["case_id"],
            user_id=log_data["user_id"],
            action=None,
            old_value=log_data["old_value"],
            new_value=log_data["new_value"],
        )
    )


def main():
    app = create_app()
    case_id = None
    with app.app_context():
        try:
            verify_connection()
            client_id = db.session.scalar(
                select(Client.client_id).order_by(Client.client_id).limit(1)
            )
            user_id = db.session.scalar(
                select(User.user_id)
                .where(User.is_active.is_(True))
                .order_by(User.user_id)
                .limit(1)
            )
            if client_id is None or user_id is None:
                raise RuntimeError("Performance DB needs a client and active user")

            case = Case(
                case_type="VAWA",
                case_status="open",
                case_stage="edits",
                client_id=client_id,
            )
            db.session.add(case)
            db.session.commit()
            case_id = case.case_id
            print(f"Disposable case created: {case_id} (stage: edits)")

            original_add_log = cases_service.add_log
            try:
                cases_service.add_log = broken_add_log
                _response, status = cases_service.edit_case_stage(
                    "review", case_id, user_id
                )
            finally:
                cases_service.add_log = original_add_log

            # Use a fresh session so the verification cannot read stale ORM state.
            db.session.remove()
            persisted_case = db.session.get(Case, case_id)
            stage = persisted_case.case_stage if persisted_case else None
            audit_count = db.session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.case_id == case_id)
            )

            print("\n--- Observations ---")
            print(f"Service HTTP-equivalent status: {status} (expected: 500)")
            print(f"Persisted stage: {stage} (expected: edits)")
            print(f"Audit entries: {audit_count} (expected: 0)")

            assert status == 500, "Injected audit failure was not rejected"
            assert stage == "edits", "Stage update survived the failed commit"
            assert audit_count == 0, "Partial audit entry survived the failed commit"
            print("PASS: Case update and audit insertion rolled back together.")
        finally:
            # Cleanup runs even if an assertion or application operation fails.
            db.session.rollback()
            db.session.remove()
            if case_id is not None:
                verify_connection()
                db.session.execute(
                    delete(AuditLog).where(AuditLog.case_id == case_id)
                )
                disposable_case = db.session.get(Case, case_id)
                if disposable_case is not None:
                    db.session.delete(disposable_case)
                db.session.commit()
                print(f"Cleaned up disposable case {case_id} and its audit logs")
            db.session.remove()


if __name__ == "__main__":
    main()
