# Client Intake & Case Tracking API

A backend system designed to manage client intake, case lifecycle, and operational workflows.  
This project simulates a real-world CRM-like system inspired by legal/immigration case management platforms.

---

## 🚀 Overview

This API allows:

- Creating and managing client cases
- Tracking case status across a defined workflow
- Filtering and querying cases
- Exporting data for operational analysis
- Monitoring backlog and metrics

The goal of this project is to practice **real-world backend engineering concepts**, including structured architecture, database design, and business rule enforcement.

---

## 🧠 Features (V1)

- Health check endpoint (`/health`)
- Modular API structure using Flask Blueprints
- Case management endpoints (in progress)
- Structured project architecture (routes, services, models)
- Ready for database integration (SQLAlchemy)

---

## 🏗️ Project Structure

project/
│
├── app/
│ ├── routes/ # API endpoints (Blueprints)
│ ├── services/ # Business logic
│ ├── models/ # Database models
│ ├── init.py # App factory
│
├── run.py # Entry point
├── requirements.txt
└── README.md

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd client-intake-case-tracking

python -m venv .venv
source venv/bin/activate
pip install -r requirements.txt


Running the Server

python run.py

Server will run at:

http://127.0.0.1:5000

Available Endpoints

Health Check
GET /health

Response:

{
  "message": "API running"
}

Roadmap
V1
 Project structure setup
 Flask app factory + Blueprints
 Case CRUD endpoints
 PostgreSQL database integration
 Status workflow validation
V2
 JWT Authentication
 Role-based access control
 Pagination & filtering
 CSV export endpoint
 Metrics & analytics endpoints
V3
 Docker setup
 Deployment (Render/Railway)
 Audit logs (status changes)
 File/document uploads

🧠 Learning Goals

This project focuses on:

Backend architecture design
REST API best practices
Database modeling & relationships
Business logic separation (services layer)
Real-world workflow constraints


📌 Author

Daniel Jaimes
Backend Developer in progress | Former Operations Manager
Focused on building real-world backend systems

⚠️ Notes

This project is actively under development as part of a learning journey into backend engineering.
Expect frequent updates and improvements.

---

