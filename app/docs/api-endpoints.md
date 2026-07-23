# API Endpoint Documentation

This document describes the available API endpoints for the Client Intake & Case Tracking API.

The API uses JSON request and response bodies. Protected endpoints require JWT authentication using the `Authorization` header.

---

## Base URL

Local development:

```text
http://127.0.0.1:5001
```

---

## Authentication Header

Protected routes require a JWT access token.

```http
Authorization: Bearer <access_token>
```

Example:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6...
```

---

# Authentication

## Login

Authenticates a user and returns a JWT access token.

```http
POST /login
```

### Request Body

```json
{
  "user_email": "admin@test.com",
  "user_password": "Password123!"
}
```

### Successful Response

Status: `200 OK`

```json
{
  "access_token": "<jwt_token>",
  "user": {
    "user_id": 1,
    "user_name": "Admin User",
    "user_email": "admin@test.com",
    "user_role": "admin",
    "is_active": true
  }
}
```

### Error Responses

Missing email or password:

Status: `400 Bad Request`

```json
{
  "error": "user email is required"
}
```

Invalid credentials:

Status: `401 Unauthorized`

```json
{
  "msg": "Bad username or password"
}
```

Inactive user:

Status: `403 Forbidden`

```json
{
  "msg": "User is inactive"
}
```

---

## Get Current Authenticated User

Returns the authenticated user based on the JWT token.

```http
GET /auth/me
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Successful Response

Status: `200 OK`

```json
{
  "user_id": 1,
  "user_name": "Admin User",
  "user_email": "admin@test.com",
  "user_role": "admin",
  "is_active": true
}
```

### Error Responses

Missing or invalid token:

Status: `401 Unauthorized` or `422 Unprocessable Entity`

Inactive user:

Status: `403 Forbidden`

```json
{
  "error": "User not active"
}
```

---

# Users

User endpoints are protected. Some actions are restricted to admin users.

## List Users

Returns active users.

Admin only.

```http
GET /users
```

### Headers

```http
Authorization: Bearer <admin_token>
```

### Successful Response

Status: `200 OK`

```json
[
  {
    "user_id": 1,
    "user_name": "Admin User",
    "user_email": "admin@test.com",
    "user_role": "admin",
    "is_active": true
  },
  {
    "user_id": 2,
    "user_name": "Staff User",
    "user_email": "staff@test.com",
    "user_role": "staff",
    "is_active": true
  }
]
```

### Error Responses

Non-admin user:

Status: `403 Forbidden`

```json
{
  "error": "User not authorized"
}
```

---

## Create User

Creates a new user.

Admin only.

```http
POST /users
```

### Headers

```http
Authorization: Bearer <admin_token>
```

### Request Body

```json
{
  "user_name": "New Staff User",
  "user_email": "newstaff@test.com",
  "user_role": "staff",
  "user_password": "Password123!"
}
```

### Successful Response

Status: `201 Created`

```json
{
  "user_id": 3,
  "user_name": "New Staff User",
  "user_email": "newstaff@test.com",
  "user_role": "staff",
  "is_active": true
}
```

### Error Responses

Missing required fields:

Status: `400 Bad Request`

```json
{
  "error": "Missing required field"
}
```

Invalid role:

Status: `400 Bad Request`

```json
{
  "error": "Invalid user role"
}
```

Duplicate email:

Status: `400 Bad Request`

```json
{
  "error": "User email already exists"
}
```

---

## Get User by ID

Returns a single user by ID.

