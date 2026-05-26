ALLOWED_STAGE_TRANSITIONS = {
                    "intake": ["document_collection"],
                    "document_collection": ["review"],
                    "review": ["edits"],
                    "edits": ["pending_submission", "review"],
                    "pending_submission": ["submitted"],
                    "submitted": ["closed"],
                    "closed": [],
                }