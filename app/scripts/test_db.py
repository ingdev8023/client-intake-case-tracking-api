from app import create_app
from app.models.models import db, User, Client, Case
from datetime import date

app = create_app()

with app.app_context():

    print("Creating tables...")
    db.drop_all()
    db.create_all()

    # --- Create User ---
    """ user = User(
        user_name="Daniel",
        user_email="daniel@test.com",
        user_role="admin"
    )
    db.session.add(user) """

    # --- Create Client ---
    client = Client(
        client_first_name="John",
        client_lastname="Doe",
        client_phone="123456",
        client_email="john@test.com",
        client_address="Somewhere",
        client_date_of_birth=date(1990, 1, 1)
    )
    db.session.add(client)

    db.session.commit()

    # --- Create Case ---
    case = Case(
        case_type="VAWA",
        case_status="open",
        case_stage="intake",
        client_id=client.client_id
    )
    db.session.add(case)
    db.session.commit()

    # --- Assign User to Case (many-to-many) ---
    case.assigned_users.append(user)
    db.session.commit()

    # --- Query ---
    print("\nAssigned users to case:")
    print(case.assigned_users)

    print("\nCases for user:")
    print(user.assigned_cases)

    print("\nClient for case:")
    print(case.client.client_first_name)