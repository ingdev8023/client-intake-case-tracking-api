import os

from flask import Flask
from dotenv import load_dotenv

from app.routes.routes import routes_blueprint
from app.extensions.extensions import db, bcrypt, jwt

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///app.db"
)
    
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(routes_blueprint)
    return app