```http
GET /users/<user_id>
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Successful Response

Status: `200 OK`

```json
{
  "user_id": 1,
  "user_name": "Admin User",
  "user_email": "admin@test.com",
  "user_role": "admin",
  "is_active": true
}
```

### Error Responses

User not found:

Status: `404 Not Found`

```json
{
  "error": "User not found"
}
```

---

## Activate User

Activates an inactive user.

Admin only.

```http
PATCH /users/<user_id>/activate
```

### Headers

```http
Authorization: Bearer <admin_token>
```

### Successful Response

Status: `200 OK`

```json
{
  "user_id": 2,
  "user_name": "Staff User",
  "user_email": "staff@test.com",
  "user_role": "staff",
  "is_active": true
}
```

---

## Deactivate User

Deactivates an active user.

Admin only.

```http
PATCH /users/<user_id>/deactivate
```

### Headers

```http
Authorization: Bearer <admin_token>
```

### Successful Response

Status: `200 OK`

```json
{
  "user_id": 2,
  "user_name": "Staff User",
  "user_email": "staff@test.com",
  "user_role": "staff",
  "is_active": false
}
```

---

# Clients

Client endpoints are protected.

## List Clients

Returns all clients.

```http
GET /clients
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Successful Response

Status: `200 OK`

```json
[
  {
    "client_id": 1,
    "client_first_name": "John",
    "client_lastname": "Doe",
    "client_phone": "123456",
    "client_email": "john@test.com",
    "client_address": "Somewhere",
    "client_date_of_birth": "1990-01-01"
  }
]
```

---

## Create Client

Creates a new client.

```http
POST /clients
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "client_first_name": "John",
  "client_lastname": "Doe",
  "client_phone": "123456",
  "client_email": "john@test.com",
  "client_address": "Somewhere",
  "client_date_of_birth": "1990-01-01"
}
```

### Successful Response

Status: `201 Created`

```json
{
  "client_id": 1,
  "client_first_name": "John",
  "client_lastname": "Doe",
  "client_phone": "123456",
  "client_email": "john@test.com",
  "client_address": "Somewhere",
  "client_date_of_birth": "1990-01-01"
}
```

---

## Get Client by ID

Returns a single client.

```http
GET /clients/<client_id>
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Successful Response

Status: `200 OK`

```json
{
  "client_id": 1,
  "client_first_name": "John",
  "client_lastname": "Doe",
  "client_phone": "123456",
  "client_email": "john@test.com",
  "client_address": "Somewhere",
  "client_date_of_birth": "1990-01-01"
}
```

### Error Responses

Client not found:

Status: `404 Not Found`

```json
{
  "error": "Client not found"
}
```

---

## Update Client

Updates client information.

```http
PUT /clients/<client_id>
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "client_phone": "987654",
  "client_address": "New Address"
}
```

### Successful Response

Status: `200 OK`

```json
{
  "client_id": 1,
  "client_first_name": "John",
  "client_lastname": "Doe",
  "client_phone": "987654",
  "client_email": "john@test.com",
  "client_address": "New Address",
  "client_date_of_birth": "1990-01-01"
}
```

---

# Cases

Case endpoints are protected.

## List Cases

Returns paginated cases. Soft-deleted cases are excluded.

```http
GET /cases
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Query Parameters

| Parameter        | Description                      |
| ---------------- | -------------------------------- |
| `case_status`    | Filter by case status            |
| `case_stage`     | Filter by workflow stage         |
| `case_type`      | Filter by case type              |
| `client_id`      | Filter by client ID              |
| `created_after`  | Filter cases created after date  |
| `created_before` | Filter cases created before date |
| `page`           | Page number                      |
| `limit`          | Results per page                 |

### Example Request

```http
GET /cases?case_status=open&case_stage=intake&page=1&limit=10
```

### Successful Response

Status: `200 OK`

```json
{
  "items": [
    {
      "case_id": 1,
      "case_type": "VAWA",
      "case_status": "open",
      "case_stage": "intake",
      "client_id": 1,
      "is_deleted": false,
      "created_at": "2026-06-20T12:00:00",
      "updated_at": "2026-06-20T12:00:00",
      "updated_by": 1,
      "deleted_at": null,
      "deleted_by": null,
      "client": {
        "client_id": 1,
        "client_first_name": "John",
        "client_lastname": "Doe"
      },
      "assigned_users": []
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_items": 1,
    "total_pages": 1
  }
}
```

---

## Create Case

Creates a new case and optionally assigns users.

