from sqlalchemy import select, func

from app.extensions.extensions import db
from app.models.models import Client, User, Case

from load_tests.synthetic_data import (
    generate_synthetic_clients,
    generate_synthetic_users,
    generate_synthetic_cases,
)


def test_synthetic_data(app):
    clients = generate_synthetic_clients()
    users = generate_synthetic_users()
    cases = generate_synthetic_cases(clients, users)

    assert len(clients) == 4
    assert len(users) == 4
    assert len(cases) == 5

    db.session.add_all(clients)
    db.session.add_all(users)
    db.session.add_all(cases)
    db.session.commit()

    assert db.session.scalar(
        select(func.count()).select_from(Client)
    ) == 4

    assert db.session.scalar(
        select(func.count()).select_from(User)
    ) == 4

    assert db.session.scalar(
        select(func.count()).select_from(Case)
    ) == 5

    saved_case = db.session.scalar(select(Case).limit(1))

    assert saved_case.client is not None
    assert len(saved_case.assigned_users) == 1