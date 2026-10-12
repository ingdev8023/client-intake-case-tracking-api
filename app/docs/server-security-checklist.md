# Server Security Hardening Checklist

This document is a security checklist for the self-hosted Linux server running the Client Intake & Case Tracking API.

The goal is to maintain a safe, repeatable, and reviewable server baseline before exposing the API publicly.

Current deployment stack:

```text
Nginx
  ↓
systemd-managed Gunicorn
  ↓
Flask API
  ↓
PostgreSQL
```

Current access status:

* API works on the local network
* Gunicorn runs on `127.0.0.1:8000`
* Nginx proxies requests on port `80`
* UFW is active
* Public internet exposure is not fully configured yet

---

## 1. Security Principles

Follow these principles when maintaining this server:

* Expose only what is necessary
* Keep Gunicorn private behind Nginx
* Keep secrets out of Git
* Use SSH keys instead of passwords when possible
* Keep the server updated
* Review logs regularly
* Avoid running application processes as root
* Make small changes and validate each layer
* Document every production-relevant change

---

## 2. Current Server Architecture

The intended deployment architecture is:

```text
Client / Browser / API Consumer
   ↓
Nginx on port 80/443
   ↓
Gunicorn on 127.0.0.1:8000
   ↓
Flask API
   ↓
PostgreSQL
```

Important:

Gunicorn must remain bound to:

```text
127.0.0.1:8000
```

It should not listen on:

```text
0.0.0.0:8000
```

Why?

`127.0.0.1` means only the server itself can reach Gunicorn directly. External users must go through Nginx.

---

## 3. Daily / Startup Health Check

Run these after starting the server or after reboot.

### Check system status

```bash
uptime
hostname -I
```

### Check firewall

```bash
sudo ufw status verbose
```

Expected:

```text
Status: active
OpenSSH ALLOW
Nginx Full ALLOW
```

### Check API service

```bash
sudo systemctl status client-intake-api.service
```

Expected:

```text
active (running)
```

### Check Nginx

```bash
sudo systemctl status nginx
```

Expected:

```text
active (running)
```

### Check PostgreSQL

```bash
sudo systemctl status postgresql
```

Expected:

```text
active (running)
```

### Test Gunicorn directly from server

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"message":"API running"}
```

### Test Nginx reverse proxy from server

```bash
curl http://127.0.0.1/health
```

Expected:

```json
{"message":"API running"}
```

### Test protected route

```bash
curl http://127.0.0.1/cases
```

Expected:

```json
{"msg":"Missing Authorization Header"}
```

This confirms JWT protection is active.

---

## 4. SSH Security Checklist

SSH is the main administrative entry point to the server. Protect it carefully.

### Check SSH service

```bash
sudo systemctl status ssh
```

Expected:

```text
active (running)
```

### Confirm SSH port exposure

```bash
sudo ss -tulpn | grep ssh
```

Usually SSH listens on port `22`.

### Recommended SSH hardening

Edit:

```bash
sudo nano /etc/ssh/sshd_config
```

Recommended settings:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Important:

Only disable password authentication after confirming SSH key login works from your laptop.

### Restart SSH after changes

```bash
sudo systemctl restart ssh
```

### Test SSH before closing current session

Open a second terminal from your laptop:

```bash
ssh djdev@SERVER_IP
```

Only close the original SSH session after confirming the new login works.

---

## 5. Firewall Checklist

The server uses UFW.

### Check firewall status

```bash
sudo ufw status verbose
```

### Recommended allowed services before public exposure

```text
OpenSSH
Nginx Full
```

`Nginx Full` allows:

```text
80/tcp
443/tcp
```

### Allow SSH

```bash
sudo ufw allow OpenSSH
```

### Allow Nginx

```bash
sudo ufw allow 'Nginx Full'
```

### Enable firewall

```bash
sudo ufw enable
```

### Do not expose Gunicorn

Do not allow port `8000` publicly.

Avoid:

```bash
sudo ufw allow 8000
```

Gunicorn should only be reachable locally through:

```text
127.0.0.1:8000
```

---

## 6. Exposed Ports Checklist

Check listening ports:

```bash
sudo ss -tulpn
```

Expected:

```text
22    SSH
80    Nginx HTTP
443   Nginx HTTPS, later
8000  Gunicorn on 127.0.0.1 only
5432  PostgreSQL local only, if visible
```

### Safer filtered checks

Check Nginx:

```bash
sudo ss -tulpn | grep ':80'
```

Expected:

```text
*:80
```

Check Gunicorn:

```bash
sudo ss -tulpn | grep ':8000'
```

Expected:

```text
127.0.0.1:8000
```

Check PostgreSQL:

```bash
sudo ss -tulpn | grep ':5432'
```

Expected for local-only PostgreSQL:

```text
127.0.0.1:5432
```

If PostgreSQL listens on `0.0.0.0:5432`, review configuration before public exposure.

---

## 7. Nginx Security Checklist

Nginx is the public-facing service.

### Check config syntax

```bash
sudo nginx -t
```

Expected:

```text
syntax is ok
test is successful
```

### Reload Nginx after config changes

```bash
sudo systemctl reload nginx
```

### Check enabled site

```bash
ls -la /etc/nginx/sites-enabled/
```

Expected:

```text
client-intake-api
```

If the default site is not needed, remove it:

```bash
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Current reverse proxy config

