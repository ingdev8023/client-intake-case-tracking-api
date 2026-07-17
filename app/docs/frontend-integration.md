# Frontend Integration Guide

This document explains how a frontend application should connect to the Client Intake & Case Tracking API.

The goal is to define a clear contract between the frontend and backend before building the user interface.

---

## 1. Integration Overview

The frontend will communicate with the Flask backend API using HTTP requests.

The backend currently provides:

* JWT authentication
* Role-based authorization
* Protected API routes
* CORS support
* Case management endpoints
* Client management endpoints
* User management endpoints
* Audit log endpoints

The frontend must handle:

* Login
* Token storage
* Authenticated requests
* User role detection
* Protected routes/pages
* API error handling
* CORS configuration
* Logout behavior

---

## 2. Backend Base URLs

The frontend should use an environment variable for the backend API URL.

Do not hardcode the API URL directly inside components.

### Local backend development

When running the Flask API locally:

```text
http://127.0.0.1:5001
```

Example frontend environment variable:

```env
VITE_API_BASE_URL=http://127.0.0.1:5001
```

### Server/LAN backend development

When calling the API through Nginx on the local network:

```text
http://<SERVER_LOCAL_IP>
```

Example:

```env
VITE_API_BASE_URL=http://192.168.101.14
```

### Future production backend

When a domain is configured:

```env
VITE_API_BASE_URL=https://api.example.com
```

---

## 3. Authentication Flow

The API uses JWT authentication.

The frontend logs in by sending user credentials to:

```http
POST /login
```

### Login request

```javascript
const response = await fetch(`${API_BASE_URL}/login`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    user_email: email,
    user_password: password
  })
});
```

### Expected successful response

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

The frontend should store:

* `access_token`
* current user object or user profile state

---

## 4. Token Storage Strategy

For the first frontend version, the access token can be stored in `localStorage`.

Example:

```javascript
localStorage.setItem("access_token", data.access_token);
```

To read the token:

```javascript
const token = localStorage.getItem("access_token");
```

To logout:

```javascript
localStorage.removeItem("access_token");
```

### Security note

`localStorage` is simple and works for this stage, but it has security tradeoffs. If malicious JavaScript runs in the browser, it can read the token.

For this project stage, `localStorage` is acceptable for learning and portfolio development.

Future improvement:

* use short-lived access tokens
* consider refresh tokens
* consider secure HTTP-only cookies if the architecture changes
* improve frontend XSS protection

---

## 5. Authenticated Requests

Protected backend routes require this header:

```http
Authorization: Bearer <access_token>
```

Example:

```javascript
const token = localStorage.getItem("access_token");

const response = await fetch(`${API_BASE_URL}/cases`, {
  method: "GET",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  }
});
```

The frontend should centralize this logic in an API client/helper instead of repeating it in every component.

Recommended helper:

```javascript
export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("access_token");

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  return response;
}
```

---

## 6. Current User Flow

After login or page refresh, the frontend should identify the authenticated user by calling:

```http
GET /auth/me
```

Example:

```javascript
const response = await apiRequest("/auth/me");

if (response.ok) {
  const user = await response.json();
  setCurrentUser(user);
}
```

### Why this matters

When the browser reloads, the frontend may still have a token but not the user object in memory.

`GET /auth/me` lets the frontend ask:

```text
Who is the currently authenticated user?
```

This helps the frontend:

* restore the logged-in session
* display the user name
* identify the user role
* show or hide admin-only UI
* redirect unauthenticated users to login

---

## 7. Role-Based Frontend Behavior

The backend currently supports these roles:

```text
admin
staff
```

The backend is the source of truth for permissions.

The frontend can use roles to improve user experience, but it must not be trusted for security.

### Admin users

Admin users can see UI actions for:

* viewing users
* creating users
* activating users
* deactivating users
* soft deleting cases

Example frontend check:

```javascript
const isAdmin = currentUser?.user_role === "admin";
```

Admin-only UI example:

```javascript
{isAdmin && (
  <button onClick={handleDeleteCase}>
    Delete Case
  </button>
)}
```

### Staff users

Staff users can see UI actions for:

* viewing cases
* updating case stage
* updating case status
* updating assigned users
* viewing clients
* updating workflow-related fields

Staff users should not see admin-only controls such as:

* create user
* deactivate user
* soft delete case

### Important security note

Even if the frontend hides a button, the backend must still enforce permissions.

Frontend role checks are for user experience.

Backend role checks are for security.

---

## 8. Recommended Frontend Routes

The frontend may eventually include pages like:

```text
/login
/dashboard
/cases
/cases/:caseId
/clients
/clients/:clientId
/users
/audit-logs/:caseId
```

