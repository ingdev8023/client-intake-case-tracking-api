from app.extensions.extensions import db
from sqlalchemy import select
from app.models.models import Case, Client,AuditLog
from app.config.constants import AUDIT_ACTIONS

#staff cannot delete a case

def test_staff_cannot_delete_cases(client, staff_token, new_case):
    response = client.delete(f"/cases/{new_case.case_id}", headers={"Authorization": f"Bearer {staff_token}"})
    assert response.status_code == 403
    case = db.session.get(Case, new_case.case_id)

    assert case.is_deleted is False
    assert case.deleted_at is None
    assert case.deleted_by is None

    logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_SOFT_DELETED"]
            )
        )
        .scalars()
        .all()
    )

    assert logs == []

#admin delete a case

def test_admin_can_delete_cases(client, admin_token, new_case, admin_user):
    response = client.delete(f"/cases/{new_case.case_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 204
    case = db.session.get(Case, new_case.case_id)
    assert case.is_deleted is True
    assert case.deleted_by == admin_user.user_id

    case_response = client.get(f"/cases/{new_case.case_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert case_response.status_code == 404
    logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_SOFT_DELETED"]
            )
        )
        .scalars()
        .all()
    )

    assert len(logs) == 1
    assert logs[0].user_id == admin_user.user_id
    assert logs[0].old_value == "active"
    assert logs[0].new_value == "deleted"