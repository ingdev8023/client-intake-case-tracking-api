def test_token_cannot_access_clients_route(client):
    response = client.get("/clients")
    assert response.status_code == 401

def test_cases_with_invalid_token_is_rejected(client):
    response = client.get(
        "/cases",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code in [401, 422]

def test_cases_with_valid_token_succeeds(client, staff_token):
    response = client.get(
        "/cases",
        headers={"Authorization": f"Bearer {staff_token}"}
    )

    assert response.status_code == 200