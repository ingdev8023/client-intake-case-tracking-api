#valid login test
def test_valid_login_returns_token(client, admin_user):
    response = client.post("/login", json={
        "user_email": "admin@test.com",
        "user_password": "Password123!"
    })

    data = response.get_json()

    assert response.status_code == 200
    assert "access_token" in data

def test_valid_staff_login_returns_token(client, staff_user):
    response = client.post("/login", json={
        "user_email": "staff@test.com",
        "user_password": "Password123!"
    })

    data = response.get_json()

    assert response.status_code == 200
    assert "access_token" in data

#invalid password test

import pytest

@pytest.mark.parametrize("email,password", [
    ("staff@test.com", "invalidpassword"),
    ("unknown@test.com", "Password123!"),
    ("inactive@test.com", "Password123!"),
])
def test_generic_login_failure(
    client, staff_user, inactive_user, email, password
):
    response = client.post("/login", json={
        "user_email": email,
        "user_password": password,
    })

    assert response.status_code == 401
    assert response.is_json
    assert response.get_json() == {
        "msg": "Bad username or password"
    }
    assert "access_token" not in response.get_json()
    assert response.headers.get("X-Request-ID")
    
#missing password test

def test_missing_pass_login(client, staff_user):
    response = client.post("/login", json={
        "user_email": "staff@test.com",
        
    })

    data = response.get_json()

    assert response.status_code == 400
    assert response.get_json()["error"] == "user password is required"
#missing email test 

def test_missing_email_login(client, staff_user):
    response = client.post("/login", json={
        "user_password": "Password123!",
        
    })

    data = response.get_json()

    assert response.status_code == 400
    assert response.get_json()["error"] == "user email is required"

#return token valid  login test
def test_admin_can_access_users(client, admin_token):
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200

#invalid role access to route

def test_staff_cannot_access_users(client, staff_token):
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {staff_token}"}
    )

    assert response.status_code == 403
