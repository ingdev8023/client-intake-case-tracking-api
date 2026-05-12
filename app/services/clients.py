from app.models.models import db, User, Client, Case
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date

def add_client(client_data):

    required_fields = [
    "client_first_name",
    "client_lastname",
    "client_phone",
    "client_email",
    "client_address",
    "client_date_of_birth"
]

    for field in required_fields:
        if not client_data.get(field):
            return {"error": f"{field} is required"}, 400

    try:
        dob = datetime.strptime(
            client_data.get("client_date_of_birth"),
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}, 400
    

    try:
        client_to_add = Client(
        client_first_name = client_data.get("client_first_name"),
        client_lastname= client_data.get("client_lastname"),
        client_phone= client_data.get("client_phone"),
        client_email= client_data.get("client_email"),
        client_address=client_data.get("client_address"),
        client_date_of_birth= dob
        )

        db.session.add(client_to_add)
        db.session.commit()
        
        return client_to_add.serialize(), 201
    
    except IntegrityError as e:
        db.session.rollback()

        if "UNIQUE constraint failed" in str(e):
            return {"error": "Email already exists"}, 400

        return {"error": "Database error"}, 500
    

        