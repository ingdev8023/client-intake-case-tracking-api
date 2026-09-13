# Authorization Matrix

## Purpose

This document reviews backend authentication and authorization rules endpoint by endpoint for the Client Intake & Case Tracking API.

The frontend can hide or show UI actions based on role, but the backend remains the source of truth. Protected routes must require a JWT, admin-only actions must verify the current user role on the server, and case audit logs must use the authenticated JWT identity rather than user IDs supplied by the request body.

---

## Access Levels

| Access level | Meaning |
| --- | --- |
| Public | No JWT required. Intentionally reachable without authentication. |
| Authenticated | Requires `Authorization: Bearer <token>` and an active user. Both `admin` and `staff` may call it. |
| Admin-only | Requires `Authorization: Bearer <token>`, an active user, and `user_role == "admin"` verified by the backend. |

Protected routes use `active_jwt_required`, which wraps `@jwt_required()` and rejects inactive or missing users before the route handler runs.

---

## Endpoint Matrix

| Method | Endpoint | Access level | Backend enforcement | Notes |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | Public | No JWT decorator | Intentionally public health check. Does not expose protected records. |
| `POST` | `/login` | Public | No JWT decorator; validates credentials in `login()` | Intentionally public so users can authenticate. Inactive users cannot log in. |
| `GET` | `/auth/me` | Authenticated | `active_jwt_required`; user loaded from JWT identity | Returns the current active authenticated user. |
| `GET` | `/clients` | Authenticated | `active_jwt_required` | Staff and admin can list clients. |
| `POST` | `/clients` | Authenticated | `active_jwt_required` | Staff and admin can create clients. |
| `GET` | `/clients/<client_id>` | Authenticated | `active_jwt_required` | Staff and admin can view a client. |
| `PUT` | `/clients/<client_id>` | Authenticated | `active_jwt_required` | Staff and admin can update client data. |
| `GET` | `/cases` | Authenticated | `active_jwt_required` | Staff and admin can list non-deleted cases. |
| `POST` | `/cases` | Authenticated | `active_jwt_required` | Staff and admin can create cases. |
| `GET` | `/cases/<case_id>` | Authenticated | `active_jwt_required` | Staff and admin can view a non-deleted case. |
| `DELETE` | `/cases/<case_id>` | Admin-only | `active_jwt_required`; `delete_case()` checks `user_role == "admin"` | Soft delete remains admin-only. Staff receives `403`. |
| `PATCH` | `/cases/<case_id>/stage` | Authenticated | `active_jwt_required`; route passes `get_jwt_identity()` to `edit_case_stage()` | Audit log `user_id` and `updated_by` come from JWT identity. |
| `PATCH` | `/cases/<case_id>/status` | Authenticated | `active_jwt_required`; route passes `get_jwt_identity()` to `edit_case_status()` | Audit log `user_id` and `updated_by` come from JWT identity. |
| `PATCH` | `/cases/<case_id>/type` | Authenticated | `active_jwt_required`; route passes `get_jwt_identity()` to `edit_case_type()` | Audit log `user_id` and `updated_by` come from JWT identity. |
| `PATCH` | `/cases/<case_id>/users` | Authenticated | `active_jwt_required`; route passes `get_jwt_identity()` to `edit_case_users()` | Acting user comes from JWT. Assigned users must exist and be active. |
| `PATCH` | `/cases/<case_id>/client` | Authenticated | `active_jwt_required`; route passes `get_jwt_identity()` to `edit_case_client()` | Audit log `user_id` and `updated_by` come from JWT identity. |
| `GET` | `/logs/<case_id>` | Authenticated | `active_jwt_required` | Staff and admin can view audit logs for a non-deleted case. |
| `GET` | `/users` | Admin-only | `active_jwt_required`; `get_users()` checks `user_role == "admin"` | Staff receives `403`. |
| `POST` | `/users` | Admin-only | `active_jwt_required`; `add_user()` checks `user_role == "admin"` | User creation remains admin-only. |
| `GET` | `/users/<user_id>` | Admin-only | `active_jwt_required`; `get_user()` checks `user_role == "admin"` | Staff receives `403`. |
| `PATCH` | `/users/<user_id>/activate` | Admin-only | `active_jwt_required`; `activate_user()` checks `user_role == "admin"` | User activation remains admin-only. |
| `PATCH` | `/users/<user_id>/deactivate` | Admin-only | `active_jwt_required`; `deactivate_user()` checks `user_role == "admin"` | User deactivation remains admin-only. Current admin cannot deactivate their own account. |

