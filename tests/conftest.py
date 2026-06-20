import pytest
from datetime import date
from app import create_app
from app.extensions.extensions import db, bcrypt
from app.models.models import User, Case, Client

@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def admin_user(app):
    hashed_password = bcrypt.generate_password_hash("Password123!").decode("utf-8")

    user = User(
        user_name="Admin User",
        user_email="admin@test.com",
        user_password=hashed_password,
        user_role="admin",
        is_active=True,
    )

    db.session.add(user)
    db.session.commit()

    return user

@pytest.fixture()
def staff_user(app):
    hashed_password = bcrypt.generate_password_hash("Password123!").decode("utf-8")

    user = User(
        user_name="Staff User",
        user_email="staff@test.com",
        user_password=hashed_password,
        user_role="staff",
        is_active=True,
    )

    db.session.add(user)
    db.session.commit()

    return user

@pytest.fixture()
def staff_token(client, staff_user):
    response = client.post("/login", json={
        "user_email": "staff@test.com",
        "user_password": "Password123!"
    })

    assert response.status_code == 200

    data = response.get_json()
    return data["access_token"]

@pytest.fixture()
def inactive_user(app):
    hashed_password = bcrypt.generate_password_hash("Password123!").decode("utf-8")

    user = User(
        user_name="Inactive User",
        user_email="inactive@test.com",
        user_password=hashed_password,
        user_role="staff",
        is_active=False,
    )

    db.session.add(user)
    db.session.commit()

    return user

@pytest.fixture()
def admin_token(client, admin_user):
    response = client.post("/login", json={
        "user_email": "admin@test.com",
        "user_password": "Password123!"
    })

    assert response.status_code == 200

    data = response.get_json()
    return data["access_token"]


@pytest.fixture()
def new_client(app):
    client = Client(
    client_first_name="John",
    client_lastname="Doe",
    client_phone="123456",
    client_email="john@test.com",
    client_address="Somewhere",
    client_date_of_birth=date(1990, 1, 1)
    )

    db.session.add(client)
    db.session.commit()

    return client

@pytest.fixture()
def new_case(app, new_client):
    case = Case(
    case_type="VAWA",
    case_status="open",
    case_stage="intake",
    client_id= new_client.client_id
    )
    db.session.add(case)
    db.session.commit()

    return case

@pytest.fixture()
def second_staff_user(app):
    hashed_password = bcrypt.generate_password_hash("Password123!").decode("utf-8")

    user = User(
        user_name="Second Staff User",
        user_email="staff2@test.com",
        user_password=hashed_password,
        user_role="staff",
        is_active=True,
    )

    db.session.add(user)
    db.session.commit()

    return user
