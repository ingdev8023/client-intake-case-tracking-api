from app.models.models import User
from app.config.constants import USER_ROLES
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.extensions.extensions import db, bcrypt, jwt_required, JWTManager,get_jwt_identity, create_access_token
import re


def validate_password(password):
    """
    Validates that a password has:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 special character
    """

    if not password:
        return {
            "is_valid": False,
            "error": "Password is required"
        }

    if len(password) < 8:
        return {
            "is_valid": False,
            "error": "Password must be at least 8 characters long"
        }

    if not re.search(r"[A-Z]", password):
        return {
            "is_valid": False,
            "error": "Password must contain at least one uppercase letter"
        }

    if not re.search(r"[a-z]", password):
        return {
            "is_valid": False,
            "error": "Password must contain at least one lowercase letter"
        }

    if not re.search(r"[^A-Za-z0-9]", password):
        return {
            "is_valid": False,
            "error": "Password must contain at least one special character"
        }

    return {
        "is_valid": True,
        "error": None
    }

def add_user(user_data, current_user_identity):  
    current_user = db.session.get(User, current_user_identity)
    if current_user is None:
        return jsonify({"error": "Authenticated user not found"}), 404
    if not current_user.is_active:
        return jsonify({"error": "User not active"}), 403
    if current_user.user_role != USER_ROLES["ADMIN"]:
        return {"error": "User not authorized"}, 403

    required_fields = [
    "user_name",
    "user_email",
    "user_role",
    "user_password"
]

    for field in required_fields:
        if not user_data.get(field):
            return {"error": f"{field} is required"}, 400
        
    password_validation = validate_password(user_data.get("user_password"))

    if not password_validation["is_valid"]:
        return {"error": password_validation["error"]}

    try:
        hashed_password = bcrypt.generate_password_hash(user_data.get("user_password")).decode('utf-8')

        user_to_add = User(
        user_name = user_data.get("user_name"),
        user_email= user_data.get("user_email"),
        user_role=user_data.get("user_role"),
        user_password = hashed_password
        )
        

        db.session.add(user_to_add)
        db.session.commit()
        
        return user_to_add.serialize(), 201
    
    except IntegrityError as e:
        db.session.rollback()

        if "UNIQUE constraint failed" in str(e):
            return {"error": "Email already exists"}, 400

        return {"error": "Database error"}, 500

def get_users(current_user_identity):
    current_user = db.session.get(User, current_user_identity)
    if current_user is None:
        return jsonify({"error": "Authenticated user not found"}), 404
    if not current_user.is_active:
        return jsonify({"error": "User not active"}), 403
    if current_user.user_role != USER_ROLES["ADMIN"]:
        return {"error": "User not authorized"}, 403
    
    users = (
        db.session.execute(
            select(User).where(User.is_active.is_(True))
        )
        .scalars()
        .all()
    )
    results = [user.serialize() for user in users if user.is_active]
    return jsonify(results), 200

def get_user(user_id, current_user_identity):
    current_user = db.session.get(User, current_user_identity)
    if current_user is None:
        return jsonify({"error": "Authenticated user not found"}), 404
    if not current_user.is_active:
        return jsonify({"error": "User not active"}), 403
    if current_user.user_role != USER_ROLES["ADMIN"]:
        return {"error": "User not authorized"}, 403
    
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
    return user.serialize(),200
    
def deactivate_user(user_id, current_user_identity):
    current_user = db.session.get(User, current_user_identity)
    if current_user is None:
        return jsonify({"error": "Authenticated user not found"}), 404
    if not current_user.is_active:
        return jsonify({"error": "User not active"}), 403
    if current_user.user_role != USER_ROLES["ADMIN"]:
        return {"error": "User not authorized"}, 403
    user = db.session.get(User, user_id)    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 400
    try:
        user.is_active = False
        db.session.commit()        
    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  
    return "", 204

def activate_user(user_id, current_user_identity):
    current_user = db.session.get(User, current_user_identity)
    if current_user is None:
        return jsonify({"error": "Authenticated user not found"}), 404
    if not current_user.is_active:
        return jsonify({"error": "User not active"}), 403
    if current_user.user_role != USER_ROLES["ADMIN"]:
        return {"error": "User not authorized"}, 403
    user = db.session.get(User, user_id)    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if user.is_active:
        return jsonify({"error": "User already active"}), 400    
    try:
        user.is_active = True
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  
    return user.serialize(), 200

def login(user_data):
    user_email = user_data.get("user_email")
    user_password = user_data.get("user_password")

    if not user_email:
            return {"error": "user email is required"}, 400
    
    if not user_password:
            return {"error": "user password is required"}, 400

    user = db.session.execute(select(User).where(User.user_email == user_email)).scalar_one_or_none()

    if user is None:
        return jsonify({"msg": "Bad username or password"}), 401

    if not user.is_active:
        return jsonify({"msg": "User is inactive"}), 403
    
    check_pass = bcrypt.check_password_hash(user.user_password,user_password)

    if not check_pass:
        return jsonify({"msg": "Wrong password"}), 401
    
    access_token = create_access_token(identity=str(user.user_id))

    return jsonify({
        "access_token": access_token,
        "user": user.serialize()
    }), 200

"""
{
    "user_email": "test3@test.com",
    "user_name": "Daniel",
    "user_role": "test2role",
    "user_password":"Test2345!"
  }
"""

{
    "user_email": "daniel2@test.com",
    "user_password": "Test2345!",
    "user_name":"daniel admin",
    "user_role":"admin"
}