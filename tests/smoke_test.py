def test_app_is_testing(app):
    assert app.config["TESTING"] is True


def test_cases_requires_token(client):
    response = client.get("/cases")

    assert response.status_code == 401