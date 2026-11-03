def test_unexpected_error_returns_json(app, client, caplog):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["DEBUG"] = False
    app.logger.addHandler(caplog.handler)

    @app.get("/__test_failure")
    def failing_endpoint():
        raise RuntimeError("SENSITIVE_INTERNAL_DETAIL")

    response = client.get("/__test_failure")   
    response_JSON = response.get_json()


   
    assert response.status_code == 500
    assert response.is_json 
    assert response_JSON['error'] == 'Internal Server Error'
    assert "SENSITIVE_INTERNAL_DETAIL" not in response.get_data(as_text=True)        
            
    try:
        records = [
                            record for record in caplog.records
                             if record.levelname == 'ERROR'
                            
                        ]
        
        record = records[0]
        
        assert record.levelname == "ERROR"
        assert record.request_id == response.headers["X-Request-ID"]

    finally:
        app.logger.removeHandler(caplog.handler)    