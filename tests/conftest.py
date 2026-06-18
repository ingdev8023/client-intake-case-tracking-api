import pytest
from app import create_app
from app.extensions.extensions import db, bcrypt
from app.models.models import User

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