from app import create_app

from load_tests.synthetic_data import (
    generate_synthetic_clients,
    generate_synthetic_users,
    generate_synthetic_cases,
)

app = create_app(test_config={
    "JWT_SECRET_KEY": "x" * 48,
    "SQLALCHEMY_DATABASE_URI": "sqlite://",
})

with app.app_context():
    clients = generate_synthetic_clients()
    users = generate_synthetic_users()
    cases = generate_synthetic_cases(clients, users)

    assert len(clients) == 4
    assert len(users) == 4
    assert len(cases) == 5

    for case in cases:
        assert case.client in clients
        assert len(case.assigned_users) >= 1
        assert all(user in users for user in case.assigned_users)

    print("Synthetic object generation passed!")