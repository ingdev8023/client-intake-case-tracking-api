import subprocess
from pathlib import Path
import os
import sys
import time

import pytest

from app.scripts import backup_postgres as backup


def test_failed_pg_dump_does_not_publish_backup(monkeypatch, tmp_path):
    # Redirect backup output into pytest's temporary directory.
    monkeypatch.setattr(backup.Path, "home", lambda: tmp_path)

    def fake_run(command, **kwargs):
        assert command[0] == "pg_dump"

        # Simulate pg_dump writing some data before failing.
        output_path = Path(command[command.index("--file") + 1])
        output_path.write_bytes(b"incomplete backup")

        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        backup.create_backup()

    backup_dir = tmp_path / "db-recovery-lab" / "m2-08"

    # No partial file or successful backup should remain.
    assert list(backup_dir.iterdir()) == []


def test_empty_backup_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(backup.Path, "home", lambda: tmp_path)

    def fake_run(command, **kwargs):
        assert command[0] == "pg_dump"

        # Return success without writing anything.
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Backup file is empty"):
        backup.create_backup()

    backup_dir = tmp_path / "db-recovery-lab" / "m2-08"

    assert list(backup_dir.iterdir()) == []

def test_checksum_failure_does_not_publish_backup(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(backup.Path, "home", lambda: tmp_path)

    def fake_run(command, **kwargs):
        if command[0] == "pg_dump":
            output_path = Path(
                command[command.index("--file") + 1]
            )
            output_path.write_bytes(b"fake backup data")

            return subprocess.CompletedProcess(command, 0)

        if command[0] == "pg_restore":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="TABLE public cases",
            )

        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    original_write_text = Path.write_text

    def fake_write_text(self, data, **kwargs):
        if self.suffix == ".sha256":
            raise OSError("Simulated checksum write failure")

        return original_write_text(self, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", fake_write_text)

    with pytest.raises(
        OSError,
        match="Simulated checksum write failure",
    ):
        backup.create_backup()

    backup_dir = tmp_path / "db-recovery-lab" / "m2-08"

    assert list(backup_dir.iterdir()) == [], (
        "A failed checksum write left a published backup"
    )


@pytest.mark.skipif(
    os.name != "posix",
    reason="fcntl locking requires POSIX",
)
def test_backup_lock_prevents_overlapping_processes(tmp_path):
    """Two independent processes cannot hold the same backup lock."""

    repo_root = Path(__file__).resolve().parents[1]

    # Both processes share the same isolated HOME,
    # ensuring they use the same lock file.
    env = {**os.environ, "HOME": str(tmp_path)}

    ready_file = tmp_path / "holder_ready"

    holder_code = """
import sys
from pathlib import Path
from app.scripts.backup_postgres import backup_lock

with backup_lock():
    Path(sys.argv[1]).write_text("ready")
    sys.stdin.read(1)
"""

    contender_code = """
from app.scripts.backup_postgres import backup_lock

try:
    with backup_lock():
        print("ACQUIRED")
except RuntimeError as exc:
    if "already running" in str(exc):
        print("BLOCKED")
    else:
        raise
"""

    # Process A acquires the lock and waits for input.
    holder = subprocess.Popen(
        [sys.executable, "-c", holder_code, str(ready_file)],
        cwd=repo_root,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        deadline = time.monotonic() + 10

        while not ready_file.exists():
            if holder.poll() is not None:
                pytest.fail("Process A exited before acquiring the lock")

            if time.monotonic() >= deadline:
                pytest.fail("Process A never acquired the lock")

            time.sleep(0.05)

        # Process B attempts to acquire A's lock.
        contender = subprocess.run(
            [sys.executable, "-c", contender_code],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert contender.returncode == 0, contender.stderr
        assert contender.stdout.strip() == "BLOCKED"

    finally:
        # Always release A, including when assertions fail.
        try:
            if holder.poll() is None:
                holder.communicate(input="x", timeout=5)
            else:
                holder.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            holder.kill()
            holder.communicate()

    assert holder.returncode == 0

    # After A exits, a new process must acquire the lock.
    after_release = subprocess.run(
        [sys.executable, "-c", contender_code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert after_release.returncode == 0, after_release.stderr
    assert after_release.stdout.strip() == "ACQUIRED"