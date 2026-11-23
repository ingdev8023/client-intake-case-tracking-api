# M2-07 — PostgreSQL backup and restore verification

**Project:** Client Intake & Case Tracking API  
**Date:** 2026-11-23  
**GitHub issue:** [#101 — Verify PostgreSQL backup and restore](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/101)  
**Status:** Manual logical backup and isolated restore verified; production backup automation **not yet implemented**  
**Data classification:** Synthetic performance dataset only

## Executive summary

A PostgreSQL 18.6 custom-format logical backup of the isolated synthetic database `client_intake_perf` was successfully restored into a separate database, `client_intake_restore_verify`. The recovered database contained **8 public tables**, including **1,000 cases, 500 clients, and 101 users**. SQL-level relationship checks detected no orphans in the three relationships examined. PostgreSQL reported **12 foreign-key constraints, all validated**. A separate Flask application context connected to the restored database and successfully loaded a `Case` and its related `Client` through SQLAlchemy.

The observed `time pg_restore` wall-clock reading was **4.893 seconds**, which includes any interactive password-entry time and does **not** constitute an end-to-end RTO. The dataset contained **0 audit-log rows**: restoration of the audit-log *schema* and its foreign keys was confirmed, but recovery of *populated* audit history was **not tested**. This was accepted as a documented limitation for this initial manual drill.

**Conclusion:** The specific archive tested was usable to reconstruct the synthetic database, and the recovered data could be read through the application's ORM. This does not yet establish a working production backup schedule, offsite durability, recovery after complete host loss, complete application restoration, or a defined recovery-time/recovery-point guarantee.

## Environment and safety controls

| Item | Observed value |
|---|---|
| Host | Ubuntu 26.04 home lab |
| PostgreSQL server / `pg_dump` / `pg_restore` | 18.6 |
| Source database | `client_intake_perf` |
| Recovery database | `client_intake_restore_verify` |
| Database role | `client_perf_user` |
| Backup format | `pg_dump --format=custom` (compressed archive) |
| Backup filename | `client_intake_perf_20261123T181524Z.dump` |
| Backup location | `/home/djdev/db-recovery-lab/m2-07/` (outside Git) |
| Approximate size | 54 KB |
| Archive table-of-contents entries | 66 |
| Recovery command duration | `real 0m4.893s` (password entry may contribute) |
| Host free disk space before lab | ~93 GB |

Safety boundaries observed:

- Operations used the **synthetic performance** database, never the active API database.
- Target recovery database had a **different name** and was created explicitly before restore.
- `--no-owner --no-acl --exit-on-error --single-transaction` was used during restore; `--clean` and `--create` were **not** used.
- Dumps, database passwords, and secrets were **not** committed to Git.
- The live Gunicorn/Nginx/Cloudflare services were not the target of restore operations.
- PostgreSQL connection identity was inspected with `current_database()` and `current_user`.

## Procedure and evidence

### 1. Confirm source identity and tool availability

Read-only preflight:

```bash
pg_dump --version
pg_restore --version
psql -h 127.0.0.1 -U client_perf_user -d client_intake_perf \
  -c "SELECT current_database(), current_user, current_setting('server_version');"
df -h ~
```

Observed source identity: `client_intake_perf` / `client_perf_user`; version 18.6.

### 2. Create the protected archive

This illustrates the **manual synthetic-data lab** (not a scheduled production job):

```bash
umask 077
mkdir -p "$HOME/db-recovery-lab/m2-07"
chmod 700 "$HOME/db-recovery-lab/m2-07"

BACKUP_FILE="$HOME/db-recovery-lab/m2-07/client_intake_perf_$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump -h 127.0.0.1 -U client_perf_user -d client_intake_perf \
  --format=custom --file="$BACKUP_FILE"

# Inspect without restoring:
ls -lh "$BACKUP_FILE"
pg_restore --list "$BACKUP_FILE" | head -n 30
sha256sum "$BACKUP_FILE"
```

Observed: roughly **54 KB**, with **66** TOC entries including `cases`, `client`, `user`, `audit_log`, `users_cases`, `tasks`, `notes`, and `alembic_version`. SHA-256 was calculated and displayed. The checksum was **not** independently tested against a second copy of the archive.

> A checksum can detect subsequent changes to bytes when compared to a trusted baseline. It does not independently prove that a dump is logically complete, readable, or recoverable. Archive inspection is similarly not a substitute for restoration.

### 3. Create a distinct recovery target

The target was inspected for prior existence and explicitly created by a PostgreSQL administrator, owned by the performance role:

```bash
sudo -u postgres psql -Atqc \
  "SELECT datname FROM pg_database WHERE datname = 'client_intake_restore_verify';"
# Continue ONLY if no database with that name already exists.
sudo -u postgres createdb --owner=client_perf_user client_intake_restore_verify
```

**Do not run `createdb` again against an existing target.** Never change this example to point at `client_intake_dev` or the active application database. Do not attempt automated target destruction.

### 4. Restore to the isolated database

```bash
BACKUP_FILE="$HOME/db-recovery-lab/m2-07/client_intake_perf_20261123T181524Z.dump"
test -s "$BACKUP_FILE" || exit 1

time pg_restore \
  --host=127.0.0.1 \
  --username=client_perf_user \
  --dbname=client_intake_restore_verify \
  --format=custom \
  --no-owner --no-acl \
  --exit-on-error --single-transaction \
  "$BACKUP_FILE"
```

Observed `real 0m4.893s`, `user 0m0.040s`, `sys 0m0.010s`. Two initial `psql` authentication attempts failed because of incorrect password entry; a subsequent successful login verified the recovery database. The restoration produced the expected tables and row counts.

> The command output shown during the drill did not include a separately captured `echo $?` immediately after `pg_restore`; future runbooks should record the exit status automatically, in addition to verifying restored contents.

### 5. Verify recovered schema and counts

The database identity was confirmed: `client_intake_restore_verify` / `client_perf_user`.

`\dt` showed **8** tables:

`alembic_version`, `audit_log`, `cases`, `client`, `notes`, `tasks`, `user`, `users_cases`.

Observed counts:

| Entity | Restored rows |
|---|---:|
| `cases` | 1,000 |
| `client` | 500 |
| `user` | 101 |
| `audit_log` | 0 |

The counts match the known synthetic dataset composition. The source database was not locked or independently fingerprinted at dump time, so this is **not** a byte-for-byte comparison of two simultaneously captured databases.

### 6. Verify relationships and constraints

Three orphan-detection queries returned zero for:

- Cases with a missing referenced client.
- Rows in `users_cases` referring to missing cases.
- Rows in `users_cases` referring to missing users.

The PostgreSQL catalog query:

```sql
SELECT COUNT(*) AS total_foreign_keys,
       COUNT(*) FILTER (WHERE NOT convalidated) AS unvalidated_foreign_keys
FROM pg_constraint
WHERE contype = 'f'
  AND connamespace = 'public'::regnamespace;
```

returned **12 total foreign keys; 0 unvalidated**. A detailed `pg_constraint` query listed references for `audit_log`, `cases`, `notes`, `tasks`, and `users_cases`.

This verifies the existence/validation metadata of the restored constraints, not an exhaustive audit of every possible relationship or every business invariant.

### 7. Verify application-level reads

A separate Flask application was initialized with a `DATABASE_URL` pointing to `client_intake_restore_verify` and a valid, isolated JWT secret. Within `with app.app_context():`, SQLAlchemy executed `SET TRANSACTION READ ONLY`, verified the database identity, counted models, and loaded a real ORM relationship.

Observed:

```text
Connected to: client_intake_restore_verify
Database role: client_perf_user
Case: 1000
Client: 500
User: 101
AuditLog: 0
Sample case ID: 6
Related client ID: 5
PASS: Flask ORM can read recovered data.
```

The session ended with `db.session.rollback()` and `db.session.remove()`. **No Flask/Gunicorn HTTP service was started against this recovery database.** This was an ORM-level verification, not a full application functionality or user-login test.

## Recovery assessment

**What passed:** a custom-format archive could reconstruct the expected schema/data in a fresh database; the selected relationships had no orphans; 12 foreign keys were present and validated; and a separate Flask/SQLAlchemy instance read recovered records and their relationships.

**Not yet demonstrated:** a filled audit history; full user authentication and HTTP functionality against the restored database; application configuration, roles/tablespaces, and secrets recovery on a new host; failed-disk/full-host recovery; automated scheduled backups; remote encrypted backups; remote download + restore; alerting; retention; or a measured end-to-end recovery time.

**No actual RPO or RTO guarantee** can be inferred from this drill. The measured ~4.9 seconds covers only an interactive small-dataset restore command. It does not include detecting failure, provisioning a new host, installing PostgreSQL, restoring PostgreSQL role definitions, reconfiguring services, updating DNS, or validating the frontend.

## Production-backup design decision (proposed, not implemented)

- **Immediate next protective action:** take a manually verified, access-controlled, encrypted-at-rest backup of the original application database after confirming its identity and data classification. Do not treat the synthetic performance backup as protection of the original DB.
- **Automation:** a small Python or shell wrapper invoking PostgreSQL's **official `pg_dump`**; verify process status, size, archive TOC, checksum, upload result, and record a log. Do not implement a custom database export using ORM model iteration.
- **Scheduling:** prefer a **systemd service + timer** on this Ubuntu/systemd host; `OnCalendar` controls cadence and `Persistent=true` can help catch a missed schedule after downtime. Cron remains valid, but offers less native integration with journald/service status.
- **Offsite:** send a separately encrypted copy to Google Drive, Dropbox, or suitable object storage using `rclone` with a configured **crypt** remote. `copy` of uniquely named snapshots is a safer initial default than a deletion-mirroring `sync`.
- **Operational security:** use a dedicated role with only necessary read permissions and protected connection credentials (`.pgpass` or appropriately restricted environment), restrict local backup permissions, protect rclone/OAuth and crypt configuration, keep encryption/recovery material separate from the backup destination, monitor failure, enforce retention, and periodically test downloading and restoring an offsite backup.
- **Durability:** consider independent versioned or immutable storage to limit ransomware/accidental-deletion blast radius, and maintain additional backups beyond the most recent snapshot.
- **Backup coverage:** `pg_dump` does **not** include cluster-wide roles and tablespaces. Plan their separate backup/recreation, as well as application secrets, migrations, configs, and any uploaded files stored outside PostgreSQL.
- **Recovery objectives:** define the acceptable **RPO** (maximum lost data window) and **RTO** (maximum acceptable outage) with the product owner before choosing backup frequency. Daily dumps may imply up to about a day's lost writes; stricter requirements may demand WAL archiving/PITR, which is out of scope for M2-07.

## Future manual recovery checklist

1. Identify the **approved backup archive** and validate its checksum against a trusted recorded value.
2. Inspect version compatibility and archive TOC (`pg_restore --list`).
3. Provision a **new** recovery database/host; confirm it cannot be confused with an active database.
4. Restore required cluster-wide roles/configuration separately if needed.
5. Restore using `pg_restore --exit-on-error --single-transaction` where appropriate; capture exit status and log.
6. Validate table counts, representative relationships, constraints, and selected business records; check for expected audit data if present.
7. Verify Flask model reads using an explicitly read-only transaction and, once authorized, run a separate HTTP smoke test.
8. Only after approval, define how to switch application traffic to the recovered database. Maintain a rollback plan.
9. Document the event, timestamps, operator, backup identifier, failure modes, data loss window, and measured full-service recovery time.

## Acceptance checklist for issue #101

- [x] Backup/archive creation and identity demonstrated on synthetic PostgreSQL.
- [x] New recovery database used; active application database never targeted.
- [x] Eight tables and expected core record counts verified.
- [x] Three orphan queries returned zero; 12 FK constraints validated.
- [x] Flask ORM read-only verification passed.
- [x] Recovery command duration and limitations recorded.
- [x] Runbook written, with proposed off-host automation strategy.
- [ ] Populated audit-history recovery **not tested**: archive contained zero audit-log records; acknowledged limitation by project owner.
- [ ] Commit this report, run full tests/CI, review and merge PR referring to `Closes #101`.

## Official references

- [PostgreSQL 18 — SQL dump backups](https://www.postgresql.org/docs/18/backup-dump.html)
- [PostgreSQL 18 — pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [PostgreSQL 18 — pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html)
- [PostgreSQL 18 — pg_dumpall](https://www.postgresql.org/docs/18/app-pg-dumpall.html)
- [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
- [rclone crypt](https://rclone.org/crypt/)

**Scope:** This document records M2-07's **manual, synthetic-data recovery drill**. It is not evidence that production backups are running or that the deployed application can be fully recovered after a real incident.