```http
POST /cases
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "case_type": "VAWA",
  "case_status": "open",
  "case_stage": "intake",
  "client_id": 1,
  "assigned_user_ids": [1, 2]
}
```

### Successful Response

Status: `201 Created`

```json
{
  "case_id": 1,
  "case_type": "VAWA",
  "case_status": "open",
  "case_stage": "intake",
  "client_id": 1,
  "is_deleted": false,
  "assigned_users": [
    {
      "user_id": 1,
      "user_name": "Admin User",
      "user_email": "admin@test.com",
      "user_role": "admin",
      "is_active": true
    }
  ]
}
```

### Error Responses

Client not found:

Status: `404 Not Found`

```json
{
  "error": "Client not found"
}
```

One or more assigned users invalid or inactive:

Status: `404 Not Found`

```json
{
  "error": "One or more users do not exist or are inactive"
}
```

---

## Get Case by ID

Returns a single case. Soft-deleted cases return `404`.

```http
GET /cases/<case_id>
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Successful Response

Status: `200 OK`

```json
{
  "case_id": 1,
  "case_type": "VAWA",
  "case_status": "open",
  "case_stage": "intake",
  "client_id": 1,
  "is_deleted": false,
  "assigned_users": []
}
```

### Error Responses

Case not found or soft deleted:

Status: `404 Not Found`

```json
{
  "error": "Case not found"
}
```

---

## Soft Delete Case

Soft deletes a case.

Admin only.

```http
DELETE /cases/<case_id>
```

### Headers

```http
Authorization: Bearer <admin_token>
```

### Successful Response

Status: `204 No Content`

No response body.

### Behavior

When a case is soft deleted:

* `is_deleted` is set to `true`
* `deleted_at` is set
* `deleted_by` is set to the authenticated admin user
* The case no longer appears in `GET /cases`
* `GET /cases/<case_id>` returns `404`
* A soft delete audit log is created

### Error Responses

Staff user attempts to delete:

Status: `403 Forbidden`

```json
{
  "error": "User not authorized for this action"
}
```

Case not found:

Status: `404 Not Found`

```json
{
  "error": "Case not found"
}
```

---

# Case Workflow Actions

The API uses command-style endpoints for case updates. These endpoints represent specific business actions and create audit logs when changes are successful.

---

## Update Case Stage

Updates a case stage if the transition is valid.

```http
PATCH /cases/<case_id>/stage
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "case_stage": "document_collection"
}
```

### Successful Response

Status: `200 OK`

```json
{
  "case_id": 1,
  "case_stage": "document_collection",
  "updated_by": 2
}
```

### Valid Workflow Stages

```text
intake
document_collection
review
edits
pending_submission
submitted
closed
```

### Example Valid Transition

```text
intake -> document_collection
```

### Example Invalid Transition

```text
intake -> submitted
```

### Invalid Transition Response

Status: `400 Bad Request`

```json
{
  "error": "Invalid stage transition"
}
```

### Audit Log

Successful stage updates create an audit log with:

```text
action: CASE_STAGE_CHANGED
old_value: previous stage
new_value: new stage
user_id: authenticated token user
```

---

## Update Case Status

Updates a case status.

```http
PATCH /cases/<case_id>/status
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "case_status": "closed"
}
```

### Successful Response

Status: `200 OK`

```json
{
  "case_id": 1,
  "case_status": "closed",
  "updated_by": 2
}
```

### Audit Log

Successful status updates create an audit log with:

```text
action: CASE_STATUS_CHANGED
old_value: previous status
new_value: new status
user_id: authenticated token user
```

---

## Update Case Type

Updates the case type.

```http
PATCH /cases/<case_id>/type
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "case_type": "AOS"
}
```

### Successful Response

Status: `200 OK`

```json
{
  "case_id": 1,
  "case_type": "AOS",
  "updated_by": 2
}
```

### Audit Log

Successful type updates create an audit log with:

```text
action: CASE_TYPE_CHANGED
old_value: previous type
new_value: new type
user_id: authenticated token user
```

---

## Update Assigned Users

Adds or removes assigned users from a case.

```http
PATCH /cases/<case_id>/users
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Add Users Request Body

