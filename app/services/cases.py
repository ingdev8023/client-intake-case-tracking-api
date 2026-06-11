from app.models.models import Case, Client, User
from app.extensions.extensions import db
from app.config.constants import ALLOWED_STAGE_TRANSITIONS, AUDIT_ACTIONS, ALLOWED_CASE_TYPES, CASE_USERS_ACTIONS
from app.services.audit_log import add_log
from app.extensions.extensions import db, bcrypt, jwt_required, JWTManager,get_jwt_identity
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, or_, text, func
from datetime import datetime, date, timezone
from math import ceil

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
    
           
    users = User.query.filter(User.user_id.in_(case_data["assigned_user_ids"]), User.is_active.is_(True)).all()

    if len(users) != len(case_data["assigned_user_ids"]):
        return {"error": "One or more users do not exist or are inactive"}, 404

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

def get_cases(filters=None): 
    filters = filters or {}
    try:
        page = int(filters.pop("page", 1))
        limit = int(filters.pop("limit", 10))

        if page < 1:
            return {"error": "page must be greater than 0"}, 400

        if limit < 1:
           return {"error": "limit must be greater than 0"}, 400

        if limit > 100:
            return {"error": "limit cannot exceed 100"}, 400
    except ValueError:
        return {"error": "page and limit must be integers"}, 400

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

    conditions.append(Case.is_deleted.is_(False))

    if conditions:
        query = query.where(and_(*conditions))

    #pagination
    
    count_query = select(func.count()).select_from(Case).where(and_(*conditions))
    total_items = db.session.scalar(count_query)

    paginated_query = (
        query
        .order_by(Case.created_at.desc())
        .limit(limit)
        .offset((page - 1) * limit)
    )

    cases = db.session.scalars(paginated_query).all()

    return jsonify({
        "items": [case.serialize() for case in cases],
        "pagination": {
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": ceil(total_items / limit) if limit else 0
        }
    }), 200

def get_case(case_id):
    case = db.session.get(Case, case_id)
    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404
    return case.serialize(),200

""" def edit_case(case_id, case_data, user_id):
    case = db.session.get(Case, case_id)
    user = db.session.get(User, user_id)

    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
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
            if key == "case_stage":               
                allowed_next_stages = ALLOWED_STAGE_TRANSITIONS.get(case.case_stage)

                if allowed_next_stages is None:
                    return {"error": "Current case stage is invalid"}, 500

                if value not in ALLOWED_STAGE_TRANSITIONS:
                    return {"error": f"Invalid case_stage: {value}"}, 400

                if value not in allowed_next_stages:
                    return {"error": f"Invalid stage transition: {case.case_stage} → {value}"}, 400
                
                case.case_stage = value                    
                
            else:                
                setattr(case, key, value)
                case.updated_by = user.user_id

            db.session.commit()

        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  """ 
    
def edit_case_stage(new_stage, case_id, user_id):
    case = db.session.get(Case, case_id)
    user = db.session.get(User, user_id)
    

    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
    if not new_stage:
        return jsonify({"error": "No stage to update"}), 400
    
    try:  

        allowed_next_stages = ALLOWED_STAGE_TRANSITIONS.get(case.case_stage)

        if allowed_next_stages is None:
                    return {"error": "Current case stage is invalid"}, 500

        if new_stage not in ALLOWED_STAGE_TRANSITIONS:
                    return {"error": f"Invalid case_stage: {new_stage}"}, 400

        if new_stage not in allowed_next_stages:
                    return {"error": f"Invalid stage transition: {case.case_stage} → {new_stage}"}, 400

        log = {
            "case_id": case_id,
            "user_id": user_id,
            "action": AUDIT_ACTIONS.get("CASE_STAGE_CHANGED"),
            "old_value": case.case_stage,
            "new_value": new_stage,
        }


        add_log(log)

        case.case_stage = new_stage
        case.updated_by = user.user_id

        db.session.commit()

        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  

def edit_case_status(new_status, case_id, user_id):
    case = db.session.get(Case, case_id)
    user = db.session.get(User, user_id)
    

    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
    if not new_status:
        return jsonify({"error": "No status to update"}), 400
    
    try:  

        log = {
            "case_id": case_id,
            "user_id": user_id,
            "action": AUDIT_ACTIONS.get("CASE_STATUS_CHANGED"),
            "old_value": case.case_status,
            "new_value": new_status,
        }


        add_log(log)

        case.case_status = new_status
        case.updated_by = user.user_id

        db.session.commit()

        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500

