from sqlalchemy.exc import OperationalError
from app.extensions.extensions import db


def test_simulate_db_failure(client, monkeypatch):

    # 1. Define our fake database operation
    def simulate_db_failure(*args, **kwargs):
        raise OperationalError(
            "SELECT 1",
            {},
            Exception("Simulated database outage")
        )

    # 2. Replace the real execute method
    monkeypatch.setattr(
        db.session,
        "execute",
        simulate_db_failure
    )

    # 3. Make the HTTP request
    response = client.get("/ready")

    # 4. Verify the behavior
    assert response.status_code == 503
    assert response.is_json
    assert "Simulated database outage" not in response.get_data(as_text=True)
    assert response.headers.get("X-Request-ID")

def test_ready_success(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.is_json
    assert response.headers.get("X-Request-ID")