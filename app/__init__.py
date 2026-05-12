from flask import Flask
from app.routes.routes import routes_blueprint
from app.models.models import db

def create_app():
    app = Flask(__name__)

    app.register_blueprint(routes_blueprint)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    
    db.init_app(app)

    return app