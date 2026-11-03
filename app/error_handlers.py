from flask import current_app, g
import json

def handle_exception(e):

    current_app.logger.error(
        "internal_server_error",
        extra={
            "request_id": g.request_id,
            "status_code": 500,
        },
    )
        
    response = e.get_response()    
    response.data = json.dumps({
        "error": e.name,
        "request_id": g.request_id,
    })
    response.content_type = "application/json"
    return response