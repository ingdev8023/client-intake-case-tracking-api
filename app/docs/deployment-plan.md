# Deployment Plan — Client Intake & Case Tracking API

This document describes the planned deployment architecture for the Client Intake & Case Tracking API.

The project will be deployed on a self-managed Linux server instead of a managed platform such as Render, Railway, Fly.io, or PythonAnywhere.

---

## Deployment Goal

Deploy the Flask backend API to a Linux server using a production-ready setup.

The target architecture is:

```text
Internet
   ↓
Nginx
   ↓
Gunicorn
   ↓
Flask API
   ↓
PostgreSQL
```

The Flask development server will not be used in production.

---

## Selected Deployment Option

### Chosen option

```text
Self-managed Linux server
```

The API will be deployed on a personal Linux server that is accessed through SSH.

### Why this option was selected

This option was selected because it provides hands-on experience with real backend deployment concepts:

* Linux server administration
* SSH-based remote management
* Virtual environments
* Environment variables
* PostgreSQL configuration
* Gunicorn WSGI server
* Nginx reverse proxy
* systemd services
* Server security hardening
* Future Docker deployment

This approach requires more manual setup than platforms like Render or Railway, but it provides stronger learning value and more control over the full deployment stack.

---

## Deployment Options Considered

### Render

Render is a managed cloud platform that can deploy web services and hosted PostgreSQL databases with less server configuration.

Pros:

* Easier setup
* Managed deployment flow
* Built-in environment variable management
* Hosted PostgreSQL available

Cons:

* Less hands-on server experience
* Less control over infrastructure
* Free/low-cost tiers may have limitations

---

### Railway

Railway provides simple app and database deployment with a developer-friendly interface.

Pros:

* Fast deployment
* Easy PostgreSQL provisioning
* GitHub integration
* Simple environment variable setup

Cons:

* Usage-based pricing can change
* Less direct Linux/server practice
* More platform abstraction

---

### Fly.io

Fly.io supports deploying applications close to users with more infrastructure control than some managed platforms.

Pros:

* More advanced deployment model
* Good for containerized apps
* Global deployment options

Cons:

* More complex than Render or Railway
* Docker knowledge is usually needed
* Higher learning curve

---

### PythonAnywhere

PythonAnywhere is useful for beginner-friendly Python web app hosting.

Pros:

* Python-focused
* Beginner-friendly
* Simple for small apps

Cons:

* Less flexible for production-like backend deployment
* Not ideal for learning full Linux server deployment
* Less aligned with future Docker/Nginx/systemd goals

---

### Self-managed Linux Server

Pros:

* Maximum learning value
* Full control over deployment
* Real Linux server experience
* Can configure Nginx, Gunicorn, PostgreSQL, Docker, and security manually
* Closest to understanding how production servers actually work

Cons:

* More responsibility
* More security concerns
* More manual troubleshooting
* Requires ongoing maintenance

Decision:

```text
Use the self-managed Linux server for this project.
```

---

## Current Deployment Status

The following deployment steps have already been completed or validated:

* Linux server access through SSH
* Project cloned on the server
* Python virtual environment created on the server
* Dependencies installed from `requirements.txt`
* PostgreSQL support added to the project
* Flask-Migrate migrations applied successfully
* Gunicorn installed
* `gunicorn.conf.py` added
* Gunicorn started successfully with `run:app`
* API responded through Gunicorn on `127.0.0.1:8000`
* Protected route returned JWT missing header response
* Health endpoint returned successful API response

Validated commands:

```bash
gunicorn -c gunicorn.conf.py run:app
```

Validated responses:

```bash
curl http://127.0.0.1:8000/cases
```

Expected:

```json
{"msg":"Missing Authorization Header"}
```

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"message":"API running"}
```

---

## Production Application Server

The production WSGI server for this project is Gunicorn.

Local development uses:

```bash
python run.py
```

Production-like execution uses:

```bash
gunicorn -c gunicorn.conf.py run:app
```

The value `run:app` means:

```text
run → run.py
app → Flask application object inside run.py
```

The `run.py` file must expose the Flask app:

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
```

