# Client Intake & Case Tracking API

A backend API for managing client intake, case tracking, user assignments, workflow stages, audit logs, and role-based access control.

This project is designed as a real-world backend system inspired by legal operations and immigration case management workflows. The goal is to model how a team can create clients, open cases, assign users, move cases through workflow stages, track changes, and protect sensitive actions through authentication and authorization.

---

## Project Status

Current status: **Backend core implemented and tested**

The project currently includes:

* Flask application factory structure
* SQLAlchemy models and relationships
* PostgreSQL development database
* SQLite test database
* Flask-Migrate / Alembic migrations
* JWT authentication
* Bcrypt password hashing
* Role-based authorization
* Soft delete for cases
* Audit log tracking
* Case filtering and pagination
* Manual auth test checklist
* Pytest automated test setup
* Integration tests for auth, protected routes, roles, soft delete, workflow rules, and audit logs

---

## Tech Stack

* Python
* Flask
* Flask-SQLAlchemy
* SQLAlchemy
* SQLite
* Flask-Migrate / Alembic
* Flask-Bcrypt
* Flask-JWT-Extended
* Pytest
* python-dotenv

---

## Core Domain

The API currently models the following main entities:

### Users

Users represent team members who interact with the system.

Current user features:

* Create users
* Store hashed passwords
* Login with email and password
* JWT-based authentication
* Active/inactive user state
* Role-based permissions

Current roles:

* `admin`
* `staff`

Admin users can perform restricted actions such as managing users and soft deleting cases.

---

### Clients

Clients represent people receiving services.

Current client features:

* Create clients
* List clients
* Retrieve a client by ID
* Update client information
* Validate required client fields
* Prevent duplicate client emails

---

### Cases

Cases represent the main workflow object in the system.

Current case features:

* Create cases
* Assign users to cases
* Link cases to clients
* List cases
* Retrieve case by ID
* Filter cases
* Paginate case results
* Update case stage
* Update case status
* Update case type
* Update assigned users
* Reassign client
* Soft delete cases
* Track `updated_by`, `deleted_by`, and `deleted_at`

---

### Audit Logs

Audit logs track important case changes.

Current audit log behavior:

* Stage changes create audit logs
* Status changes create audit logs
* Type changes create audit logs
* Assigned user changes create audit logs
* Client reassignment creates audit logs
* Soft delete creates audit logs
* Audit logs store the authenticated user from the JWT token
* Failed actions do not create audit logs

---

## Authentication

The API uses JWT authentication.

Users log in with email and password. If the credentials are valid, the API returns an access token.

### Login

```http
POST /login
```

Example request:

```json
{
  "user_email": "admin@test.com",
  "user_password": "Password123!"
}
```

Example response:

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

Protected routes require the token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

---

## Authorization

The API protects routes using JWT and role checks.

### Admin permissions

Admin users can:

* View users
* Create users
* Activate users
* Deactivate users
* Soft delete cases
* Access protected system operations

### Staff permissions

Staff users can:

* View protected resources
* Update case workflow fields
* Update case status
* Update assigned users
* Trigger audit-logged case actions

Staff users cannot perform admin-only actions such as soft deleting cases.

---

## Case Workflow

Cases move through controlled workflow stages.

Current stages:

```text
intake
document_collection
review
edits
pending_submission
submitted
closed
```

Stage transitions are validated by the backend.

Example valid transition:

```text
intake → document_collection
```

Example invalid transition:

```text
intake → submitted
```

Invalid transitions return an error and do not modify the case or create audit logs.

---

## Main API Endpoints

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

## Case Filtering and Pagination

The `GET /cases` endpoint supports filters and pagination.

Example:

```http
GET /cases?page=1&limit=10
```

Example with filters:

```http
GET /cases?case_status=open&case_stage=intake&page=1&limit=10
```

Supported filters include:

```text
case_status
case_stage
case_type
client_id
created_after
created_before
page
limit
```

Example paginated response:

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

