# Client Intake & Case Tracking API

A production-minded full-stack case operations platform for managing clients, cases, team assignments, workflow transitions, and audit history.

The backend is built with Flask, SQLAlchemy and PostgreSQL and is deployed on a self-hosted Ubuntu server behind Gunicorn and Nginx. A React/Vite
frontend consumes the API using JWT authentication and role-based access control.

The project is currently evolving from a working full-stack MVP toward a production-ready platform, with security hardening, observability,
reliability, containerization and system-design work tracked publicly.

---

## Architecture

Browser
│
▼
React + Vite
│
│ HTTP + JWT
▼
Cloudflare Tunnel
│
▼
Nginx
│
▼
Gunicorn
│
▼
Flask API
│
▼
PostgreSQL

## Project Status

Current status:

**Backend core deployed, connected to the frontend and available through a temporary Cloudflare Quick Tunnel**

| Component | Status |

| Backend API | ✅ Working |
| PostgreSQL | ✅ Working |
| Automated tests | ✅ Working |
| React frontend | ✅ Integrated |
| Linux deployment | ✅ Self-hosted |
| Nginx/Gunicorn | ✅ Working |
| Public access | 🧪 Temporary Cloudflare Tunnel |
| Production hardening | 🚧 In progress |
| Redis/cache | 📋 Planned |
| Docker | 📋 Planned |
| Public API docs | 📋 Planned |

---
## Front-End Screenshots

1. Login Page 
![Alt text](https://res.cloudinary.com/smivyk2c/image/upload/v1791830237/Screenshot_2026-10-12_133056.png "Login Page")

2. Dashboard Page 
![Alt text](https://res.cloudinary.com/smivyk2c/image/upload/v1791830681/Screenshot_2026-10-12_134340.png "Dashboard Page")

3. Users Page 
![Alt text](https://res.cloudinary.com/smivyk2c/image/upload/v1791830681/Screenshot_2026-10-12_134424.png "Users Page")

## Tech Stack

### Backend

- Python
- Flask
- SQLAlchemy
- Flask-JWT-Extended
- Flask-Bcrypt
- Flask-Migrate / Alembic
- Flask-CORS

### Data

- PostgreSQL — development/deployed relational database
- SQLite — isolated in-memory testing

### Frontend

- React
- Vite
- React Router

### Testing

- Pytest

### Deployment

- Ubuntu Server
- Gunicorn
- systemd
- Nginx
- Cloudflare Tunnel

---

## Core Domain

The API currently models the following main entities:

### Users

Users represent team members who interact with the system.

Current user features:

- Create users
- Store hashed passwords
- Login with email and password
- JWT-based authentication
- Active/inactive user state
- Role-based permissions

Current roles:

- `admin`
- `staff`

Admin users can perform restricted actions such as managing users and soft deleting cases.

---

### Clients

Clients represent people receiving services.

Current client features:

- Create clients
- List clients
- Retrieve a client by ID
- Update client information
- Validate required client fields
- Prevent duplicate client emails

---

### Cases

Cases represent the main workflow object in the system.

Current case features:

- Create cases
- Assign users to cases
- Link cases to clients
- List cases
- Retrieve case by ID
- Filter cases
- Paginate case results
- Update case stage
- Update case status
- Update case type
- Update assigned users
- Reassign client
- Soft delete cases
- Track `updated_by`, `deleted_by`, and `deleted_at`

---

### Audit Logs

Audit logs track important case changes.

Current audit log behavior:

- Stage changes create audit logs
- Status changes create audit logs
- Type changes create audit logs
- Assigned user changes create audit logs
- Client reassignment creates audit logs
- Soft delete creates audit logs
- Audit logs store the authenticated user from the JWT token
- Failed actions do not create audit logs

---

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
│   ├── services/
|   └── docs/
│    └── manual-auth-test-checklist.md
│    └── api-endpoints.md
│    └── deployment-plan.md
│    └── development.md
│    └── frontend-integration.md
│    └── public-access-diagnosis.md
│    └── server-security-checklist.md
│    └── api-testing-checklist.md
│    └── authorization-matrix.md
├── migrations/
│   ├── versions/
│   ├── alembic.ini
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── conftest.py
│   ├── smoke_test.py  
│   └── test_*.py
├── .env.example
├── requirements.txt
├── run.py
├── gunicorn.conf.py
├── LICENSE
└── README.md
```

## Architecture document

Read the [architecture document](docs/architecture/system-architecture.md) for more information

---

## Current Backend Strengths

This project includes several backend concepts used in real systems:

- Application factory pattern
- Environment-based configuration
- Password hashing
- JWT authentication
- Role-based authorization
- Protected routes
- Soft delete instead of destructive deletes
- Audit logging
- Workflow validation
- Pagination
- Filtering
- Database migrations
- Automated integration testing
- Manual QA checklist
- Deployment with Gunicorn and Nginx

---

## Data safety

- The current public/demo environment uses fake/test data only.
- Real client data will not be introduced until the production security,
- backup, monitoring and access-control baseline is completed.

## Roadmap

Development is tracked through the GitHub Production Roadmap.

Current engineering phases:

- M0 — Governance & Architecture Baseline
- M1 — Secure & Observable Foundation
- M2 — Reliability, Redis & Performance
- M3 — Containerization & Infrastructure
- M4 — Operations Product Expansion
- M5 — Business Workflow Modules
- M6 — Production Readiness & Public API

---

## Purpose of This Project

This project serves three purposes:

1. Build a production-minded operations platform that could eventually
   support real client workflows.

2. Practice backend and systems engineering through real problems:
   security, reliability, observability, concurrency, caching,
   deployment and system design.

3. Maintain a documented engineering project that can be discussed
   transparently in technical interviews.
