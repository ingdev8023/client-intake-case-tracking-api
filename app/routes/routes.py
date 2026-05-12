from flask import Blueprint, request, Response
from app.services.clients import add_client, get_clients, get_client

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

@routes_blueprint.route("/clients/<int:client_id>")
def retrieve_client(client_id):
    return get_client(client_id)
    
    