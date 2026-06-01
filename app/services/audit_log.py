from flask import jsonify
from app.models.models import db, AuditLog


def add_log(log_data):

    log_to_add = AuditLog(
       case_id = log_data.get("case_id"),
       user_id= log_data.get("user_id"),
       action= log_data.get("action"),
       old_value= log_data.get("old_value"),
       new_value=log_data.get("new_value"),
        )

    db.session.add(log_to_add)
