# API Testing Checklist

## Purpose

Use this checklist after deploys, server restarts, tunnel restarts, or network changes to confirm the Client Intake & Case Tracking API is reachable and still protected.

This checklist covers:

* local Flask access
* server-local Nginx access
* LAN access
* authentication and authorization
* CORS behavior
* Cloudflare Tunnel access
* expected success and failure responses

Do not paste real passwords, JWTs, tunnel credentials, or `.env` values into this document. Use placeholders such as `<admin_email>`, `<admin_password>`, `<access_token>`, `<server_lan_ip>`, and `<active_tunnel_hostname>`.

---

## Access Paths

Test every access path that applies to the current environment.

| Access path | Base URL | Purpose |
| --- | --- | --- |
| Local Flask dev server | `http://127.0.0.1:5001` | Local development with `python run.py` |
| Server-local Nginx | `http://127.0.0.1` | Confirms Nginx proxies to Gunicorn on the server |
| Server-local Gunicorn | `http://127.0.0.1:8000` | Server-only diagnosis, not a public API URL |
| LAN | `http://<server_lan_ip>` | Confirms another device on the same network can reach Nginx |
| Cloudflare Tunnel | `https://<active_tunnel_hostname>` | Confirms public access through the active tunnel |
| Direct public IP | `http://<direct_public_ip>` | Diagnostic only; expected to fail unless router/ISP setup allows it |

Notes:

* `run.py` starts the Flask development server on port `5001`.
* The deployed server should expose Nginx on port `80`.
* Gunicorn should remain private on `127.0.0.1:8000`.
* PostgreSQL, `.env`, JWT secrets, tunnel credentials, and SSH are not part of public API testing.

---

## Before Testing

Complete these checks after every deploy or server restart:

* The API process is running.
* Nginx is running.
* Gunicorn is running on `127.0.0.1:8000` when testing the server deployment.
* Database migrations have been applied with `flask db upgrade`.
* Required environment variables are present on the server.
* `cloudflared` is running when testing tunnel access.
* The current LAN IP and tunnel hostname are known.
* At least one active admin user exists.
* `CORS_ORIGINS` includes only approved frontend origins.

If an admin user is needed, create one interactively:

```bash
flask create-admin
```

Do not record the admin password in this file, in issue comments, or in commit history.

---

## Test Variables

Set the base URL for the access path being tested.

```bash
BASE_URL="http://127.0.0.1:5001"
```

Examples:

```bash
BASE_URL="http://<server_lan_ip>"
BASE_URL="https://<active_tunnel_hostname>"
```

PowerShell:

```powershell
$BASE_URL = "http://127.0.0.1:5001"
```

Use `curl.exe` in PowerShell if `curl` resolves to `Invoke-WebRequest`.

---

## 1. Local And Nginx Health Tests

### 1.1 Local Flask health

Run while `python run.py` is active.

```bash
curl -i "http://127.0.0.1:5001/health"
```

Expected successful response:

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{"message":"API running"}
```

### 1.2 Gunicorn health on server

Run on the server only.

```bash
curl -i "http://127.0.0.1:8000/health"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
{"message":"API running"}
```

Failure response to investigate:

```text
Connection refused, timeout, or non-200 status
```

Likely causes:

* Gunicorn is not running.
* Gunicorn is listening on the wrong host or port.
* The app failed during startup.

### 1.3 Nginx health on server

Run on the server.

```bash
curl -i "http://127.0.0.1/health"
```

Expected successful response:

```http
HTTP/1.1 200 OK
Server: nginx
```

```json
{"message":"API running"}
```

Failure response to investigate:

```text
502 Bad Gateway, 504 Gateway Timeout, connection refused, or non-200 status
```

Likely causes:

* Nginx is not running.
* Nginx cannot reach Gunicorn.
* The proxy target is not `127.0.0.1:8000`.

---

## 2. LAN Tests

Run these from a second device connected to the same WiFi/LAN.

### 2.1 LAN health

```bash
curl -i "http://<server_lan_ip>/health"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
{"message":"API running"}
```

Expected failure responses:

```text
Connection refused
Connection timed out
Could not resolve host
```

Pass criteria:

* The second device reaches Nginx through the server LAN IP.
* The test is not using mobile data.
* Testers do not use Gunicorn port `8000` as the LAN API base URL.

### 2.2 LAN protected route without token

```bash
curl -i "http://<server_lan_ip>/cases"
```

Expected failure response:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
```

```json
{"msg":"Missing Authorization Header"}
```

Pass criteria:

* LAN access reaches the API.
* Protected records are not returned without a JWT.

---

## 3. Tunnel Tests

Run these from outside the LAN, such as a phone on mobile data.

### 3.1 Tunnel health

```bash
curl -i "https://<active_tunnel_hostname>/health"
```

Expected successful response:

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{"message":"API running"}
```

Expected failure responses:

```text
404 from tunnel provider
502 Bad Gateway
Connection timed out
Tunnel hostname not found
```

Likely causes:

* The tunnel is not running.
* The temporary tunnel hostname changed.
* The tunnel routes to the wrong local service.
* Nginx or Gunicorn is down behind the tunnel.

### 3.2 Tunnel protected route without token

```bash
curl -i "https://<active_tunnel_hostname>/cases"
```

Expected failure response:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
```