Location:

```text
/etc/nginx/sites-available/client-intake-api
```

Expected proxy target:

```nginx
proxy_pass http://127.0.0.1:8000;
```

### Important proxy headers

The config should include:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

These headers help the backend understand the original request context.

---

## 8. Gunicorn Security Checklist

Gunicorn should be managed by systemd and should not be directly public.

### Check service

```bash
sudo systemctl status client-intake-api.service
```

### Check logs

```bash
sudo journalctl -u client-intake-api.service -n 50
```

### Follow live logs

```bash
sudo journalctl -u client-intake-api.service -f
```

### Check Gunicorn bind address

Open:

```bash
cat gunicorn.conf.py
```

Expected:

```python
bind = "127.0.0.1:8000"
workers = 2
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

Do not bind Gunicorn to:

```python
bind = "0.0.0.0:8000"
```

unless intentionally exposing it, which is not recommended for this project.

---

## 9. systemd Service Checklist

Service file:

```text
/etc/systemd/system/client-intake-api.service
```

Expected service behavior:

* runs as `djdev`
* uses project working directory
* loads `.env`
* runs Gunicorn from virtual environment
* restarts on failure
* starts on boot

### Check service file

```bash
sudo cat /etc/systemd/system/client-intake-api.service
```

Expected structure:

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

### Reload systemd after edits

```bash
sudo systemctl daemon-reload
```

### Restart service

```bash
sudo systemctl restart client-intake-api.service
```

### Enable on boot

```bash
sudo systemctl enable client-intake-api.service
```

### Confirm enabled

```bash
sudo systemctl is-enabled client-intake-api.service
```

Expected:

```text
enabled
```

---

## 10. Secrets and Environment Variables

Secrets must not be committed to Git.

Server `.env` path:

```text
/home/djdev/apps/client-intake-case-tracking-api/.env
```

Expected variables:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
JWT_SECRET_KEY=secure-secret
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Check `.env` exists

```bash
ls -la /home/djdev/apps/client-intake-case-tracking-api/.env
```

### Recommended permissions

```bash
chmod 600 /home/djdev/apps/client-intake-case-tracking-api/.env
```

### Check permissions

```bash
ls -la /home/djdev/apps/client-intake-case-tracking-api/.env
```

Expected:

```text
-rw-------
```

### Never commit

Confirm `.env` is ignored:

```bash
git status
```

`.env` should not appear as a tracked file.

---

## 11. PostgreSQL Security Checklist

PostgreSQL should not be publicly exposed.

### Check PostgreSQL service

```bash
sudo systemctl status postgresql
```

### Check PostgreSQL listening address

```bash
sudo ss -tulpn | grep ':5432'
```

Expected:

```text
127.0.0.1:5432
```

### Connect locally

```bash
psql -U postgres -d client_intake_dev
```

Inside `psql`:

```sql
\dt
```

Exit:

```sql
\q
```

### Migration check

From the project folder:

```bash
source .venv/bin/activate
flask db current
flask db upgrade
```

### Notes

* Do not expose port `5432` publicly.
* Use strong database passwords.
* Keep database credentials in `.env`.
* Use migrations, not `db.create_all()`, for server/dev database changes.

---

## 12. Application Security Checklist

### JWT secret

The server must use a strong `JWT_SECRET_KEY`.

Do not use:

```text
test-secret-key
dev-secret
password
123456
```

Use a long random value.

Generate one:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Password storage

User passwords must be hashed with bcrypt.

Never store plaintext passwords.

### Admin bootstrap

Create the first admin with:

```bash
flask create-admin
```

Do not hardcode production admin credentials in the repository.

### Role checks

Admin-only actions must remain protected:

* create users
* list users, depending on product rules
* activate users
* deactivate users
* soft delete cases

### Protected routes

Protected routes should return:

```json
{"msg":"Missing Authorization Header"}
```

when called without a token.

Test:

```bash
curl http://127.0.0.1/cases
```

---

## 13. CORS Security Checklist

CORS is configured through:

```env
CORS_ORIGINS=...
```

### Check allowed origins

Development example:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Production example:

```env
CORS_ORIGINS=https://frontend-domain.com
```

### Avoid wildcard origins in production

Avoid:

```env
CORS_ORIGINS=*
```

### Test allowed origin

```bash
curl -i http://127.0.0.1/health -H "Origin: http://localhost:5173"
```

Expected header:

```http
Access-Control-Allow-Origin: http://localhost:5173
```

### Test blocked origin

```bash
curl -i http://127.0.0.1/health -H "Origin: http://evil-site.com"
```

Expected:

No `Access-Control-Allow-Origin: http://evil-site.com`.

