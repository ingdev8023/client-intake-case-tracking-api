from datetime import date

from app.extensions.extensions import db
from app.models.models import Client, Case
from load_tests.query_profiler import measure_sql


def test_cases_eager_loading(
    app, client, staff_user, staff_token
):
    # Arrange: create six cases with six distinct clients.
    for i in range(6):
        test_client = Client(
            client_first_name=f"Test{i}",
            client_lastname="Client",
            client_phone=f"000000{i:04d}",
            client_email=f"regression{i}@example.test",
            client_address="Test Address",
            client_date_of_birth=date(1990, 1, 1),
        )

        case = Case(
            case_type="VAWA",
            case_status="open",
            case_stage="intake",
            client=test_client,
            assigned_users=[staff_user],
        )

        db.session.add(case)

    db.session.commit()

    expected_user_id = staff_user.user_id

    # Start with a fresh ORM session.
    db.session.remove()

    # Act: measure the real authenticated endpoint.
    with measure_sql(db.engine) as metrics:
        response = client.get(
            "/cases?page=1&limit=10",
            headers={
                "Authorization": f"Bearer {staff_token}"
            },
        )

    # Assert: response correctness.
    assert response.status_code == 200

    data = response.get_json()

    assert len(data["items"]) == 6
    assert data["pagination"]["total_items"] == 6
    assert data["pagination"]["total_pages"] == 1

    for item in data["items"]:
        assert item["client"] is not None
        assert len(item["assigned_users"]) == 1
        assert item["assigned_users"][0]["user_id"] == expected_user_id

    # Assert: SQL query count remains bounded.
    assert metrics["query_count"] <= 7, (
    f"N+1 regression: {metrics['query_count']} SQL statements"
)