---

## Gunicorn Configuration

The project includes a Gunicorn configuration file:

```text
gunicorn.conf.py
```

Current configuration:

```python
bind = "127.0.0.1:8000"
workers = 2
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

### Why bind to `127.0.0.1:8000`?

Gunicorn should not be directly exposed to the public internet.

It should listen only locally:

```text
127.0.0.1:8000
```

Later, Nginx will receive public traffic on ports `80` and `443` and forward requests internally to Gunicorn.

## systemd Service for Gunicorn

The API is managed on the Linux server using `systemd`.

Before this step, Gunicorn could run manually with:

```bash
gunicorn -c gunicorn.conf.py run:app
```

That confirmed the Flask app could run through Gunicorn, but the process stopped when the SSH session or terminal closed.

To make the API behave like a real server process, a `systemd` service was created.

---

### Service Name

The selected service name is:

```text
client-intake-api.service
```

The service file is located at:

```text
/etc/systemd/system/client-intake-api.service
```

---

### Service File

Current service configuration:

```ini
[Unit]
Description=Client Intake Case Tracking API
After=network.target

[Service]
User=djdev
Group=djdev
WorkingDirectory=/home/djdev/apps/client-intake-case-tracking-api
EnvironmentFile=/home/djdev/apps/client-intake-case-tracking-api/.env
ExecStart=/home/djdev/apps/client-intake-case-tracking-api/.venv/bin/gunicorn -c gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

---

### Important Configuration Notes

`User=djdev` and `Group=djdev` make the service run as the deployment user instead of root.

`WorkingDirectory` tells systemd where the project lives. This is important because Gunicorn must run from the project root where `run.py`, `gunicorn.conf.py`, and `.env` exist.

`EnvironmentFile` loads environment variables required by the API, such as `DATABASE_URL` and `JWT_SECRET_KEY`.

`ExecStart` starts Gunicorn directly from the project virtual environment. The virtual environment is not activated manually inside systemd. Instead, the service calls the Gunicorn binary directly from:

```text
/home/djdev/apps/client-intake-case-tracking-api/.venv/bin/gunicorn
```

`Restart=always` makes systemd restart the service if the API crashes.

`PrivateTmp=true` gives the service a private temporary directory, which is a small security improvement.

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
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"message":"API running"}
```

Protected route validation:

```bash
curl http://127.0.0.1:8000/cases
```

Expected response:

```json
{"msg":"Missing Authorization Header"}
```

This confirms:

* systemd starts Gunicorn successfully
* Gunicorn loads the Flask app through `run:app`
* The API responds on `127.0.0.1:8000`
* JWT protection still works through the systemd-managed process

---

### Current Deployment Status

At this stage, the API runs as a managed Linux service.

Completed:

* Gunicorn manual execution
* systemd service creation
* environment file loading
* service start/restart/status validation
* API health check through systemd-managed Gunicorn

Still pending:

* Nginx reverse proxy
* HTTPS
* domain configuration
* production CORS
* admin bootstrap command
* server hardening


---

## Planned Reverse Proxy

Nginx will be used as the reverse proxy.

Planned flow:

```text
Client browser or frontend
   ↓
https://api-domain.com
   ↓
Nginx
   ↓
http://127.0.0.1:8000
   ↓
Gunicorn
   ↓
