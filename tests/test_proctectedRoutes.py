def token_cannot_access_clients_route(client):
    request = client.get("/clients")
    assert request.status_code == 200