from app.models.models import Client
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from datetime import datetime, date
from app.extensions.extensions import db

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


def get_clients():
    clients = db.session.execute(select(Client)).scalars().all()
    results = [client.serialize() for client in clients]
    return jsonify(results), 200
    

def get_client(client_id):
    client = db.session.get(Client, client_id)
    if client is None:
        return jsonify({"error": "Client not found"}), 404
    return client.serialize(),200
    

def update_client(client_id, client_data):
    client = db.session.get(Client, client_id)

    if client is None:
        return jsonify({"error": "Client not found"}), 404

    if not client_data:
        return {"error": "No data to update"}, 400

    allowed_edits = {
        "client_first_name",
        "client_lastname",
        "client_phone",
        "client_email",
        "client_date_of_birth",
        "client_address"
    }

    try:
        for key, value in client_data.items():
            if key not in allowed_edits:
                return {"error": f"Invalid field: {key}"}, 400
            if key == "client_date_of_birth":
                try:
                    value = date.fromisoformat(value)
                except ValueError:
                    return {"error": "Invalid date format. Use YYYY-MM-DD"}, 400
                           
            setattr(client, key, value)
                
        
        db.session.commit()

        return client.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Email already exists or database constraint failed"}, 400
           