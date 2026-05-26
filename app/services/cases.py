from app.models.models import db, Case, Client, User
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, or_, text
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

def get_cases(filters={}):
    filters = filters or {}

    query = select(Case)

    allowed_filters = {
        "case_status": Case.case_status,
        "case_stage": Case.case_stage,
        "case_type": Case.case_type,
        "client_id": Case.client_id,
        "created_after": Case.created_at,
        "created_before":Case.created_at
    }

    conditions = []

    for key, value in filters.items():
        column = allowed_filters.get(key)

        if column is None:
            return {"error": f"Invalid filter: {key}"}, 400
        
        if key == "created_after":
            try:
                date_value = datetime.fromisoformat(value)
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD"}, 400

            conditions.append(column > date_value)
        elif key == "created_before":
            try:
                date_value = datetime.fromisoformat(value)
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD"}, 400
            
            conditions.append(column < date_value)
        else:
            conditions.append(column == value)


    
    cases = db.session.execute(select(Case)).scalars().all()
    results = [case.serialize() for case in cases]
    return jsonify(results), 200

def get_case(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404
    return case.serialize(),200

def edit_case(case_id, case_data):
    case = db.session.get(Case, case_id)

    if case is None:
        return jsonify({"error": "Case not found"}), 404
    if not case_data:
        return jsonify({"error": "No data to update"}), 400
    
    allowed_edits = {
        "case_status",
        "case_stage",
        "case_type",
        "client_id",
        "assigned_users_ids"
    }   
    
    try:
        for key, value in case_data.items():
            if key not in allowed_edits:
                return {"error": f"Invalid field: {key}"}, 400
            if key == "assigned_user_ids":
                if not isinstance(value, list):
                    return {"error": "assigned_user_ids must be a list"}, 400

                users = User.query.filter(User.user_id.in_(value)).all()

                if len(users) != len(value):
                    return {"error": "One or more users do not exist"}, 404

                case.assigned_users = users

            else:
            
                setattr(case, key, value)

            db.session.commit()

        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  
    
    
def delete_case(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404
        
    try:
        db.session.delete(case)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  
    return "", 204

  
    
