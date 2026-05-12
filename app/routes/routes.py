from flask import Blueprint, request, Response
from app.services.clients import add_client

routes_blueprint = Blueprint("routes", __name__)

@routes_blueprint.route("/health")
def health():
    return {"message": "API running"}

@routes_blueprint.route("/clients", methods=["POST"])
def add_clients():
    client_data = request.get_json()
    if not client_data:
        return {"error": "Invalid JSON"}, 400

    return add_client(client_data)