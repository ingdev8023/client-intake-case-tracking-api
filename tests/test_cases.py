from app.extensions.extensions import db
from sqlalchemy import select
from app.models.models import Case, Client,AuditLog, User
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

    #stage transition test

def test_valid_stage_transition(client, staff_token,staff_user,new_case):
        response = client.patch(f"/cases/{new_case.case_id}/stage", headers={"Authorization": f"Bearer {staff_token}"},json={
        "case_stage": "document_collection",
    })
        assert response.status_code == 200
        case = db.session.get(Case, new_case.case_id)
        assert case.case_stage == "document_collection"
        assert case.updated_by == staff_user.user_id

        logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_STAGE_CHANGED"]
            )
        )
        .scalars()
        .all()
        )

        assert len(logs) == 1
        assert logs[0].user_id == staff_user.user_id
        assert logs[0].old_value == "intake"
        assert logs[0].new_value == "document_collection"

def test_invalid_stage_transition(client, staff_token,new_case):
        response = client.patch(f"/cases/{new_case.case_id}/stage", headers={"Authorization": f"Bearer {staff_token}"},json={
        "case_stage": "review",
    })
        assert response.status_code == 400
        case = db.session.get(Case, new_case.case_id)
        assert case.case_stage == "intake"
        

        logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_STAGE_CHANGED"]
            )
        )
        .scalars()
        .all()
        )

        assert logs == []

def test_valid_status_update(client, staff_token,staff_user,new_case):
        response = client.patch(f"/cases/{new_case.case_id}/status", headers={"Authorization": f"Bearer {staff_token}"},json={
        "case_status": "closed",
    })
        assert response.status_code == 200
        case = db.session.get(Case, new_case.case_id)
        assert case.case_status == "closed"
        assert case.updated_by == staff_user.user_id

        logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_STATUS_CHANGED"]
            )
        )
        .scalars()
        .all()
        )

        assert len(logs) == 1
        assert logs[0].user_id == staff_user.user_id
        assert logs[0].old_value == "open"
        assert logs[0].new_value == "closed"

def test_assigned_users_update(client, staff_token,staff_user, second_staff_user, new_case):
        response = client.patch(f"/cases/{new_case.case_id}/users", headers={"Authorization": f"Bearer {staff_token}"},json={
        "action": "add",
        "user_assigned_ids": [second_staff_user.user_id],
    })
        assert response.status_code == 200
        case = db.session.get(Case, new_case.case_id)
        assigned_user_ids = [
        user.user_id for user in case.assigned_users
    ]
        assert second_staff_user.user_id in assigned_user_ids
        assert case.updated_by == staff_user.user_id

        

        logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_ASSIGNED_USERS_CHANGED"]
            )
        )
        .scalars()
        .all()
        )

        assert len(logs) == 1
        assert logs[0].user_id == staff_user.user_id
        assert logs[0].old_value == "[]"
        assert logs[0].new_value == f"[{second_staff_user.user_id}]"

def test_assigned_users_update_rejects_inactive_user(
    client,
    staff_token,
    inactive_user,
    new_case
):
    response = client.patch(
        f"/cases/{new_case.case_id}/users",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "action": "add",
            "user_assigned_ids": [inactive_user.user_id],
        },
    )

    assert response.status_code in [400, 404]

    case = db.session.get(Case, new_case.case_id)

    assigned_user_ids = [
        user.user_id for user in case.assigned_users
    ]

    assert inactive_user.user_id not in assigned_user_ids

    logs = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_ASSIGNED_USERS_CHANGED"],
            )
        )
        .scalars()
        .all()
    )

    assert logs == []