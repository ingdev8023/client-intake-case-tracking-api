ALLOWED_STAGE_TRANSITIONS = {
                    "intake": ["document_collection"],
                    "document_collection": ["review"],
                    "review": ["edits"],
                    "edits": ["pending_submission", "review"],
                    "pending_submission": ["submitted"],
                    "submitted": ["closed"],
                    "closed": [],
                }

AUDIT_ACTIONS = {
    "CASE_STAGE_CHANGED": "case_stage_changed",
    "CASE_STATUS_CHANGED": "case_status_changed",
    "CASE_TYPE_CHANGED": "case_type_changed",
    "CASE_CLIENT_CHANGED": "case_client_changed",
    "CASE_SOFT_DELETED": "case_soft_deleted",
    "CASE_ASSIGNED_USERS_CHANGED": "case_assigned_users_changed",
}

ALLOWED_CASE_TYPES = ["VAWA","CP","AOS","FOIA"]

CASE_USERS_ACTIONS = ["delete", "add"]

USER_ROLES = {
    "ADMIN": "admin",
    "STAFF": "staff",
}