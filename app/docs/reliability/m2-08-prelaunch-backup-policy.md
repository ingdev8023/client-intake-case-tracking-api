# M2-08 — Pre-launch Backup Policy and Deferred Production Controls

**Decision date:** 2026-11-26  
**Status:** Pre-launch operating decision; **not an activated schedule**  
**Tracking:** [M2-08 #103](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/103) · [Deferred production readiness #104](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/104)

## 1. Context and rationale

The Client Intake & Case Tracking API has no real customers at present. The engineering goal is to preserve a reasonable recovery capability without adding unnecessary production infrastructure before onboarding clients. The database used in M2-08 is the isolated synthetic PostgreSQL database `client_intake_perf`.

This document records an **owner-approved temporary policy**, not an active systemd configuration or approval to back up a different database.

## 2. Temporary backup policy

| Control | Pre-launch decision | Implementation status |
| --- | --- | --- |
| Frequency | Once every **30 days** | **Policy only**; no automated schedule has been activated |
| Retention | Keep backup history for **three months** | **Policy only**; no automated pruning has been enabled |
| Data scope | Synthetic/development data | Script currently allows only `client_intake_perf` / `client_perf_user` |
| Local backup | Protected filesystem directory, custom `pg_dump` archive + SHA-256 | Tested manually through Python |
| Offsite | Client-side encrypted Google Drive via `gdrive_crypt:` | End-to-end manual execution and downloaded restore verified; unattended auth not ready |
| Production app database | **Not yet included** | Separate approval required |
| Real-client privacy and deletion policy | Define before first real client | Backlog #104 |

**Retention interpretation to finalize before implementation:** “Three months” is the agreed policy. A calendar-age rule (e.g. 90 days) and retaining three monthly recovery points are not always equivalent. The automated deletion algorithm must be reviewed, tested and explicitly approved; **do not delete any existing backups as part of this decision**.

**Recovery objective:** A monthly cadence can expose up to approximately 30 days of data changes to loss between successful recovery points (temporary pre-launch RPO). Real-world recovery time (RTO) has not been measured end-to-end and must not be inferred from the isolated `pg_restore` timing.

## 3. Evidence collected

### Local automation
- Synthetic DB and role identity verified before creating a backup.
- Python orchestrates `pg_dump` custom archive creation, `pg_restore --list` inspection, SHA-256 manifest creation and final-file publication.
- Pytest covers failed `pg_dump`, empty archives, failed checksum creation, successful file return, corrupted upload input, failed cloud upload, crypt configuration and Linux process locking.
- Cross-platform tests deliberately skip POSIX-only `fcntl` behavior on Windows.

### Encrypted offsite round-trip
- `gdrive_backup:` is the underlying Google Drive connection.
- `gdrive_crypt:` is a confirmed rclone `crypt` remote pointing to `gdrive_backup:encrypted-postgres-backups`.
- The Python workflow uploaded a synthetic `.dump` and `.sha256`; a fresh download via the encrypted remote passed SHA-256 validation.
- A cloud-downloaded archive was restored into the separate `client_intake_offsite_restore_verify` database.
- Restore exited with code 0. Verification showed **8 tables, 1,000 cases, 500 clients, 101 users, 12 validated foreign keys and zero unvalidated foreign keys**.
- The synthetic dataset contained zero audit rows; recovery of populated audit history was **not** specifically verified.
- Restore wall-clock time was **5.502 seconds**, including an interactive password prompt; this is **not** a production RTO.

## 4. Important limitations and safety controls

1. The OAuth application is currently in Google's **Testing** state (unless subsequently changed). For the requested Drive scope, the refresh token can expire after seven days. Consequently **do not claim a reliable unattended 30-day encrypted offsite schedule**, or enable a systemd timer that blindly runs the existing uploader.
2. If a 30-day automatic *local-only* backup is desired before resolving OAuth, it requires a **separately tested local-only script mode** (the current `main()` performs an offsite upload), then a reviewed systemd service/timer. Until that is implemented, periodic backup execution remains manual.
3. `rclone.conf` includes access tokens and obscured encryption settings. Preserve encryption recovery secrets securely **outside the same server**, and rotate the OAuth client credentials previously exposed in a screenshot before production reliance.
4. The existing script uses an allowlisted synthetic DB. Do not repoint it to the running application database or use production credentials without explicit rollout review.
5. `pg_dump` of one DB does not include PostgreSQL cluster-wide roles or necessarily any files uploaded outside PostgreSQL, app secrets or operational configuration.
6. No cron/systemd timer, automatic cloud retention deletion, backup alerting or scheduled success-monitoring is deployed as part of this documentation.
7. No client privacy/deletion representation is being asserted by this temporary policy. Before storing personal information, decide contract/privacy language, applicable data-protection obligations, deletion requests and retention of copies in backups.

## 5. Deferred work — trigger before the first real client

Tracked in [#104](https://github.com/ingdev8023/client-intake-case-tracking-api/issues/104):

- Resolve Google OAuth token longevity and rotate exposed OAuth client credentials.
- Verify that encryption keys and configuration can be recovered off-server.
- Define final backup schedule, retention and deletion rules, failure alerts, and RPO/RTO for real clients.
- Review backups of the actual application database, least-privilege access and full-system recovery dependencies.
- Implement/test systemd service and timer, plus monitoring and expiration policies.
- Establish privacy notice/terms and handling of client data deletion (including retained backups), before real data enters the system.

## 6. Future decisions and review

Review this temporary policy upon the **first client onboarding decision**, any planned use of personal data, or a materially changed risk profile. A customer-facing launch must not inherit the 30-day RPO or OAuth Testing-mode limitations by default.

**Current engineering result:** the synthetic encrypted offsite restore **works when explicitly run**. Long-term, unattended reliability has **not yet been established**.
