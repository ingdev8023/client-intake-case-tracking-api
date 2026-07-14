import click
from sqlalchemy.exc import IntegrityError

from app.extensions.extensions import db, bcrypt
from app.models.models import User
from app.config.constants import USER_ROLES


def register_cli_commands(app):
    @app.cli.command("create-admin")
    @click.option("--name", prompt="Admin name")
    @click.option("--email", prompt="Admin email")
    @click.option(
        "--password",
        prompt="Admin password",
        hide_input=True,
        confirmation_prompt=True,
    )
    def create_admin(name, email, password):
        
        existing_user = User.query.filter_by(user_email=email).first()

        if existing_user:
            click.echo("User with this email already exists.")
            return

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        admin = User(
            user_name=name,
            user_email=email,
            user_role=USER_ROLES["ADMIN"],
            user_password=hashed_password,
            is_active=True,
        )

        try:
            db.session.add(admin)
            db.session.commit()
            click.echo(f"Admin user created successfully: {email}")

        except IntegrityError:
            db.session.rollback()
            click.echo("Database error: could not create admin user.")