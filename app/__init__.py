import os
import uuid
import json
from datetime import datetime, timezone

from flask import Flask, g, request
import logging
from time import perf_counter
from dotenv import load_dotenv

from app.routes.routes import routes_blueprint
from app.extensions.extensions import db, bcrypt, jwt, migrate, cors
from app.cli import register_cli_commands
from app.logging_config import configure_logging


load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)
    configure_logging(app)
    def get_allowed_origins():
        origins = os.getenv("CORS_ORIGINS", "")
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

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

    allowed_origins = get_allowed_origins()

    cors.init_app(
    app,
    resources={
        r"/*": {
            "origins": allowed_origins
        }
    },
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=False,
    )

    @app.before_request
    def request_start():
        g.start_time = perf_counter()
        g.request_id = str(uuid.uuid4())



    @app.after_request
    def log_request(response):
        duration_ms = (perf_counter() - g.start_time) * 1000
        app.logger.info(
            "http_request",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "route": (
                    request.url_rule.rule
                    if request.url_rule else "unmatched"
                ),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )        
                        
        response.headers["X-Request-ID"] = g.request_id
        return response


    register_cli_commands(app)
    app.register_blueprint(routes_blueprint)





    return app





