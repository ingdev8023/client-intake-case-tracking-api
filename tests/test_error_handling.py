def test_unexpected_error_returns_json(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["DEBUG"] = False

    @app.get("/__test_failure")
    def failing_endpoint():
        raise RuntimeError("SENSITIVE_INTERNAL_DETAIL")

    response = client.get("/__test_failure")   
    response_JSON = response.get_json()
    

    assert response_JSON['code'] == 500
    assert isinstance(response_JSON, dict) == True 
    assert response_JSON['name'] == 'Internal Server Error'
    assert response_JSON['id'] == response.headers.get("X-Request-ID")