Suggested access rules:

| Page                  | Access                                                         |
| --------------------- | -------------------------------------------------------------- |
| `/login`              | Public                                                         |
| `/dashboard`          | Authenticated users                                            |
| `/cases`              | Authenticated users                                            |
| `/cases/:caseId`      | Authenticated users                                            |
| `/clients`            | Authenticated users                                            |
| `/users`              | Admin only                                                     |
| `/audit-logs/:caseId` | Authenticated users or admin, depending on final product rules |

---

## 9. API Endpoints Used by the Frontend

### Authentication

```http
POST /login
GET /auth/me
```

### Users

```http
GET /users
POST /users
GET /users/<user_id>
PATCH /users/<user_id>/activate
PATCH /users/<user_id>/deactivate
```

### Clients

```http
GET /clients
POST /clients
GET /clients/<client_id>
PUT /clients/<client_id>
```

### Cases

```http
GET /cases
POST /cases
GET /cases/<case_id>
DELETE /cases/<case_id>
```

### Case workflow actions

```http
PATCH /cases/<case_id>/stage
PATCH /cases/<case_id>/status
PATCH /cases/<case_id>/type
PATCH /cases/<case_id>/users
PATCH /cases/<case_id>/client
```

### Audit logs

```http
GET /logs/<case_id>
```

---

## 10. Case List Integration

The frontend should call:

```http
GET /cases
```

The endpoint supports pagination and filters.

Example:

```javascript
const response = await apiRequest("/cases?page=1&limit=10");
const data = await response.json();
```

Expected response shape:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_items": 0,
    "total_pages": 0
  }
}
```

The frontend should use:

```text
data.items
data.pagination
```

for rendering lists and pagination controls.

### Filter examples

```http
GET /cases?case_status=open
GET /cases?case_stage=intake
GET /cases?case_type=VAWA
GET /cases?client_id=1
GET /cases?page=2&limit=10
```

Combined example:

```http
GET /cases?case_status=open&case_stage=intake&page=1&limit=10
```

---

## 11. Case Workflow Integration

The API uses command-style endpoints for case workflow actions.

This means the frontend should not send one large generic update for every case change.

Instead, each UI action should call the specific backend endpoint.

### Update stage

```javascript
await apiRequest(`/cases/${caseId}/stage`, {
  method: "PATCH",
  body: JSON.stringify({
    case_stage: "document_collection"
  })
});
```

### Update status

```javascript
await apiRequest(`/cases/${caseId}/status`, {
  method: "PATCH",
  body: JSON.stringify({
    case_status: "closed"
  })
});
```

### Update type

```javascript
await apiRequest(`/cases/${caseId}/type`, {
  method: "PATCH",
  body: JSON.stringify({
    case_type: "AOS"
  })
});
```

### Update assigned users

```javascript
await apiRequest(`/cases/${caseId}/users`, {
  method: "PATCH",
  body: JSON.stringify({
    action: "add",
    user_assigned_ids: [2, 3]
  })
});
```

Remove assigned users:

```javascript
await apiRequest(`/cases/${caseId}/users`, {
  method: "PATCH",
  body: JSON.stringify({
    action: "delete",
    user_assigned_ids: [2]
  })
});
```

### Reassign client

```javascript
await apiRequest(`/cases/${caseId}/client`, {
  method: "PATCH",
  body: JSON.stringify({
    client_id: 2
  })
});
```

---

## 12. CORS Requirements

The backend uses controlled CORS configuration.

Allowed origins are configured with:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

For a frontend running on another machine in the LAN, add the frontend origin:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.101.13:5173
```

For production:

```env
CORS_ORIGINS=https://frontend-domain.com
```

### Important CORS rules

Do not use wildcard origins for protected production APIs.

Avoid:

```env
CORS_ORIGINS=*
```

The backend must allow the `Authorization` header because the frontend sends JWT tokens:

```http
Authorization: Bearer <token>
```

The backend CORS configuration should allow:

```text
Content-Type
Authorization
```

and methods:

```text
GET
POST
PUT
PATCH
DELETE
OPTIONS
```

---

## 13. Common Error Handling

The frontend should handle the following status codes intentionally.

### `400 Bad Request`

Usually means invalid input or missing required fields.

Frontend behavior:

* show validation message
* keep user on the same form
* highlight invalid fields if possible

Example:

```json
{
  "error": "Invalid JSON"
}
```

---

### `401 Unauthorized`

Usually means the user is not authenticated or the token is missing.

Frontend behavior:

* clear stored token
* redirect user to login
* show session/login message

Example:

```json
{
  "msg": "Missing Authorization Header"
}
```