Flask API
```

Nginx will eventually handle:

* Public HTTP traffic
* HTTPS/TLS certificates
* Reverse proxy to Gunicorn
* Request forwarding headers
* Basic request size limits
* Future frontend/backend domain separation

Nginx is not configured yet in this phase.

---

## Process Management

Gunicorn currently runs manually from the terminal.

Current command:

```bash
gunicorn -c gunicorn.conf.py run:app
```

This works for testing, but it stops when the terminal session closes.

The next planned step is to create a `systemd` service so the API can be managed as a Linux service.

Planned service commands:

```bash
sudo systemctl start client-intake-api
sudo systemctl stop client-intake-api
sudo systemctl restart client-intake-api
sudo systemctl status client-intake-api
```

The systemd service should:

* Start Gunicorn automatically
* Restart the API if it crashes
* Run the app from the project directory
* Use the project virtual environment
* Load the correct environment variables
* Keep the API running after SSH disconnects

---

## Database

The project supports PostgreSQL through the `DATABASE_URL` environment variable.

Production/server database will use PostgreSQL.

Example:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/client_intake_dev
```

For local development, SQLite can still be used:

```env
DATABASE_URL=sqlite:///app.db
```

For automated tests, the project uses an in-memory SQLite database configured in pytest fixtures. Tests do not depend on the development or server database.

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

Possible future variables:

```env
FLASK_ENV=production
CORS_ORIGINS=https://frontend-domain.com
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure-temporary-password
```

Important:

* `.env` must not be committed to Git
* production secrets must not be stored in the repository
* JWT secret must be strong and different from local development

---

## Frontend and CORS Considerations

A frontend will eventually call this backend API.

Possible frontend deployment options:

* Netlify
* Vercel
* Static site on the same server
* Separate frontend container in Docker

If the frontend is hosted on a different domain, the backend will need CORS configuration.

Example future architecture:

```text
Frontend:
https://client-intake-ui.com

Backend API:
https://api.client-intake.com
```

In that case, the Flask API must allow requests from the frontend origin.

Planned future dependency:

```text
Flask-CORS
```

CORS should be configured carefully. It should not allow every origin in production unless intentionally required.

---

## Security Considerations

Because this project will run on a self-managed server, security is critical.

Planned security work:

* Keep SSH access secure
* Disable password-based SSH login if possible
* Use SSH keys
* Keep system packages updated
* Use a firewall
* Expose only required ports
* Keep Gunicorn bound to `127.0.0.1`
* Put Nginx in front of Gunicorn
* Use HTTPS
* Protect environment variables
* Use strong JWT secrets
* Avoid committing credentials
* Create a safe admin bootstrap process
* Review CORS configuration before frontend deployment

---

## Deployment Workflow

Planned deployment workflow:

```text
1. Develop locally
2. Run tests locally
3. Commit changes
4. Push to GitHub
5. SSH into server
6. Pull latest changes
7. Activate virtual environment
8. Install dependencies
9. Run migrations
10. Restart Gunicorn/systemd service
11. Test health endpoint
```

Current manual server commands:

```bash
cd ~/apps/client-intake-case-tracking-api
git pull
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
gunicorn -c gunicorn.conf.py run:app
```

Future systemd workflow:

```bash
cd ~/apps/client-intake-case-tracking-api
git pull
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart client-intake-api
sudo systemctl status client-intake-api
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

* Gunicorn runs manually
* No systemd service yet
* No Nginx reverse proxy yet
* No HTTPS yet
* No domain configured yet
* No production CORS configuration yet
* No admin bootstrap command yet
* No Docker deployment yet
* Server security hardening still pending

---

## Next Deployment Issues

Recommended next issues:

1. Create systemd service for Gunicorn
2. Configure Nginx reverse proxy
3. Add HTTPS with Certbot
4. Add admin bootstrap CLI command
5. Add production CORS configuration
6. Add Dockerfile
7. Add Docker Compose deployment
8. Add deployment runbook

---

## Acceptance Criteria

This deployment plan is complete when:

* Deployment option is selected
* Self-managed server architecture is documented
* Gunicorn usage is documented
* PostgreSQL deployment requirements are documented
* Environment variables are documented
* CORS needs are documented
* Current deployment status is documented
* Next deployment steps are clearly listed

Current selected deployment path:

```text
Self-managed Linux server with Gunicorn, PostgreSQL, systemd, and Nginx.
```
