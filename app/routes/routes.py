from flask import Blueprint

routes_blueprint = Blueprint("routes", __name__)

@routes_blueprint.route("/health")
def health():
    return {"message": "API running"}