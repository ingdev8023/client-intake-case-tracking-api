from app.models.models import db, User
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from datetime import datetime, date

def add_user(user_data):

    required_fields = [
    "user_name",
    "user_email",
    "user_role"
]

    for field in required_fields:
        if not user_data.get(field):
            return {"error": f"{field} is required"}, 400

    try:
        user_to_add = User(
        user_name = user_data.get("user_name"),
        user_email= user_data.get("user_email"),
        user_role=user_data.get("user_role")
        )

        db.session.add(user_to_add)
        db.session.commit()
        
        return user_to_add.serialize(), 201
    
    except IntegrityError as e:
        db.session.rollback()

        if "UNIQUE constraint failed" in str(e):
            return {"error": "Email already exists"}, 400

        return {"error": "Database error"}, 500


def get_users():
    users = db.session.execute(select(User)).scalars().all()
    results = [user.serialize() for user in users]
    return jsonify(results), 200
    

def get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404
    return user.serialize(),200
    

        