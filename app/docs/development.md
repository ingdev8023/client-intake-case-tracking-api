# Developer Setup Guide

This guide explains how to set up, run, test, and maintain the Client Intake & Case Tracking API in a local development environment.

---

## Requirements

Before starting, make sure you have:

* Python 3.10+
* Git
* pip
* A terminal or PowerShell
* SQLite
* Optional: Postman or Insomnia for API testing

---

## 1. Clone the Repository

```bash
git clone <repository-url>
cd client-intake-case-tracking-api
```

---

## 2. Create a Virtual Environment

Create a local Python virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows PowerShell

```bash
.\.venv\Scripts\Activate.ps1
```

### Windows CMD

```bash
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
source .venv/bin/activate
```

After activation, your terminal should show something like:

```text
(.venv)
```

---

## 3. Install Dependencies

Install project dependencies:

```bash
pip install -r requirements.txt
```

After installing new packages during development, update `requirements.txt` with:

```bash
pip freeze > requirements.txt
```

---

## 4. Environment Variables

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=sqlite:///app.db
JWT_SECRET_KEY=your-development-secret-key
```

The project uses `python-dotenv` to load environment variables.

Important:

* Commit `.env.example`
* Do not commit `.env`
* Keep real secrets out of Git

---

## 5. Database Setup

This project uses Flask-Migrate and Alembic for database migrations.

### First-time setup

If the `migrations/` folder already exists, do not run `flask db init` again.

To create or update your local development database, run:

```bash
flask db upgrade
```

This applies all migration files to the database.

---

## 6. Creating New Migrations

When you change a SQLAlchemy model, create a new migration:

```bash
flask db migrate -m "Describe the model change"
```

Then apply it:

```bash
flask db upgrade
```

Example:

```bash
flask db migrate -m "Add billing table"
flask db upgrade
```

---

## 7. Migration Workflow

The normal workflow for database model changes is:

```text
1. Update SQLAlchemy models
2. Run flask db migrate -m "Description"
3. Review the generated migration file
4. Run flask db upgrade
5. Run tests
6. Commit model changes and migration file together
```

Do not rely on `db.create_all()` for the development database.

`db.create_all()` is only used in tests because the test database is temporary and in-memory.

---

## 8. Running the Application

Run the app locally:

```bash
python run.py
```

The API should be available at:

```text
http://127.0.0.1:5000
```

---

## 9. Running Tests

This project uses pytest.

Run all tests:

```bash
python -m pytest tests
```

Run tests with verbose output:

```bash
python -m pytest tests -v
```

Run a specific test file:

```bash
python -m pytest tests/test_auth.py -v
```

Run a specific test function:

```bash
python -m pytest tests/test_auth.py::test_valid_login_returns_token -v
```

---

## 10. Test Environment

The test suite uses:

* A separate Flask test app
* An in-memory SQLite database
* Pytest fixtures
* Test users
* JWT token fixtures
* Flask test client

The test database is not the same as the development database.

This means tests do not depend on existing local data.

Each test should create the users, clients, cases, and logs it needs.

---

## 11. Common Test Fixtures

The test suite may include fixtures such as:

```text
app
client
admin_user
staff_user
inactive_user
admin_token
staff_token
new_client
new_case
```

These fixtures help create predictable test data.

Example usage:

```python
def test_admin_can_access_users(client, admin_token):
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
```

---

## 12. Manual API Testing

You can use Postman, Insomnia, or curl.

Most routes require a JWT token.

Basic flow:

```text
1. Create or use an existing admin user
2. Log in using POST /login
3. Copy the access_token
4. Add this header to protected requests:
   Authorization: Bearer <access_token>
```

Example protected request:

```http
GET /cases
Authorization: Bearer <access_token>
```

---

## 13. Authentication Flow

The API uses JWT authentication.

Login endpoint:

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

The response includes:

```json
{
  "access_token": "<jwt_token>"
}
```

Protected endpoints require:

```http
Authorization: Bearer <jwt_token>
```

---

## 14. User Roles

Current roles:

```text
admin
staff
```

Admin users can perform restricted actions such as:

* Create users
* View users
* Activate users
* Deactivate users
* Soft delete cases

Staff users can perform regular case workflow actions but cannot perform admin-only actions.

---

## 15. Project Structure

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
│   ├── api-endpoints.md
│   ├── development.md
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

## 16. Development Rules

Recommended rules for this project:

### Keep secrets out of Git

Never commit:

```text
.env
instance/app.db
local database files
```

### Use migrations for schema changes

Do not manually recreate the development database unless intentionally resetting local data.

### Keep tests isolated

Tests should create their own data using fixtures.

Do not make tests depend on your local development database.

### Avoid plaintext passwords

Passwords must be hashed with bcrypt before being stored.

### Do not trust client input

Backend services should validate:

* Required fields
* User role
* User active state
* Case existence
* Client existence
* Valid workflow transitions
* Valid assigned users

---

## 17. Useful Commands

### Activate virtual environment

```bash
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Update requirements

```bash
pip freeze > requirements.txt
```

### Run app

```bash
python run.py
```

### Run migrations

```bash
flask db migrate -m "Migration message"
flask db upgrade
```

### Run tests

```bash
python -m pytest tests -v
```

### Check Git status

```bash
git status
```

---

## 18. Troubleshooting

### PowerShell does not allow virtual environment activation

If PowerShell blocks activation, run:

```bash
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

Then activate again:

```bash
.\.venv\Scripts\Activate.ps1
```

---

### `ModuleNotFoundError: No module named 'app'`

Make sure you are running commands from the project root:

```text
client-intake-case-tracking-api/
```

Run tests with:

```bash
python -m pytest tests
```

Also confirm that `app/__init__.py` exists.

---

### `No changes in schema detected`

This means Alembic did not detect model changes.

Possible reasons:

* The current database already matches the models
* Models were not imported before migration
* No model changes were actually made

If models are not being detected, make sure they are imported during app startup.

---

### `Missing Authorization Header`

The route is protected and requires:

```http
Authorization: Bearer <access_token>
```

Log in first and send the token in the request header.

---

### `Signature verification failed`

This usually means the JWT token was generated with a different `JWT_SECRET_KEY`.

Log in again and use the new token.

---

## 19. Recommended Development Workflow

For a normal backend change:

```text
1. Create or select a GitHub issue
2. Create/update code
3. Add or update tests
4. Run pytest
5. If models changed, create a migration
6. Run flask db upgrade
7. Update docs if needed
8. Commit focused changes
9. Update the issue status
```

Example:

```bash
python -m pytest tests -v
flask db migrate -m "Add payment model"
flask db upgrade
git status
git add .
git commit -m "Add payment model and migration"
```

---

## 20. PostgreSQL Local Development

The app can run with PostgreSQL by changing `DATABASE_URL`.

Example:

env
DATABASE_URL=postgresql://username:password@localhost:5432/client_intake_dev


##21 ## Admin Bootstrap

Create the first admin user with:

```bash
flask create-admin

## 22. Current Local Development Notes


Deployment is also planned for a future iteration and will require:

* Production configuration
* Hosted database
* Environment variables
* WSGI server such as Gunicorn
* Cloud hosting provider
