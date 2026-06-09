from flask import jsonify
from app.models.models import db, AuditLog, Case
from sqlalchemy import select, and_, or_, text, func


def add_log(log_data):

    log_to_add = AuditLog(
       case_id = log_data.get("case_id"),
       user_id= log_data.get("user_id"),
       action= log_data.get("action"),
       old_value= log_data.get("old_value"),
       new_value=log_data.get("new_value"),
        )

    db.session.add(log_to_add)

def get_logs(case_id):
    case  = db.session.get(Case, case_id)
    if case is None or case.is_deleted:
        return jsonify({"error": "Case not found"}), 404
    logs = (db.session.execute(select(AuditLog)
                              .where(AuditLog.case_id == case_id)
                              .order_by(AuditLog.created_at.desc()))
                              .scalars()
                              .all()
    )
    results = [log.serialize() for log in logs]
    return jsonify(results), 200
