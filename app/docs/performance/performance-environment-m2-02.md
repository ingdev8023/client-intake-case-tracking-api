# M2-02 — Isolated PostgreSQL Performance Environment

**Project:** Client Intake & Case Tracking API  
**Date:** 2026-11-09  
**Issue:** [#91](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/91)  
**Prior baseline:** [M2-01](api-baseline-2026-11.md)  
**Measured pagination results:** [M2-02 benchmark](pagination-benchmark-2026-11-09.md)

## 1. Purpose and architecture

Use a dedicated PostgreSQL database, separate application worktree, and isolated Gunicorn process to test synthetic CRM workloads without changing the existing systemd, Nginx, or Cloudflare setup.

```text
Windows / Locust (127.0.0.1:18001)
   └── SSH local port forward
       └── Ubuntu / Gunicorn 127.0.0.1:8001 (2 sync workers)
           └── Flask API (~/apps/client-intake-perf)
               └── PostgreSQL: client_intake_perf, role client_perf_user

Separate existing service (not modified):
Nginx → systemd/Gunicorn port 8000 → existing application database
```

Host: Ubuntu 26.04 LTS, 5th-generation Intel Core i5, 8 GB RAM. **Only the database contents and application processes are isolated.** Both databases share PostgreSQL's server process and the same CPU, RAM, storage, and operating system. The SSH tunnel is a *different* HTTP path from the M2-01 LAN/Nginx benchmark; raw latencies are not directly comparable as dataset-size effects.

## 2. Provision database and role (first setup only)

Open PostgreSQL administrator `psql` on Ubuntu:

```bash
sudo -u postgres psql
```

The following is for a **new** test database only; do not rerun once provisioned:

```sql
CREATE ROLE client_perf_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
\password client_perf_user
CREATE DATABASE client_intake_perf OWNER client_perf_user;
REVOKE ALL ON DATABASE client_intake_perf FROM PUBLIC;
```

The password is entered interactively; never include it in Git or commands. Exit with `\q`. We verified `client_perf_user` lacked `SELECT`, `INSERT`, `DELETE` on the eight tables in the existing `client_intake_dev` database and lacked `CREATE` on that database/public schema. The performance role owns its own test DB but has no superuser privileges.

## 3. Dedicated worktree and process environment

On Ubuntu, **do not switch branches in the running service's checkout**:

```bash
cd ~/apps/client-intake-case-tracking-api
git fetch origin perf/91-isolated-dataset
git worktree add --detach ~/apps/client-intake-perf origin/perf/91-isolated-dataset
cd ~/apps/client-intake-perf
source ../client-intake-case-tracking-api/.venv/bin/activate
git rev-parse --short HEAD
```

For an existing worktree, from `~/apps/client-intake-perf`, check `git status --short`, then update it with `git fetch origin perf/91-isolated-dataset` and `git switch --detach origin/perf/91-isolated-dataset`. The test used the existing venv without installing additional dependencies; changes to that shared venv would also affect the deployed checkout. Do not edit the existing application's `.env`.

Configure the **performance terminal only**, entering commands in sequence:

```bash
read -rsp "Performance DB password: " PGPASSWORD
echo
export PGPASSWORD
export DATABASE_URL="postgresql+psycopg2://client_perf_user@127.0.0.1:5432/client_intake_perf"
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

`psycopg2` (libpq) uses `PGPASSWORD`; the URL therefore contains no password. A fresh test JWT key invalidates earlier test tokens, but clients can log in again. Do not print or commit the secrets.

**Mandatory connection preflight** before any migrations or writes:

```bash
python - <<'PY_CHECK'
from app import create_app
from app.extensions.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        identity = tuple(conn.execute(
            text("SELECT current_user, current_database()")
        ).one())
assert identity == ("client_perf_user", "client_intake_perf"), identity
print("Verified:", identity)
PY_CHECK
```

## 4. Apply existing migrations and create a test admin

After the preflight, run:

```bash
python -m flask --app run:app db upgrade
python -m flask --app run:app db current
```

The existing initial Alembic revision `d82bbba225d9` was applied successfully; the test database contained eight tables, including `alembic_version`, `client`, `cases`, `user`, and `users_cases`. Use **`db upgrade`**, not a new `db migrate` revision or `db.create_all()`.

```bash
python -m flask --app run:app create-admin
```

Enter synthetic test credentials at the prompts (example email: `perf-admin@example.test`). This account is the **Flask application admin**, not the PostgreSQL user. Its password is never placed in source control.

## 5. Seed and verify records

After the application preflight and confirming an empty test dataset:

```bash
python -m flask --app run:app seed-perf
```

Current implementation: `app/cli.py` checks actual `current_user` and `current_database`, refuses to seed if any clients/cases or existing synthetic users are detected, and commits a single SQLAlchemy transaction (rollback on SQLAlchemy failure). Generators are in `load_tests/synthetic_data.py`. The code uses ORM references (`Case(client=..., assigned_users=[...])`) rather than manually assigning IDs.

**Verified result:**

| Database entity / relationship | Count |
|---|---:|
| Clients | 500 |
| Newly generated staff users | 100 |
| Total users (including preserved admin) | 101 |
| Cases | 1,000 |
| `users_cases` association rows | 1,000 |
| Distinct clients with cases | 434 |
| Distinct staff with case assignments | 100 |

```sql
SELECT current_database(), current_user,
       (SELECT COUNT(*) FROM client) AS clients,
       (SELECT COUNT(*) FROM "user") AS users,
       (SELECT COUNT(*) FROM cases) AS cases,
       (SELECT COUNT(*) FROM users_cases) AS assignments,
       (SELECT COUNT(DISTINCT client_id) FROM cases) AS clients_with_cases,
       (SELECT COUNT(DISTINCT user_id) FROM users_cases) AS users_with_cases;
```

**Reproducibility caveat:** client dates use `Random(42)`; case type/client/assignment selection uses `Random(43)`. Synthetic user passwords are randomly generated and bcrypt-hashed, and timestamps/auto-increment IDs change between resets. Therefore row counts and certain assignments are repeatable, but the **entire database dump is not bitwise deterministic**. The generated staff passwords are not retained; Locust logs in as the dedicated test admin. Case types vary, while *all case statuses are currently `open` and all stages `intake`*.

The successful second invocation of `seed-perf` returned `Error: Performance database already contains clients or cases.` (no duplicate insert attempted).

## 6. Start and check the isolated API

From the configured Ubuntu worktree terminal:

```bash
gunicorn --bind 127.0.0.1:8001 --workers 2 run:app
```

Keep Gunicorn running in this foreground terminal. In a separate Ubuntu terminal:

```bash
curl -i http://127.0.0.1:8001/health
curl -i http://127.0.0.1:8001/ready
```

Observed: both HTTP `200`. The performance admin's `POST /login` also returned `200`; the authenticated `/cases?page=1&limit=10` returned `200`, ten items, `total_items=1000`, and `total_pages=100`. Do **not** change Nginx, Cloudflare, firewall ports, or the existing systemd service. Stop only this temporary Gunicorn with `Ctrl+C` when finished.

## 7. SSH tunnel and Locust (Windows)

Open a PowerShell window and keep the forwarding connection running:

```powershell
ssh -N -L 18001:127.0.0.1:8001 djdev@YOUR_SERVER_LAN_IP
```

In another PowerShell terminal, confirm `curl.exe -i http://127.0.0.1:18001/ready` returns `200`. Set the Locust credentials and workload variables in the **same PowerShell session used to launch Locust**:

```powershell
$env:PERF_EMAIL = "perf-admin@example.test"
$secret = Read-Host "Performance admin password" -AsSecureString
$env:PERF_PASSWORD = [System.Net.NetworkCredential]::new("", $secret).Password
Remove-Variable secret

$env:PERF_PAGE = "1"
$env:PERF_LIMIT = "10"
$env:PERF_WAIT_MIN = "1"
$env:PERF_WAIT_MAX = "3"

python -m locust -f load_tests/locustfile.py `
  --host http://127.0.0.1:18001 `
  --web-host 127.0.0.1 --web-port 8089
```

Open `http://127.0.0.1:8089`; choose users/spawn rate/duration in the Locust web UI. The captured three-minute reports used 10 simulated users. To change page, limit, or wait time, update `PERF_*` variables **and restart Locust**, then save each HTML/CSV report separately. The simulated users all log in with the same test-admin account; they do not represent 10 different staff login identities.

## 8. Safe cleanup (only for the known 500/100/1,000 dataset)

**Optional and destructive, only inside `client_intake_perf`.** Stop the test traffic first. Never run on the main DB. Do not proceed if other notes, tasks, or audit events were created, or if counts differ.

Connect as the test role:

```bash
psql -h 127.0.0.1 -U client_perf_user -d client_intake_perf -W
```

Review before executing. Use one transaction, with exact counts and identity guards:

```sql
BEGIN;
DO $$
BEGIN
    IF current_database() <> 'client_intake_perf'
       OR current_user <> 'client_perf_user' THEN
       RAISE EXCEPTION 'Wrong DB or role: reset refused';
    END IF;
    IF (SELECT COUNT(*) FROM client) <> 500
       OR (SELECT COUNT(*) FROM "user") <> 101
       OR (SELECT COUNT(*) FROM "user" WHERE user_email LIKE 'test_user%@test.test') <> 100
       OR (SELECT COUNT(*) FROM "user" WHERE user_role = 'admin') <> 1
       OR (SELECT COUNT(*) FROM cases) <> 1000
       OR (SELECT COUNT(*) FROM users_cases) <> 1000
       OR (SELECT COUNT(*) FROM audit_log) <> 0
       OR (SELECT COUNT(*) FROM notes) <> 0
       OR (SELECT COUNT(*) FROM tasks) <> 0 THEN
       RAISE EXCEPTION 'Unexpected records: reset refused';
    END IF;
END $$;

DELETE FROM users_cases;
DELETE FROM cases;
DELETE FROM client;
DELETE FROM "user" WHERE user_email LIKE 'test_user%@test.test';

SELECT (SELECT COUNT(*) FROM client) AS clients,
       (SELECT COUNT(*) FROM "user") AS users,
       (SELECT COUNT(*) FROM cases) AS cases,
       (SELECT COUNT(*) FROM users_cases) AS assignments;
-- Expected: 0 | 1 | 0 | 0. Confirm that the remaining user is the test admin.
-- Manually execute COMMIT; only if all checks match. Otherwise ROLLBACK;
```

If any guard fails, the transaction is aborted; use `ROLLBACK;` and investigate. This script deliberately does not delete or truncate the existing application database. It is a manual reset, not a reusable general-purpose migration.

## 9. Evidence and remaining acceptance criteria

**Verified in the hands-on exercise:** isolated DB and restricted role; initial migrations; role/table privileges; dedicated Git worktree; loopback-only Gunicorn; SSH forwarding; `200` health/readiness/login/authenticated cases; synthetic FK relationships/counts; duplicate rejection; local `tests/test_synthetic_data.py` passing on Windows and Ubuntu; Locust environment-variable credentials and pagination reports.

**Still required before closing #91 (or explicitly adjust scope in the issue):**

- [ ] Add an **explicit Click operator confirmation** after DB/duplicate checks and before writes; the committed `seed-perf` currently does not prompt.
- [ ] Generate valid **varied status and stage** values, or update the original issue criteria to accept realistic but uniform initial `open`/`intake` states.
- [ ] Verify the main API database remains unaffected via read-only queries against the actual main connection and check for synthetic email markers. Earlier M2-01 notes recorded three cases, but no pre-seed snapshot is included here.
- [ ] Run `python -m pytest tests -v`, obtain a green GitHub Actions run (workflow runs on PRs to `main`), and check no secrets were committed.
- [ ] Open/review/merge a PR with `Closes #91` and link the runbook plus benchmark results.

Never commit `PGPASSWORD`, the test JWT key, Locust credentials, bearer tokens, or secret-bearing logs. After stopping the performance process, `unset PGPASSWORD DATABASE_URL JWT_SECRET_KEY` in its Ubuntu shell; in PowerShell run `Remove-Item Env:PERF_PASSWORD` when done.