---

## Environment Variables

Create a `.env` file in the project root.

Example:

```env
# SQLite local development
DATABASE_URL=sqlite:///app.db

# PostgreSQL local development example
DATABASE_URL=postgresql://username:password@localhost:5432/client_intake_dev

JWT_SECRET_KEY=your-secret-key
```

A `.env.example` file should be committed to the repository, but the real `.env` file should stay ignored by Git.

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd client-intake-case-tracking-api
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment.

On Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Database Migrations

This project uses Flask-Migrate and Alembic for database migrations.

Initialize migrations only once when setting up migrations for the first time:

```bash
flask db init
```

Create a migration after model changes:

```bash
flask db migrate -m "Describe migration"
```

Apply migrations:

```bash
flask db upgrade
```

Current migration status:

* Initial migration created
* Tables generated through Alembic
* Development database can be created using `flask db upgrade`

Important:

For the real development database, use migrations instead of `db.create_all()`.

`db.create_all()` is still used in tests because the test database is temporary and in-memory.

---

## Running the Application

Run the Flask application:

```bash
python run.py
```

The API should be available locally at:

```text
http://127.0.0.1:5001
```

---

## Running Tests

This project uses pytest.

Run all tests:

```bash
python -m pytest tests
```

Run tests with verbose output:

```bash
python -m pytest tests -v
```

The test suite uses:

* A separate Flask test app
* An in-memory SQLite database
* Test users and fixtures
* JWT token fixtures
* Integration tests against real API routes

Current test coverage includes:

* App testing configuration
* Protected routes without token
* Invalid token behavior
* Valid login
* Inactive user login rejection
* Admin access
* Staff authorization restrictions
* Admin soft delete
* Case workflow updates
* Invalid stage transitions
* Audit log creation
* Audit log prevention on failed actions

---

## Manual Test Documentation

Manual authentication and authorization test cases are documented in:

```text
docs/manual-auth-test-checklist.md
```

This checklist covers:

* Missing token behavior
* Invalid token behavior
* Inactive user login
* Staff restricted actions
* Admin-only actions
* Audit log ownership

---

## Project Structure

```text
client-intake-case-tracking-api/
├── app/
│   ├── __init__.py
│   ├── config/
│   ├── extensions/
│   ├── models/
│   ├── routes/
│   └── services/
├── docs/
│   └── manual-auth-test-checklist.md
├── migrations/
│   ├── versions/
│   ├── alembic.ini
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

---

## Current Backend Strengths

This project includes several backend concepts used in real systems:

* Application factory pattern
* Environment-based configuration
* Password hashing
* JWT authentication
* Role-based authorization
* Protected routes
* Soft delete instead of destructive deletes
* Audit logging
* Workflow validation
* Pagination
* Filtering
* Database migrations
* Automated integration testing
* Manual QA checklist

---

## Roadmap

Planned future improvements:

### Backend Hardening

* Improve reusable permission helpers
* Add more automated tests
* Add API endpoint documentation
* Add developer setup guide
* Improve error response consistency
* Add request validation helpers

### Database

* Expand migrations as models evolve

### Product Features

* Notes section
* Tasks section
* Document tracking
* Billing section
* Payment service integration
* Metrics and dashboard endpoints
* CSV export endpoints

### Deployment

* Add production configuration
* Add Gunicorn
* Add deployment guide
* Deploy API to a cloud platform
* Configure hosted PostgreSQL database

### Frontend

* Build frontend client
* Connect frontend to backend API
* Implement login flow
* Store and send JWT token
* Display role-based UI
* Build case management views

---

## Purpose of This Project

This project is part of a backend engineering portfolio focused on building a realistic, secure, and maintainable API.

The system is designed to demonstrate:

* Backend architecture
* REST API design
* Authentication and authorization
* Database modeling
* Business workflow validation
* Auditability
* Testing discipline
* Migration-based database management

The goal is not only to build endpoints, but to build a backend that behaves like a real operational system.
