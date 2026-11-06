import click
from app.extensions.extensions import db, bcrypt
from app.models.models import User, Client, Case
from app.config.constants import USER_ROLES
from sqlalchemy import text
from load_tests.synthetic_data import generate_synthetic_clients, generate_synthetic_users, generate_synthetic_cases
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


def verify_perf_database():
    """Refuse to proceed outside the designated performance DB."""

    with db.engine.connect() as connection:
        user, database = connection.execute(
            text("SELECT current_user, current_database()")
        ).one()

    if (
        user != "client_perf_user"
        or database != "client_intake_perf"
    ):
        raise click.ClickException(
            "Seeding refused: incorrect database or role."
        )

    click.echo(f"Verified: {user} @ {database}")
    

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


    @app.cli.command("seed-perf")           
    def seed_perf():
        verify_perf_database()

        if Client.query.first() or Case.query.first():
            raise click.ClickException(
                "Performance database already contains clients or cases."
            )

        if User.query.filter(
            User.user_email.like("test_user%@test.test")
        ).first():
            raise click.ClickException(
                "Synthetic users already exist."
            )

        clients = generate_synthetic_clients(count=500)
        users = generate_synthetic_users(count=100)
        cases = generate_synthetic_cases(clients,users, count=1000)
        
        
        try:
                db.session.add_all(clients)
                db.session.add_all(users)
                db.session.add_all(cases)
                db.session.commit()
                click.echo(f"{len(clients)} clients created successfully")
                click.echo(f"{len(users)} users created successfully")
                click.echo(f"{len(cases)} cases created successfully")
        except SQLAlchemyError as e:
                db.session.rollback()
                raise click.ClickException(
                "Database integrity error while creating synthetic clients."
                )
        
        

