def test_unexpected_error_returns_json(app, client, caplog):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["DEBUG"] = False
    app.logger.addHandler(caplog.handler)

    @app.get("/__test_failure")
    def failing_endpoint():
        raise RuntimeError("SENSITIVE_INTERNAL_DETAIL")
    try:
        response = client.get("/__test_failure")   
        response_JSON = response.get_json()

        records = [
                    record for record in caplog.records
                    if record.getMessage() == "internal_server_error"              
                                ]
        assert len(records) == 1    
        record = records[0]
   
        assert response.status_code == 500
        assert response.is_json 
        assert response_JSON['error'] == 'Internal Server Error'
        assert response_JSON["request_id"] == response.headers["X-Request-ID"]
        assert "SENSITIVE_INTERNAL_DETAIL" not in response.get_data(as_text=True)        
        assert record.levelname == "ERROR"
        assert record.request_id == response.headers["X-Request-ID"]

    finally:
        app.logger.removeHandler(caplog.handler)    