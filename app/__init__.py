import os

from flask import Flask
from dotenv import load_dotenv

from app.routes.routes import routes_blueprint
from app.extensions.extensions import db, bcrypt, jwt, migrate

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///app.db"
)
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

    if test_config is not None:
        app.config.update(test_config)
    
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(routes_blueprint)
    return app