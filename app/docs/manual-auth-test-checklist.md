# Manual Auth Test Checklist

## Purpose

This checklist validates authentication, authorization, user state, and audit logging behavior for the Client Intake & Case Tracking API.

---

## Test Users Required

Create at least:

- Admin user
- Staff user
- Inactive user

---

## 1. Login with valid admin credentials

### Request

POST `/auth/login`

### Expected

- Status: `200`
- Response includes `access_token`
- Response includes user data
- User role is `admin`

---

## 2. Login with invalid password

### Request

POST `/auth/login`

### Expected

- Status: `401`
- Response: bad username or password

---

## 3. Login with inactive user

### Request

POST `/auth/login`

### Expected

- Status: `403`
- User cannot log in

---

## 4. Access protected endpoint without token

### Request

GET `/cases`

### Expected

- Status: `401`
- Request is rejected

---

## 5. Access protected endpoint with invalid token

### Request

GET `/cases`

Header:

Authorization: Bearer invalid-token

### Expected

- Request is rejected
- User does not receive protected data

---

## 6. Access protected endpoint with valid token

### Request

GET `/cases`

Header:

Authorization: Bearer `<valid_token>`

### Expected

- Status: `200`
- Case list is returned

---

## 7. Staff user attempts to soft delete a case

### Request

DELETE `/cases/<case_id>`

Header:

Authorization: Bearer `<staff_token>`

### Expected

- Status: `403`
- Case is not deleted
- No delete audit log is created

---

## 8. Admin user soft deletes a case

### Request

DELETE `/cases/<case_id>`

Header:

Authorization: Bearer `<admin_token>`

### Expected

- Status: `204`
- Case is soft deleted
- Case no longer appears in GET `/cases`
- Audit log is created with action `case_soft_deleted`

---

## 9. Stage update uses authenticated user

### Request

PATCH `/cases/<case_id>/stage`

Header:

Authorization: Bearer `<valid_token>`

Body:

{
  "case_stage": "document_collection"
}

### Expected

- Status: `200`
- Case stage is updated
- `updated_by` matches token user
- Audit log `user_id` matches token user

---

## 10. Invalid stage transition is rejected

### Request

PATCH `/cases/<case_id>/stage`

Body:

{
  "case_stage": "submitted"
}

### Expected

- Status: `400`
- Invalid transition error
- Case stage does not change
- No audit log is created

---

## 11. Assigned users update rejects inactive users

### Request

PATCH `/cases/<case_id>/users`

Body:

{
  "action": "add",
  "user_assigned_ids": [<inactive_user_id>]
}

### Expected

- Status: `404` or `400`
- Inactive user is not assigned
- No audit log is created

---

## 12. Authenticated current user profile

### Request

GET `/auth/me`

Header:

Authorization: Bearer `<valid_token>`

### Expected

- Status: `200`
- Response returns current authenticated user
- Response does not include password