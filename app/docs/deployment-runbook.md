# Deployment Runbook — Client Intake & Case Tracking API

This document describes the current deployment architecture for the Client Intake & Case Tracking API.

The project is deployed on a self-managed Linux server instead of a managed platform such as Render, Railway, Fly.io, or PythonAnywhere.

---

## Current architecture

The architecture is:


Internet
   ↓
Cloudflared Tunnel
   ↓
Nginx
   ↓
Gunicorn
   ↓
Flask API
   ↓
PostgreSQL


The Flask development server will not be used in production.

---

### Service Management Commands

Reload systemd after editing the service file:

```bash
sudo systemctl daemon-reload
```

Start the service:

```bash
sudo systemctl start client-intake-api.service
```

Stop the service:

```bash
sudo systemctl stop client-intake-api.service
```

Restart the service:

```bash
sudo systemctl restart client-intake-api.service
```

Check service status:

```bash
sudo systemctl status client-intake-api.service
```

Enable the service to start automatically after reboot:

```bash
sudo systemctl enable client-intake-api.service
```

View live logs:

```bash
sudo journalctl -u client-intake-api.service -f
```

View recent logs:

```bash
sudo journalctl -u client-intake-api.service -n 50
```

---

### Validation

The service was validated with:

```bash
curl http://127.0.0.1/health
```

Expected response:

```json
{"message":"API running"}
```

Protected route validation:

```bash
curl http://127.0.0.1/cases
```

Expected response:

```json
{"msg":"Missing Authorization Header"}
```

---

## Database Migrations

The project uses Flask-Migrate and Alembic.

Migrations should be applied on the server with:

```bash
flask db upgrade
```

When models change, the development workflow is:

```bash
flask db migrate -m "Describe migration"
flask db upgrade
```

Migration files must be committed to Git and pulled on the server before running:

```bash
flask db upgrade
```

The server database should not be created with `db.create_all()`.

---

## Required Production Environment Variables

The server must have a `.env` file or equivalent environment variable configuration.

Required variables:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
JWT_SECRET_KEY=secure-production-secret
```

---

## CORS Configuration

The API uses Flask-CORS to allow browser-based frontend applications to call the backend from approved origins.

Allowed origins are controlled with:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```
---

## Health Check

The API includes a health endpoint:

```http
GET /health
```

Expected response:

```json
{
  "message": "API running"
}
```

This endpoint can be used to verify that the API is running after deployment.

---

## Known Current Limitations

The deployment is not complete yet.

Current limitations:

* No HTTPS yet
* No domain configured yet
* No production CORS configuration yet
* No Docker deployment yet


---

