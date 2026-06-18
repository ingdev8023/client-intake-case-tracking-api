def test_valid_login_returns_token(client, admin_user):
    response = client.post("/login", json={
        "user_email": "admin@test.com",
        "user_password": "Password123!"
    })

    data = response.get_json()

    assert response.status_code == 200
    assert "access_token" in data

def test_inactive_user_cannot_login(client, inactive_user):
    response = client.post("/login", json={
        "user_email": "inactive@test.com",
        "user_password": "Password123!"
    })

    assert response.status_code == 403

def test_admin_can_access_users(client, admin_token):
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200

def test_staff_cannot_access_users(client, staff_token):
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {staff_token}"}
    )

    assert response.status_code == 403