---

### `403 Forbidden`

User is authenticated but not allowed to perform the action.

Frontend behavior:

* show permission error
* do not redirect to login automatically
* optionally hide the restricted UI for that role

Example:

```json
{
  "error": "User not authorized"
}
```

---

### `404 Not Found`

Resource does not exist or is hidden because it was soft deleted.

Frontend behavior:

* show not found message
* optionally redirect back to list page

Example:

```json
{
  "error": "Case not found"
}
```

---

### `422 Unprocessable Entity`

Often happens with malformed JWT tokens or invalid request structure.

Frontend behavior:

* if token-related, clear token and redirect to login
* if request-related, show an error message

---

## 14. Logout Flow

Logout is handled on the frontend by removing the token.

```javascript
function logout() {
  localStorage.removeItem("access_token");
  setCurrentUser(null);
  navigate("/login");
}
```

There is currently no backend logout endpoint because JWT access tokens are stateless.

Future improvement:

* token blocklist
* refresh tokens
* token expiration handling
* backend logout endpoint

---

## 15. Suggested Frontend API Client Structure

Recommended frontend structure:

```text
src/
├── api/
│   ├── client.js
│   ├── authApi.js
│   ├── casesApi.js
│   ├── clientsApi.js
│   └── usersApi.js
├── auth/
│   ├── AuthProvider.jsx
│   └── ProtectedRoute.jsx
├── pages/
├── components/
└── main.jsx
```

### `client.js`

Centralizes API base URL, token header, and response handling.

### `authApi.js`

Handles:

```text
login
getCurrentUser
logout helper
```

### `casesApi.js`

Handles:

```text
list cases
get case
create case
update stage
update status
update type
update assigned users
reassign client
soft delete case
```

### `clientsApi.js`

Handles:

```text
list clients
get client
create client
update client
```

### `usersApi.js`

Handles admin-only user management.

---

## 16. Example API Client

```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("access_token");

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    localStorage.removeItem("access_token");
  }

  return response;
}
```

---

## 17. Example Login Helper

```javascript
import { apiRequest } from "./client";

export async function login(email, password) {
  const response = await apiRequest("/login", {
    method: "POST",
    body: JSON.stringify({
      user_email: email,
      user_password: password
    })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || data.msg || "Login failed");
  }

  localStorage.setItem("access_token", data.access_token);

  return data.user;
}
```

---

## 18. Example Current User Helper

```javascript
import { apiRequest } from "./client";

export async function getCurrentUser() {
  const response = await apiRequest("/auth/me");

  if (!response.ok) {
    throw new Error("Unable to load current user");
  }

  return response.json();
}
```

---

## 19. Example Protected Request

```javascript
import { apiRequest } from "./client";

export async function getCases(page = 1, limit = 10) {
  const response = await apiRequest(`/cases?page=${page}&limit=${limit}`);

  if (!response.ok) {
    throw new Error("Unable to load cases");
  }

  return response.json();
}
```

---

## 20. Example Role-Based UI Logic

```javascript
function CaseActions({ currentUser, caseItem }) {
  const isAdmin = currentUser?.user_role === "admin";

  return (
    <div>
      <button>Update Stage</button>
      <button>Update Status</button>

      {isAdmin && (
        <button>
          Soft Delete Case
        </button>
      )}
    </div>
  );
}
```

---

## 21. Frontend Development Checklist

Before building the frontend, confirm:

* backend is running locally or on LAN server
* `/health` responds
* `/login` works with an admin user
* `GET /auth/me` works with token
* `GET /cases` returns `401` without token
* `GET /cases` works with token
* CORS allows the frontend origin
* `Authorization` header is allowed in CORS preflight
* frontend has `VITE_API_BASE_URL`
* frontend can store and send JWT token

---

## 22. Codex Prompt Context

When using Codex to build the frontend, provide this guide as part of the project context.

Important backend facts for Codex:

```text
Backend API uses JWT authentication.
Login endpoint is POST /login.
JWT token must be sent with Authorization: Bearer <token>.
Current user endpoint is GET /auth/me.
Admin users have user_role = "admin".
Staff users have user_role = "staff".
Case list endpoint returns { items, pagination }.
Case workflow updates use command-style PATCH endpoints.
CORS must allow the frontend origin.
```

---

## 23. Current Integration Status

Current backend integration readiness:

* API has login endpoint
* API has JWT-protected routes
* API has role-based authorization
* API has CORS configured
* API supports frontend requests with `Authorization` header
* API is deployable behind Nginx/Gunicorn/systemd
* API has documentation for endpoints and deployment

Frontend is not implemented yet.

This document defines the contract for the future frontend implementation.