```json
{
  "action": "add",
  "user_assigned_ids": [2, 3]
}
```

### Remove Users Request Body

```json
{
  "action": "delete",
  "user_assigned_ids": [2]
}
```

### Successful Response

Status: `200 OK`

```json
{
  "case_id": 1,
  "assigned_users": [
    {
      "user_id": 3,
      "user_name": "Case Manager",
      "user_email": "manager@test.com",
      "user_role": "staff",
      "is_active": true
    }
  ],
  "updated_by": 2
}
```

### Error Responses

Invalid action:

Status: `400 Bad Request`

```json
{
  "error": "Invalid action. Use 'add' or 'delete'"
}
```

No users provided:

Status: `400 Bad Request`

```json
{
  "error": "No users to update"
}
```

One or more users invalid or inactive:

Status: `404 Not Found`

```json
{
  "error": "One or more users do not exist or are inactive"
}
```

No change detected:

Status: `400 Bad Request`

```json
{
  "error": "Assigned users did not change"
}
```

### Audit Log

Successful assigned user updates create an audit log with:

```text
action: CASE_ASSIGNED_USERS_CHANGED
old_value: previous assigned user IDs
new_value: new assigned user IDs
user_id: authenticated token user
```

---

## Reassign Case Client

Updates the client linked to a case.

```http
PATCH /cases/<case_id>/client
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "client_id": 2
}
```

### Successful Response

Status: `200 OK`

```json
{
  "case_id": 1,
  "client_id": 2,
  "updated_by": 2
}
```

### Error Responses

Client not found:

Status: `404 Not Found`

```json
{
  "error": "Client not found"
}
```

No change detected:

Status: `400 Bad Request`

```json
{
  "error": "Case already belongs to this client"
}
```

### Audit Log

Successful client reassignment creates an audit log with:

```text
action: CASE_CLIENT_CHANGED
old_value: previous client ID
new_value: new client ID
user_id: authenticated token user
```

---

# Audit Logs

## Get Case Audit Logs

Returns audit logs for a case.

```http
GET /logs/<case_id>
```

### Headers

```http
Authorization: Bearer <access_token>
```

### Successful Response

Status: `200 OK`

```json
[
  {
    "log_id": 1,
    "case_id": 1,
    "user_id": 2,
    "action": "CASE_STAGE_CHANGED",
    "old_value": "intake",
    "new_value": "document_collection",
    "created_at": "2026-06-20T12:00:00"
  }
]
```

### Error Responses

Case not found or soft deleted:

Status: `404 Not Found`

```json
{
  "error": "Case not found"
}
```

---

# Common Error Responses

## Missing Token

Status: `401 Unauthorized`

```json
{
  "msg": "Missing Authorization Header"
}
```

---

## Invalid Token

Status: `401 Unauthorized` or `422 Unprocessable Entity`

```json
{
  "msg": "Not enough segments"
}
```

---

## Invalid JSON Body

Status: `400 Bad Request`

```json
{
  "error": "Invalid JSON"
}
```

---

## Not Found

Status: `404 Not Found`

```json
{
  "error": "Resource not found"
}
```

---

## Unauthorized Role

Status: `403 Forbidden`

```json
{
  "error": "User not authorized"
}
```

---

# Notes for Frontend Integration

A frontend should:

1. Send user credentials to `POST /login`
2. Store the returned JWT access token
3. Include the token in protected requests using the `Authorization` header
4. Use `GET /auth/me` to identify the logged-in user after page reload
5. Hide or show UI actions based on `user_role`
6. Handle `401` by redirecting to login
7. Handle `403` by showing a permissions message

Example frontend request:

```javascript
fetch("http://127.0.0.1:5000/cases", {
  method: "GET",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  }
})
```

---

# Notes

This API documentation reflects the current backend implementation and is intended to help with:

* Manual API testing
* Frontend integration
* Future automated testing
* Portfolio review
* Developer onboarding


#changing something to test the conexion with github