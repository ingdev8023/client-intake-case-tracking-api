import logging
import json
from app.logging_config import JsonFormatter

def test_logger():

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        msg="formatter_test",
        pathname=__file__,
        lineno=1,
        args=(),
        exc_info=None,       
        )

    record.request_id = "test_id"
    record.status_code = 200
    record.duration_ms = 0.2

    result = JsonFormatter().format(record)
    data = json.loads(result)
  
    assert isinstance(data, dict)
    assert data["level"] == "INFO"
    assert data["message"] == "formatter_test"
    assert data["request_id"] == "test_id"
    assert data["status_code"] == 200
    assert data["duration_ms"] == 0.2
    assert "timestamp" in data
    
