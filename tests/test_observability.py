import uuid

def test_health_has_request_id(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    request_id = response.headers["X-Request-ID"]

    assert uuid.UUID(request_id).version == 4

def test_health_not_same_request_id(client):
    response1 = client.get("/health")
    response2 = client.get("/health")

    request_id1 = response1.headers["X-Request-ID"]
    request_id2 = response2.headers["X-Request-ID"]

    assert request_id1 != request_id2

def test_cases_has_request_id(client):
    response = client.get("/cases")

    assert response.status_code == 401
    assert "X-Request-ID" in response.headers

def test_not_real_route_has_request_id(client):
    response = client.get("/not-a-real-route")

    assert response.status_code == 404
    assert "X-Request-ID" in response.headers

    

    

    