"""M2-08: PostgreSQL backup automation — safety preflight."""

import os
import shutil
import subprocess

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

    for executable in ("psql", "pg_dump"):
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


def main():
    try:
        verify_environment()
        print("PASS: Backup preflight completed.")

    except (
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(f"Preflight failed: {type(exc).__name__}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()