---

## Public Endpoint Decisions

### `GET /health`

Decision: intentionally public.

Reason:

* Required for local, LAN, Nginx, tunnel, and deploy health checks.
* Returns only a generic API status message.
* Does not expose users, clients, cases, audit logs, database details, or secrets.

### `POST /login`

Decision: intentionally public.

Reason:

* Users need this endpoint to obtain a JWT.
* Invalid credentials return `401`.
* Inactive users return `403`.
* Password hashes are never returned.

---

## Confirmed Rules

### Protected endpoints require JWT

All non-public routes use `active_jwt_required`, which wraps `@jwt_required()`. Requests without a token are rejected before protected data is returned.

Confirmed by tests:

* `tests/test_proctectedRoutes.py::test_token_cannot_access_clients_route`
* `tests/test_proctectedRoutes.py::test_cases_with_invalid_token_is_rejected`
* `tests/test_proctectedRoutes.py::test_cases_with_valid_token_succeeds`

### Inactive users cannot perform protected actions

Inactive users cannot log in. If an inactive user still has an old token, `active_jwt_required` rejects protected requests with `403`.

Confirmed by tests:

* `tests/test_auth.py::test_inactive_user_cannot_login`
* `tests/test_authorization_matrix.py::test_inactive_token_cannot_access_protected_routes`

### Staff users cannot call admin-only user endpoints

Admin-only user management endpoints check the current JWT user role in the service layer. Staff users receive `403`.

Confirmed by tests:

* `tests/test_auth.py::test_staff_cannot_access_users`
* `tests/test_authorization_matrix.py::test_staff_cannot_call_admin_only_user_endpoints`

### User creation remains admin-only

`POST /users` requires an active JWT and `user_role == "admin"` in `add_user()`.

Confirmed by tests:

* `tests/test_authorization_matrix.py::test_staff_cannot_call_admin_only_user_endpoints`

### User activation and deactivation remain admin-only

`PATCH /users/<user_id>/activate` and `PATCH /users/<user_id>/deactivate` require an active admin user.

Confirmed by tests:

* `tests/test_authorization_matrix.py::test_staff_cannot_call_admin_only_user_endpoints`

### Current admin cannot deactivate themselves

Decision: block self-deactivation.

Reason:

* Prevents an admin from accidentally locking out the active admin session.
* Keeps user management recoverable for the MVP.

Confirmed by tests:

* `tests/test_authorization_matrix.py::test_admin_cannot_deactivate_self`

### Soft delete case remains admin-only

`DELETE /cases/<case_id>` requires an active admin user in `delete_case()`. Staff users receive `403`, the case remains active, and no soft-delete audit log is created.

Confirmed by tests:

* `tests/test_cases.py::test_staff_cannot_delete_cases`
* `tests/test_cases.py::test_admin_can_delete_cases`

### Case workflow endpoints use JWT identity

Case workflow route handlers read the acting user from `get_jwt_identity()` and pass it to the service layer. The request body is not trusted for `user_id` or `updated_by`.

Confirmed by tests:

* `tests/test_cases.py::test_valid_stage_transition`
* `tests/test_cases.py::test_valid_status_update`
* `tests/test_cases.py::test_assigned_users_update`
* `tests/test_authorization_matrix.py::test_case_audit_log_uses_jwt_identity_not_request_body`

### Audit logs record authenticated user

Audit logs for case workflow changes and soft delete use the authenticated JWT user. A client cannot spoof audit ownership by sending `user_id` or `updated_by` in the JSON body.