---

## 14. Update and Patch Checklist

Keep the server updated.

### Check available updates

```bash
sudo apt update
```

### Apply updates

```bash
sudo apt upgrade -y
```

### Remove unused packages

```bash
sudo apt autoremove -y
```

### Reboot if required

Check:

```bash
ls /var/run/reboot-required
```

If the file exists, reboot when safe:

```bash
sudo reboot
```

After reboot, run the daily startup health check.

---

## 15. Logs Checklist

### API service logs

```bash
sudo journalctl -u client-intake-api.service -n 50
```

Follow live:

```bash
sudo journalctl -u client-intake-api.service -f
```

### Nginx access logs

```bash
sudo tail -n 50 /var/log/nginx/access.log
```

Follow live:

```bash
sudo tail -f /var/log/nginx/access.log
```

### Nginx error logs

```bash
sudo tail -n 50 /var/log/nginx/error.log
```

Follow live:

```bash
sudo tail -f /var/log/nginx/error.log
```

### Auth logs

```bash
sudo tail -n 50 /var/log/auth.log
```

Useful for SSH login attempts.

---

## 16. Git and Deployment Hygiene

The server should usually not create code changes.

Normal workflow:

```text
Laptop → edit → test → commit → push
Server → pull → install deps → migrate → restart service
```

### Server deployment commands

```bash
cd ~/apps/client-intake-case-tracking-api
git pull
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart client-intake-api.service
curl http://127.0.0.1/health
```

### Check server repo

```bash
git status
```

Expected:

```text
nothing to commit, working tree clean
```

### Do not commit from server unless intentionally fixing deployment-only files

Avoid:

```bash
git add .
git commit
```

from the server unless you clearly understand why.

---

## 17. Backup Considerations

Before public exposure, define a backup strategy.

### Minimum backup targets

* PostgreSQL database
* `.env` file
* Nginx config
* systemd service file

### PostgreSQL backup example

