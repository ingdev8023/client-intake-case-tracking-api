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

def test_invalid_pass_login(client, staff_user):
    response = client.post("/login", json={
        "user_email": "staff@test.com",
        "user_password": "invalidpassword"
    })

    data = response.get_json()

    assert response.status_code == 401

#invalid email test 

def test_invalid_email_login(client, staff_user):
    response = client.post("/login", json={
        "user_email": "invaliadstaff@test.com",
        "user_password": "Password123!"
    })

    data = response.get_json()

    assert response.status_code == 401
    
#missing password test

def test_missing_pass_login(client, staff_user):
    response = client.post("/login", json={
        "user_email": "staff@test.com",
        
    })

    data = response.get_json()

    assert response.status_code == 400

#missing email test 

def test_missing_email_login(client, staff_user):
    response = client.post("/login", json={
        "user_password": "Password123!",
        
    })

    data = response.get_json()

    assert response.status_code == 400


#inactive user test
def test_inactive_user_cannot_login(client, inactive_user):
    response = client.post("/login", json={
        "user_email": "inactive@test.com",
        "user_password": "Password123!"
    })

    assert response.status_code == 403

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