def edit_case_type(new_type, case_id, user_id):
    case = db.session.get(Case, case_id)
    user = db.session.get(User, user_id)
    

    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
    if not new_type:
        return jsonify({"error": "No case type to update"}), 400
    if case.case_type == new_type:
        return {"error": "Case type is already set to this value"}, 400
    
    try:  

        if new_type not in ALLOWED_CASE_TYPES:
                return {"error": f"Invalid case_type: {new_type}"}, 400

      
        log = {
            "case_id": case_id,
            "user_id": user_id,
            "action": AUDIT_ACTIONS.get("CASE_TYPE_CHANGED"),
            "old_value": case.case_type,
            "new_value": new_type,
        }


        add_log(log)

        case.case_type = new_type
        case.updated_by = user.user_id

        db.session.commit()

        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500

def edit_case_users(case_data, case_id, user_id):
    case = db.session.get(Case, case_id)
    acting_user = db.session.get(User, user_id)
    action = case_data.get("action")
    user_assigned_ids = case_data.get("user_assigned_ids")

    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404    
    if acting_user is None:
        return jsonify({"error": "User not found"}), 404
    if not acting_user.is_active:
        return jsonify({"error": "User not active"}), 403
    if not action:
        return jsonify({"error":"No action to perform with the users"}), 400
    if action not in CASE_USERS_ACTIONS:
        return {"error": "Invalid action. Use 'add' or 'delete'"}, 400
    if not user_assigned_ids:
        return jsonify({"error":"No users to update"}), 400
    if not isinstance(user_assigned_ids, list):
        return {"error": "assigned_user_ids must be a list"}, 400

    users = User.query.filter(User.user_id.in_(user_assigned_ids), User.is_active.is_(True)).all()
     
    if len(users) != len(user_assigned_ids):
        return {"error": "One or more users do not exist or are inactive"}, 404
    
    try:
        old_user_ids = [assigned_user.user_id for assigned_user in case.assigned_users]

        if action == "add":
            current_users = set(case.assigned_users)
            users_to_add = set(users)
            case.assigned_users = list(current_users | users_to_add)

        if action == "delete":
            case.assigned_users = [
                assigned_user
                for assigned_user in case.assigned_users
                if assigned_user not in users
            ]

        new_user_ids = [assigned_user.user_id for assigned_user in case.assigned_users]

        if sorted(old_user_ids) == sorted(new_user_ids):
            return {"error": "Assigned users did not change"}, 400

        add_log({
            "case_id": case.case_id,
            "user_id": acting_user.user_id,
            "action": AUDIT_ACTIONS["CASE_ASSIGNED_USERS_CHANGED"],
            "old_value": str(old_user_ids),
            "new_value": str(new_user_ids),
        })

        case.updated_by = acting_user.user_id

        db.session.commit()
        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500

def edit_case_client(client_id, case_id, user_id):
    case = db.session.get(Case, case_id)
    user = db.session.get(User, user_id)

    if not client_id:
        return jsonify({"error": "No client to update"}), 404
    
    client = db.session.get(Client, client_id)

    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
          
    if not client:
        return jsonify({"error": "client does not exist or is inactive"}), 400
    if client_id == case.client_id:
        return jsonify({"error":"client already assigned to this case"}), 400
    
    try:

          
        log = {
            "case_id": case_id,
            "user_id": user_id,
            "action": AUDIT_ACTIONS.get("CASE_CLIENT_CHANGED"),
            "old_value": str(case.client_id),
            "new_value": str(client_id),
        }


        add_log(log)

        case.client_id = client_id
        case.updated_by = user.user_id

        db.session.commit()

        return case.serialize(), 200

    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500

def delete_case(case_id, user_id):
    case = db.session.get(Case, case_id)
    user = db.session.get(User, user_id)
    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if not user.is_active:
        return jsonify({"error": "User not active"}), 403
    if user.user_role != 'admin':
        return jsonify({"error": "User not authorize for this action"}), 403
    try:
        case.is_deleted = True
        case.deleted_at = datetime.now(timezone.utc)
        case.deleted_by = user.user_id
        add_log({
            "case_id": case.case_id,
            "user_id": user.user_id,
            "action": AUDIT_ACTIONS.get("CASE_SOFT_DELETED"),
            "old_value": "active",
            "new_value": "deleted",
        })

        case.updated_by = user.user_id
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "Database error"}, 500  
    return "", 204

  
    