Confirmed by tests:

* `tests/test_cases.py::test_admin_can_delete_cases`
* `tests/test_cases.py::test_valid_stage_transition`
* `tests/test_cases.py::test_valid_status_update`
* `tests/test_cases.py::test_assigned_users_update`
* `tests/test_authorization_matrix.py::test_case_audit_log_uses_jwt_identity_not_request_body`

---

## Follow-Up Security Issues

These are not blockers for the current frontend MVP, but they should be tracked as follow-up GitHub issues.

### 1. Validate allowed user roles on user creation

Current behavior:

* `POST /users` is admin-only.
* The service currently accepts the submitted `user_role` value if required fields are present.

Risk:

* An admin could accidentally create a user with an unsupported role string.

Recommended issue:

```text
Validate user_role against allowed backend roles when creating users
```

Acceptance criteria:

* `POST /users` only accepts `admin` or `staff`.
* Invalid roles return `400`.
* Tests cover invalid role rejection.

### 2. Decide whether audit logs should be admin-only

Current behavior:

* `GET /logs/<case_id>` is authenticated.
* Staff and admin can read audit logs for any non-deleted case.

Risk:

* This may be acceptable for the MVP, but audit log visibility is a product/security decision.

Recommended issue:

```text
Decide and enforce audit log visibility rules
```

Acceptance criteria:

* Product decision documented: authenticated, assigned-user-only, or admin-only.
* Backend tests match the chosen rule.

### 3. Decide whether client and case access should be assignment-scoped

Current behavior:

* Any active authenticated user can list and update clients.
* Any active authenticated user can list and update cases.

Risk:

* This is acceptable for an internal MVP if all staff can work all cases, but it is broader than assignment-scoped access.

Recommended issue:

```text
Decide whether case and client access should be restricted by assignment
```

Acceptance criteria:

* Product decision documented.
* If assignment-scoped access is required, list/detail/update queries enforce it server-side.
* Tests cover assigned and unassigned staff access.

### 4. Add JWT revocation or token freshness policy

Current behavior:

* Inactive users are rejected on protected routes even if they still hold an old token.
* There is no token blocklist or explicit logout invalidation.

Risk:

* Deactivation is enforced, but individual tokens cannot be revoked without changing user state or JWT secret.

Recommended issue:

```text
Add JWT revocation or token freshness policy
```

Acceptance criteria:

* Logout or administrative token revocation strategy is documented.
* Tests cover revoked token rejection if implemented.

---

## Test Command

Run the authorization/security-focused tests:

```bash
python -m pytest tests/test_authorization_matrix.py tests/test_auth.py tests/test_proctectedRoutes.py tests/test_cases.py -v
```

On this Windows project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_authorization_matrix.py tests/test_auth.py tests/test_proctectedRoutes.py tests/test_cases.py -v
```

Latest local result:

```text
Security-focused command: 31 passed
Full test suite: 33 passed
```

Warnings observed:

```text
InsecureKeyLengthWarning for the test JWT secret
```

The warning comes from the short test secret configured in `tests/conftest.py`; production and deployed environments should use a strong `JWT_SECRET_KEY`.

## Current Authorization Decisions

- Public endpoints are limited to `/health` and `/login`.
- All client, case, user, and log endpoints require an active authenticated user unless explicitly marked admin-only.
- User management is admin-only.
- Case soft delete is admin-only.
- Case workflow updates are allowed for active authenticated users.
- Audit logs are currently visible to active authenticated users.
- Case/client access is currently not assignment-scoped.
- Current admin self-deactivation is blocked.

## Accepted MVP Tradeoffs

The current authorization model is intentionally simple for the MVP.

Accepted for now:

- Any active staff user can view and update any non-deleted case.
- Any active staff user can view and update clients.
- Audit logs are visible to all active authenticated users.
- JWT access tokens are stateless and do not currently support individual token revocation.

These decisions should be revisited before handling real client data or multi-team production usage.