```json
{"msg":"Missing Authorization Header"}
```

Pass criteria:

* The tunnel exposes the API path.
* The tunnel does not bypass JWT authentication.

### 3.3 Tunnel login

```bash
curl -i -X POST "https://<active_tunnel_hostname>/login" \
  -H "Content-Type: application/json" \
  -d '{"user_email":"<admin_email>","user_password":"<admin_password>"}'
```

Expected successful response:

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "access_token": "<access_token>",
  "user": {
    "user_id": 1,
    "user_name": "Admin User",
    "user_email": "<admin_email>",
    "user_role": "admin",
    "is_active": true
  }
}
```

Security note:

* The token shown above is a placeholder.
* Do not paste a real token into documentation, screenshots, issue comments, or commit messages.

---

## 4. Authentication Tests

Run these against each full-use base URL: local Flask, LAN, Nginx, and tunnel.

### 4.1 Valid login

```bash
curl -i -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"user_email":"<admin_email>","user_password":"<admin_password>"}'
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
{
  "access_token": "<access_token>",
  "user": {
    "user_role": "admin",
    "is_active": true
  }
}
```

Save the returned token only in your local terminal session:

```bash
TOKEN="<access_token>"
```

PowerShell:

```powershell
$TOKEN = "<access_token>"
```

### 4.2 Invalid login

```bash
curl -i -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"user_email":"<admin_email>","user_password":"<wrong_password>"}'
```

Expected failure response:

```http
HTTP/1.1 401 Unauthorized
```

Example response:

```json
{"msg":"Wrong password"}
```

Pass criteria:

* No `access_token` is returned.
* The failure does not reveal stored password data.

### 4.3 Current user with valid token

```bash
curl -i "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
{
  "user_id": 1,
  "user_name": "Admin User",
  "user_email": "<admin_email>",
  "user_role": "admin",
  "is_active": true
}
```

Pass criteria:

* The response identifies the token user.
* The response does not include `user_password`.

### 4.4 Current user with invalid token

```bash
curl -i "$BASE_URL/auth/me" \
  -H "Authorization: Bearer invalid-token"
```

Expected failure response:

```http
HTTP/1.1 401 Unauthorized
```

or:

```http
HTTP/1.1 422 Unprocessable Entity
```

Pass criteria:

* Protected user data is not returned.

---

## 5. Protected Endpoint Tests

Run these after setting `TOKEN` to a valid admin JWT in the local terminal session.

### 5.1 Cases without token

```bash
curl -i "$BASE_URL/cases"
```

Expected failure response:

```http
HTTP/1.1 401 Unauthorized
```

```json
{"msg":"Missing Authorization Header"}
```

### 5.2 Cases with token

```bash
curl -i "$BASE_URL/cases?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

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

### 5.3 Clients with token

```bash
curl -i "$BASE_URL/clients" \
  -H "Authorization: Bearer $TOKEN"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
[]
```

The list may contain records in a seeded or existing database.

### 5.4 Users with admin token

```bash
curl -i "$BASE_URL/users" \
  -H "Authorization: Bearer $TOKEN"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
[
  {
    "user_id": 1,
    "user_name": "Admin User",
    "user_email": "<admin_email>",
    "user_role": "admin",
    "is_active": true
  }
]
```

Expected failure response with a non-admin token:

```http
HTTP/1.1 403 Forbidden
```

```json
{"error":"User not authorized"}
```

---

## 6. Write Smoke Tests

Run this section only against a development or staging database where test data is allowed.

### 6.1 Create client

```bash
curl -i -X POST "$BASE_URL/clients" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_first_name":"Access","client_lastname":"Tester","client_phone":"555-0100","client_email":"access.tester@example.com","client_address":"Test Address","client_date_of_birth":"1990-01-01"}'
```

Expected successful response:

```http
HTTP/1.1 201 Created
```

```json
{
  "client_id": 1,
  "client_first_name": "Access",
  "client_lastname": "Tester",
  "client_email": "access.tester@example.com"
}
```

Save the returned ID only in your terminal session:

```bash
CLIENT_ID="<client_id>"
```

### 6.2 Create case

```bash
curl -i -X POST "$BASE_URL/cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"case_type":"VAWA","case_status":"open","case_stage":"intake","client_id":'"$CLIENT_ID"'}'
```

Expected successful response:

```http
HTTP/1.1 201 Created
```

```json
{
  "case_id": 1,
  "case_type": "VAWA",
  "case_status": "open",
  "case_stage": "intake",
  "client_id": 1
}
```

Save the returned ID only in your terminal session:

```bash
CASE_ID="<case_id>"
```

### 6.3 Valid stage update

```bash
curl -i -X PATCH "$BASE_URL/cases/$CASE_ID/stage" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"case_stage":"document_collection"}'
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
{
  "case_id": 1,
  "case_stage": "document_collection",
  "updated_by": 1
}
```

