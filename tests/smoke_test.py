def test_app_is_testing(app):
    assert app.config["TESTING"] is True


def test_cases_requires_token(client):
    response = client.get("/cases")

    assert response.status_code == 401

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
    