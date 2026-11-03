from flask import current_app, g

def handle_exception(e):
    
    response = e.get_response()    
    response.data = json.dumps({
        "error": e.name,
        "request_id": g.request_id,
    })
    response.content_type = "application/json"
    return response