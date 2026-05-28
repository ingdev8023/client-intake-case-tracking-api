from flask import Blueprint, request, Response, jsonify
from app.services.clients import add_client, get_clients, get_client, update_client
from app.services.users import add_user, get_users, get_user
from app.services.cases import add_case, get_cases, get_case, edit_case, delete_case

routes_blueprint = Blueprint("routes", __name__)

@routes_blueprint.route("/health")
def health():
    return {"message": "API running"}

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

@routes_blueprint.route("/cases/<int:case_id>/<int:user_id>", methods=["PUT", "DELETE"])
def case_edit(case_id, user_id):
    if request.method == "DELETE":
        return delete_case(case_id, user_id)
    case_data = request.get_json()
    if not case_data:
        return {"error": "Invalid JSON"}, 400
    return edit_case(case_id, case_data, user_id)

@routes_blueprint.route("/users", methods=["POST", "GET"])
def users():
    if request.method == "POST":
        user_data = request.get_json()
        if not user_data:
            return {"error": "Invalid JSON"}, 400
        
        return add_user(user_data)
    return get_users()

@routes_blueprint.route("/users/<int:user_id>")
def retrieve_user(user_id):
    return get_user(user_id)
    
    




    
    