### 6.4 Invalid stage update

```bash
curl -i -X PATCH "$BASE_URL/cases/$CASE_ID/stage" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"case_stage":"submitted"}'
```

Expected failure response:

```http
HTTP/1.1 400 Bad Request
```

```json
{"error":"Invalid stage transition"}
```

Pass criteria:

* The invalid transition does not change the case.
* The invalid transition does not create an audit log.

### 6.5 Audit log check

```bash
curl -i "$BASE_URL/logs/$CASE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Expected successful response:

```http
HTTP/1.1 200 OK
```

```json
[
  {
    "case_id": 1,
    "user_id": 1,
    "action": "CASE_STAGE_CHANGED",
    "old_value": "intake",
    "new_value": "document_collection"
  }
]
```

---

## 7. CORS Tests

Run these when a browser frontend calls the API.

### 7.1 Approved origin preflight

```bash
curl -i -X OPTIONS "$BASE_URL/cases" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization, Content-Type"
```

Expected successful response:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Headers: Authorization, Content-Type
```

Pass criteria:

* The approved origin is present in `CORS_ORIGINS`.
* The `Authorization` header is allowed.
* The requested method is allowed.

### 7.2 Unapproved origin preflight

```bash
curl -i -X OPTIONS "$BASE_URL/cases" \
  -H "Origin: http://evil-site.example" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization, Content-Type"
```

Expected failure behavior:

```text
No Access-Control-Allow-Origin header for the unapproved origin
```

Pass criteria:

* `CORS_ORIGINS` is explicit.
* `CORS_ORIGINS=*` is not used for protected production APIs.

---

## 8. Restart And Deploy Verification

Run this compact sequence after every deploy, server restart, service restart, or tunnel restart.

### 8.1 Server restart sequence

On the server:

```bash
curl -i "http://127.0.0.1:8000/health"
curl -i "http://127.0.0.1/health"
curl -i "http://127.0.0.1/cases"
```

Expected:

* Gunicorn health returns `200 OK`.
* Nginx health returns `200 OK`.
* `/cases` without token returns `401 Unauthorized`.

### 8.2 LAN restart sequence

From a LAN device:

```bash
curl -i "http://<server_lan_ip>/health"
curl -i "http://<server_lan_ip>/cases"
```

Expected:

* `/health` returns `200 OK`.
* `/cases` without token returns `401 Unauthorized`.

### 8.3 Tunnel restart sequence

From outside the LAN:

```bash
curl -i "https://<active_tunnel_hostname>/health"
curl -i "https://<active_tunnel_hostname>/cases"
```

Expected:

* `/health` returns `200 OK`.
* `/cases` without token returns `401 Unauthorized`.

Pass criteria:

* The API comes back after restart.
* Nginx still routes to Gunicorn.
* The LAN URL still points to the server.
* The active tunnel hostname still routes to Nginx.
* Authentication remains enforced after restart.

---

## 9. Security Checks

Confirm these before treating LAN or tunnel access as acceptable:

* `/health` may be public.
* `/cases`, `/clients`, `/users`, `/logs/<case_id>`, and `/auth/me` require JWT authentication.
* Admin-only endpoints still require an admin token.
* Staff users cannot soft delete cases.
* Missing or invalid JWTs do not return protected records.
* Gunicorn is not exposed as the public API URL.
* PostgreSQL is not exposed publicly.
* SSH is not exposed publicly unless intentionally hardened and approved.
* `.env` is not committed.
* Real JWTs, passwords, and tunnel credentials are not added to docs, logs, issues, or commits.

---

## 10. Results Template

Use this template in issue comments or deploy notes. Keep secrets out of the notes.

```text
API testing checklist run
Date:
Tester:
Environment:
Commit:

Base URLs tested:
- Local Flask:
- Server-local Nginx:
- LAN:
- Tunnel:

Reachability:
- Local /health:
- Gunicorn /health:
- Nginx /health:
- LAN /health:
- Tunnel /health:

Auth:
- /login valid credentials:
- /login invalid credentials:
- /auth/me valid token:
- /auth/me invalid token:
- /cases without token:
- /cases with token:
- /users admin-only:

CORS:
- Approved origin preflight:
- Unapproved origin preflight:

Restart/deploy:
- Server restart checks:
- LAN checks:
- Tunnel checks:

Security:
- No secrets or tokens recorded:
- Gunicorn private:
- PostgreSQL private:
- Tunnel does not bypass auth:

Result:
- PASS / FAIL

Notes:
```

---

## 11. Final Pass Criteria

This checklist passes when:

* `docs/api-testing-checklist.md` exists.
* Local, LAN, Nginx, auth, CORS, and tunnel tests are all represented.
* Health endpoints return the expected successful JSON response.
* Authenticated API calls return expected successful responses.
* Missing-token, invalid-token, invalid-login, CORS, LAN, Nginx, and tunnel failures have expected failure responses.
* No real secrets, passwords, JWTs, or tunnel credentials are stored in the documentation.
* The restart and deploy verification section can be followed after deploys or server restarts.
