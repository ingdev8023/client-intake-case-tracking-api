"""M2-08: PostgreSQL backup automation — safety preflight."""

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import hashlib
import tempfile

EXPECTED_DB = "client_intake_perf"
EXPECTED_ROLE = "client_perf_user"
HOST = "127.0.0.1"
PORT = "5432"


def run_command(command):
    """Execute a command and capture its result."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )


def verify_environment():
    """Prevent accidental execution against unintended databases."""

    if os.getenv("RUN_PERF_BACKUP") != "1":
        raise RuntimeError(
            "Backup not authorized. Set RUN_PERF_BACKUP=1."
        )

    for executable in ("psql", "pg_dump","pg_restore"):
        if shutil.which(executable) is None:
            raise RuntimeError(
                f"Required executable not found: {executable}"
            )

    result = run_command([
        "psql",
        "-X",
        "-w",
        "-h", HOST,
        "-p", PORT,
        "-U", EXPECTED_ROLE,
        "-d", EXPECTED_DB,
        "-At",
        "-F", "|",
        "-c", "SELECT current_database(), current_user",
    ])

    identity = result.stdout.strip().split("|")

    if identity != [EXPECTED_DB, EXPECTED_ROLE]:
        raise RuntimeError(
            "STOP: Unexpected database connection identity"
        )

    print(f"Database verified: {EXPECTED_DB}")
    print(f"Role verified: {EXPECTED_ROLE}")

def create_backup():
    """Create and verify a backup of the synthetic performance DB."""

    backup_dir = Path.home() / "db-recovery-lab" / "m2-08"
    old_umask = os.umask(0o077)
    partial_file = None

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.chmod(0o700)

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        unique_id = uuid4().hex[:12]

        final_file = backup_dir / (
            f"{EXPECTED_DB}_{timestamp}_{unique_id}.dump"
        )

        # Create a temporary file in the backup directory.
        fd, temp_name = tempfile.mkstemp(
            prefix="backup_",
            suffix=".partial",
            dir=backup_dir,
        )

        os.close(fd)
        partial_file = Path(temp_name)

        # Generate the actual PostgreSQL backup.
        subprocess.run(
            [
                "pg_dump",
                "-w",
                "-h", HOST,
                "-p", PORT,
                "-U", EXPECTED_ROLE,
                "-d", EXPECTED_DB,
                "--format=custom",
                "--file", str(partial_file),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=180,
        )

        # Reject an empty backup.
        if partial_file.stat().st_size == 0:
            raise RuntimeError("Backup file is empty")

        # Verify the PostgreSQL archive can be inspected.
        result = subprocess.run(
            ["pg_restore", "--list", str(partial_file)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        if "TABLE" not in result.stdout:
            raise RuntimeError("Backup archive has no table entries")

        # Calculate SHA-256 without loading the entire file into RAM.
        with partial_file.open("rb") as file:
            digest = hashlib.file_digest(
                file, "sha256"
            ).hexdigest()

        # Publish the verified backup.
        partial_file.rename(final_file)

        checksum_file = Path(str(final_file) + ".sha256")
        checksum_file.write_text(
            f"{digest}  {final_file.name}\n",
            encoding="utf-8",
        )

        print(f"Backup created: {final_file}")
        print(f"Backup size: {final_file.stat().st_size} bytes")
        print(f"Checksum file: {checksum_file}")

        return final_file

    finally:
        if partial_file is not None:
            partial_file.unlink(missing_ok=True)

        os.umask(old_umask)


def main():
    try:
        verify_environment()
        print("PASS: Backup preflight completed.")
        create_backup()

        print("PASS: Backup created and verified.")

    except (
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(f"Backup failed: {type(exc).__name__}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()