```bash
pg_dump -U postgres client_intake_dev > client_intake_backup.sql
```

### Restore example

```bash
psql -U postgres client_intake_dev < client_intake_backup.sql
```

### Config files to backup

```text
/home/djdev/apps/client-intake-case-tracking-api/.env
/etc/nginx/sites-available/client-intake-api
/etc/systemd/system/client-intake-api.service
```

Store backups securely. Do not upload secrets to public repositories.

---

## 18. Before Public Internet Exposure Checklist

Do not expose the server publicly until this checklist is complete.

### Required before router port forwarding

* UFW active
* Only required ports open
* SSH key login works
* Password-based SSH disabled, if possible
* Root SSH login disabled
* Nginx proxy works locally
* Gunicorn bound to `127.0.0.1`
* PostgreSQL not publicly exposed
* Strong JWT secret configured
* `.env` file permissions restricted
* Admin bootstrap command works
* API health endpoint works
* Protected routes require JWT
* CORS origins restricted
* Server updates applied
* Logs reviewed
* Backup plan defined

### Public exposure ports

Only expose:

```text
80/tcp
443/tcp
```

Avoid exposing:

```text
8000/tcp
5432/tcp
```

---

## 19. Public Access / Router / CGNAT Checklist

For a home server, public exposure depends on the network provider and router.

### Router port forwarding

Forward:

```text
External 80/tcp  → Server LAN IP 80/tcp
External 443/tcp → Server LAN IP 443/tcp
```

### Check server LAN IP

```bash
hostname -I
```

### Check public IP

From a browser, search:

```text
what is my ip
```

### CGNAT warning

If the router WAN IP does not match the public IP shown online, the ISP may be using CGNAT.

If CGNAT is active, regular port forwarding may not work.

Possible alternatives:

* request public IP from ISP
* use Cloudflare Tunnel
* use Tailscale
* use a small VPS as reverse proxy
* use a managed hosting platform

---

## 20. Emergency Commands

### Stop API

```bash
sudo systemctl stop client-intake-api.service
```

### Stop Nginx

```bash
sudo systemctl stop nginx
```

### Disable API on boot

```bash
sudo systemctl disable client-intake-api.service
```

### Block HTTP/HTTPS quickly

```bash
sudo ufw deny 'Nginx Full'
```

### Re-enable HTTP/HTTPS

```bash
sudo ufw allow 'Nginx Full'
```

### Reboot server

```bash
sudo reboot
```

### Power off server

```bash
sudo shutdown now
```

---

## 21. Weekly Review Checklist

Run this once per week while the server is active.

```bash
sudo apt update
sudo apt upgrade -y
sudo ufw status verbose
sudo systemctl status client-intake-api.service
sudo systemctl status nginx
sudo systemctl status postgresql
curl http://127.0.0.1/health
curl http://127.0.0.1/cases
git status
sudo journalctl -u client-intake-api.service -n 50
sudo tail -n 50 /var/log/nginx/error.log
```

Review:

* unexpected failed logins
* service restarts
* Nginx errors
* unexpected exposed ports
* uncommitted server files
* outdated packages
* disk usage

Check disk:

```bash
df -h
```

Check memory:

```bash
free -h
```

Check CPU/load:

```bash
top
```

---

## 22. Security Status Summary

Current safe baseline:

* API is behind Nginx
* Gunicorn is private on localhost
* systemd manages the app process
* UFW is active
* PostgreSQL is local
* JWT protects API routes
* CORS is restricted
* Admin bootstrap exists
* Deployment docs exist

Still pending before serious public exposure:

* SSH hardening review
* HTTPS with Certbot
* domain or public access strategy
* backup automation
* log monitoring routine
* router/CGNAT diagnosis
* production secret rotation plan

---

## 23. Final Rule

If a change affects public access, authentication, secrets, firewall, SSH, database, or Nginx, document it and test it immediately.

Use this pattern:

```text
Change one thing
Reload/restart only what is needed
Test locally
Test through Nginx
Check logs
Commit documentation if needed
```
