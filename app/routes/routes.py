from functools import wraps

from flask import Blueprint, request, Response, jsonify
from app.models.models import User
from app.services.clients import add_client, get_clients, get_client, update_client
from app.services.users import add_user, get_users, get_user,deactivate_user, activate_user, login, get_current_user
from app.services.audit_log import get_logs
from app.services.cases import add_case, get_cases, get_case,delete_case, edit_case_stage,edit_case_status, edit_case_type, edit_case_users, edit_case_client
from app.extensions.extensions import db, bcrypt, jwt_required, JWTManager,get_jwt_identity

routes_blueprint = Blueprint("routes", __name__)

def active_jwt_required(route_handler):
    @wraps(route_handler)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        try:
            user_id = int(current_user_id)
        except (TypeError, ValueError):
            return {"error": "Invalid token identity"}, 401

        user = db.session.get(User, user_id)

        if user is None:
            return {"error": "Authenticated user not found"}, 404

        if not user.is_active:
            return {"error": "User not active"}, 403

        return route_handler(*args, **kwargs)

    return wrapper

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
@active_jwt_required
def clients():
    if request.method == "POST":
        client_data = request.get_json()
        if not client_data:
            return {"error": "Invalid JSON"}, 400
        return add_client(client_data)
    return get_clients()

@routes_blueprint.route("/clients/<int:client_id>", methods=["PUT", "GET"])
@active_jwt_required
def retrieve_client(client_id):
    if request.method == "PUT":
        client_data= request.get_json()
        if not client_data:
            return {"error": "Invalid JSON"}, 400
        return update_client(client_id,client_data)
    return get_client(client_id)

@routes_blueprint.route("/cases", methods=["POST", "GET"])
@active_jwt_required
def cases():    
    if request.method == "POST":
        case_data = request.get_json()
        if not case_data:
            return {"error": "Invalid JSON"}, 400
        return add_case(case_data)
    
    return get_cases(request.args.to_dict())

@routes_blueprint.route("/cases/<int:case_id>")
@active_jwt_required
def retrieve_case(case_id):
    return get_case(case_id)

@routes_blueprint.route("/cases/<int:case_id>", methods=["DELETE"])
@active_jwt_required
def case_edit(case_id):
    current_user_identity = get_jwt_identity()
    return delete_case(case_id, current_user_identity)
    
@routes_blueprint.route("/cases/<int:case_id>/stage", methods=["PATCH"])
@active_jwt_required
def case_stage_edit(case_id):
    case_data = request.get_json()
    current_user_identity = get_jwt_identity()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_stage(case_data.get("case_stage"), case_id,current_user_identity)

@routes_blueprint.route("/cases/<int:case_id>/status", methods=["PATCH"])
@active_jwt_required
def case_status_edit(case_id):
    case_data = request.get_json()
    current_user_identity = get_jwt_identity()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_status(case_data.get("case_status"), case_id,current_user_identity)

@routes_blueprint.route("/cases/<int:case_id>/type", methods=["PATCH"])
@active_jwt_required
def case_type_edit(case_id):
    case_data = request.get_json()
    current_user_identity = get_jwt_identity()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_type(case_data.get("case_type"), case_id,current_user_identity)

@routes_blueprint.route("/cases/<int:case_id>/users", methods=["PATCH"])
@active_jwt_required
def case_users_edit(case_id):
    case_data = request.get_json()
    current_user_identity = get_jwt_identity()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_users(case_data, case_id,current_user_identity)

@routes_blueprint.route("/cases/<int:case_id>/client", methods=["PATCH"])
@active_jwt_required
def case_client_edit(case_id):
    case_data = request.get_json()
    current_user_identity = get_jwt_identity()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case_client(case_data.get("client_id"), case_id,current_user_identity)

@routes_blueprint.route("/users", methods=["POST", "GET"])
@active_jwt_required
def users():
    current_user_identity = get_jwt_identity()
    if request.method == "POST":
        user_data = request.get_json()
        if not user_data:
            return {"error": "Invalid JSON"}, 400        
        return add_user(user_data, current_user_identity)
    return get_users(current_user_identity)

@routes_blueprint.route("/users/<int:user_id>", methods=["GET"])
@active_jwt_required
def get_user_route(user_id):
    current_user_identity = get_jwt_identity()
    return get_user(user_id, current_user_identity)

@routes_blueprint.route("/users/<int:user_id>/deactivate", methods=["PATCH"])
@active_jwt_required
def deactivate_user_route(user_id):
    current_user_identity = get_jwt_identity()
    return deactivate_user(user_id,current_user_identity)

@routes_blueprint.route("/users/<int:user_id>/activate", methods=["PATCH"])
@active_jwt_required
def active_user_route(user_id):
    current_user_identity = get_jwt_identity()
    return activate_user(user_id, current_user_identity)    

@routes_blueprint.route("/logs/<int:case_id>")
@active_jwt_required
def get_logs_route(case_id):
    return get_logs(case_id)

@routes_blueprint.route("/auth/me")
@active_jwt_required
def get_current_user_route():
    current_user_id = get_jwt_identity()
    return get_current_user(current_user_id)
