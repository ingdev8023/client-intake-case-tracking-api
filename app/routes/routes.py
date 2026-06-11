from flask import Blueprint, request, Response, jsonify
from app.services.clients import add_client, get_clients, get_client, update_client
from app.services.users import add_user, get_users, get_user,deactivate_user, activate_user, login
from app.services.audit_log import get_logs
from app.services.cases import add_case, get_cases, get_case,delete_case, edit_case_stage,edit_case_status, edit_case_type, edit_case_users, edit_case_client


routes_blueprint = Blueprint("routes", __name__)

@routes_blueprint.route("/health")
def health():
    return {"message": "API running"}

@routes_blueprint.route("/login", methods=["POST"])
def login_route():
    user_data = request.get_json()
    if not user_data:
        return {"error": "Invalid JSON"}, 400
    return login(user_data)

@routes_blueprint.route("/clients", methods=["POST", "GET"])
def clients():
    if request.method == "POST":
        client_data = request.get_json()
        if not client_data:
            return {"error": "Invalid JSON"}, 400
        return add_client(client_data)
    return get_clients()

@routes_blueprint.route("/clients/<int:client_id>", methods=["PUT", "GET"])
def retrieve_client(client_id):
    if request.method == "PUT":
        client_data= request.get_json()
        if not client_data:
            return {"error": "Invalid JSON"}, 400
        return update_client(client_id,client_data)
    return get_client(client_id)

@routes_blueprint.route("/cases", methods=["POST", "GET"])
def cases():
    if request.method == "POST":
        case_data = request.get_json()
        if not case_data:
            return {"error": "Invalid JSON"}, 400
        return add_case(case_data)
    
    return get_cases(request.args.to_dict())

@routes_blueprint.route("/cases/<int:case_id>")
def retrieve_case(case_id):
    return get_case(case_id)

@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>", methods=["DELETE"])
def case_edit(case_id, user_id):
    return delete_case(case_id, user_id)
    
@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>/stage", methods=["PATCH"])
def case_stage_edit(case_id, user_id):
    case_data = request.get_json()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_stage(case_data.get("case_stage"), case_id,user_id)

@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>/status", methods=["PATCH"])
def case_status_edit(case_id, user_id):
    case_data = request.get_json()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_status(case_data.get("case_status"), case_id,user_id)

@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>/type", methods=["PATCH"])
def case_type_edit(case_id, user_id):
    case_data = request.get_json()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_type(case_data.get("case_type"), case_id,user_id)

@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>/users", methods=["PATCH"])
def case_users_edit(case_id, user_id):
    case_data = request.get_json()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_users(case_data, case_id,user_id)

@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>/client", methods=["PATCH"])
def case_client_edit(case_id, user_id):
    case_data = request.get_json()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_client(case_data.get("client_id"), case_id,user_id)

@routes_blueprint.route("/users", methods=["POST", "GET"])
def users():
    if request.method == "POST":
        user_data = request.get_json()
        if not user_data:
            return {"error": "Invalid JSON"}, 400        
        return add_user(user_data)
    return get_users()

@routes_blueprint.route("/users/<int:user_id>", methods=["GET"])
def get_user_route(user_id):
    return get_user(user_id)

@routes_blueprint.route("/users/<int:user_id>/deactivate", methods=["PATCH"])
def deactivate_user_route(user_id):
    return deactivate_user(user_id)

@routes_blueprint.route("/users/<int:user_id>/activate", methods=["PATCH"])
def active_user_route(user_id):
    return(activate_user(user_id))    

@routes_blueprint.route("/logs/<int:case_id>")
def get_logs_route(case_id):
    return get_logs(case_id)

@routes_blueprint.route("/login")
def register_user_login_info_route():
    login_data = request.get_json()
    if not login_data:
        return {"error": "Invalid JSON"}, 400
    return register_user_login_info(login_data)
    
    