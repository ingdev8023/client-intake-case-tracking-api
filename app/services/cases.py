from app.models.models import db, Case, Client, User
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from datetime import datetime, date


def add_case(case_data):
    required_fields = [
    "case_type",
    "case_status",
    "case_stage",
    "client_id",
    "assigned_user_ids"
    ]

    for field in required_fields:
        if not case_data.get(field):
            return {"error": f"{field} is required"}, 400
    
    client = db.session.get(Client, case_data["client_id"])

    if client is None:
        return jsonify({"error": "Client does not exist"}), 404
    
           
    users = User.query.filter(
        User.user_id.in_(case_data["assigned_user_ids"])
    ).all()

    if len(users) != len(case_data["assigned_user_ids"]):
        return {"error": "One or more users do not exist"}, 404


    try:
        case_to_add = Case(
        case_type = case_data.get("case_type"),
        case_status= case_data.get("case_status"),
        case_stage= case_data.get("case_stage"),
        client_id= case_data.get("client_id")
        )

        case_to_add.assigned_users.extend(users)
        db.session.add(case_to_add)
         
        db.session.commit()
        
        return case_to_add.serialize(), 201
    
    except IntegrityError:

        db.session.rollback()

        return {"error": "Database error"}, 500

def get_cases():
    cases = db.session.execute(select(Case)).scalars().all()
    results = [case.serialize() for case in cases]
    return jsonify(results), 200

def get_case(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404
    return case.serialize(),200
    
