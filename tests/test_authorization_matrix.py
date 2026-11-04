import pytest
from sqlalchemy import select

from app.config.constants import AUDIT_ACTIONS
from app.extensions.extensions import db
from app.models.models import AuditLog, User


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("get", "/auth/me", None),
        ("get", "/clients", None),
        ("post", "/clients", {
            "client_first_name": "Inactive",
            "client_lastname": "Tester",
            "client_phone": "555-0100",
            "client_email": "inactive-client@test.com",
            "client_address": "Test Address",
            "client_date_of_birth": "1990-01-01",
        }),
        ("get", "/cases", None),
        ("get", "/users", None),
    ],
)
def test_inactive_token_cannot_access_protected_routes(
    client,
    inactive_token,
    method,
    path,
    json_body,
):
    request_method = getattr(client, method)
    response = request_method(
        path,
        headers={"Authorization": f"Bearer {inactive_token}"},
        json=json_body,
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "User not active"


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("get", "/users", None),
        ("post", "/users", {
            "user_name": "Unauthorized User",
            "user_email": "unauthorized@test.com",
            "user_role": "staff",
            "user_password": "Password123!",
        }),
        ("get", "/users/1", None),
        ("patch", "/users/1/deactivate", None),
        ("patch", "/users/1/activate", None),
    ],
)
def test_staff_cannot_call_admin_only_user_endpoints(
    client,
    staff_token,
    admin_user,
    method,
    path,
    json_body,
):
    path = path.replace("/users/1", f"/users/{admin_user.user_id}")
    request_method = getattr(client, method)
    response = request_method(
        path,
        headers={"Authorization": f"Bearer {staff_token}"},
        json=json_body,
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "User not authorized"


def test_admin_cannot_deactivate_self(client, admin_token, admin_user):
    response = client.patch(
        f"/users/{admin_user.user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Admin users cannot deactivate their own account"

    user = db.session.get(User, admin_user.user_id)
    assert user.is_active is True


def test_case_audit_log_uses_jwt_identity_not_request_body(
    client,
    staff_token,
    staff_user,
    admin_user,
    new_case,
):
    response = client.patch(
        f"/cases/{new_case.case_id}/status",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "case_status": "closed",
            "user_id": admin_user.user_id,
            "updated_by": admin_user.user_id,
        },
    )

    assert response.status_code == 200

    log = (
        db.session.execute(
            select(AuditLog).where(
                AuditLog.case_id == new_case.case_id,
                AuditLog.action == AUDIT_ACTIONS["CASE_STATUS_CHANGED"],
            )
        )
        .scalars()
        .one()
    )

    assert log.user_id == staff_user.user_id
    assert log.user_id != admin_user.user_id
