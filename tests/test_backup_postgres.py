import subprocess
from pathlib import Path
import os
import sys
import time
import hashlib

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

def test_successful_backup_returns_verified_file(
    monkeypatch, tmp_path
):
    import hashlib

    monkeypatch.setattr(backup.Path, "home", lambda: tmp_path)

    data = b"synthetic PostgreSQL backup test data"

    def fake_run(command, **kwargs):
        if command[0] == "pg_dump":
            output = Path(command[command.index("--file") + 1])
            output.write_bytes(data)

        elif command[0] == "pg_restore":
            return subprocess.CompletedProcess(
                command, 0, stdout="TABLE public cases"
            )

        else:
            raise AssertionError(command)

        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    result = backup.create_backup()

    assert result is not None
    assert result.exists()
    assert result.suffix == ".dump"
    assert result.read_bytes() == data

    checksum = Path(str(result) + ".sha256")

    assert checksum.exists()
    assert checksum.read_text().split()[0] == (
        hashlib.sha256(data).hexdigest()
    )




def test_upload_rejects_corrupted_backup(monkeypatch, tmp_path):
    monkeypatch.setenv("RUN_PERF_BACKUP", "1")
    monkeypatch.setattr(backup.Path, "home", lambda: tmp_path)

    backup_dir = tmp_path / "db-recovery-lab" / "m2-08"
    backup_dir.mkdir(parents=True)

    backup_file = backup_dir / "client_intake_perf_test.dump"
    backup_file.write_bytes(b"CORRUPTED BACKUP")

    checksum_file = Path(str(backup_file) + ".sha256")

    # The checksum belongs to DIFFERENT content.
    original_hash = hashlib.sha256(
        b"ORIGINAL BACKUP"
    ).hexdigest()

    checksum_file.write_text(
        f"{original_hash}  {backup_file.name}\n",
        encoding="utf-8",
    )

    def forbidden_upload(*args, **kwargs):
        pytest.fail("rclone must not run for corrupted backups")

    monkeypatch.setattr(
        backup.subprocess, "run", forbidden_upload
    )

    with pytest.raises(
        RuntimeError, match="Backup checksum mismatch"
    ):
        backup.upload_backup(backup_file)

def test_upload_failure_is_reported(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("RUN_PERF_BACKUP", "1")
    monkeypatch.setattr(backup.Path, "home", lambda: tmp_path)

    backup_dir = tmp_path / "db-recovery-lab" / "m2-08"
    backup_dir.mkdir(parents=True)

    backup_file = backup_dir / "client_intake_perf_test.dump"
    data = b"synthetic test backup"
    backup_file.write_bytes(data)

    checksum_file = Path(str(backup_file) + ".sha256")
    digest = hashlib.sha256(data).hexdigest()

    checksum_file.write_text(
        f"{digest}  {backup_file.name}\n",
        encoding="utf-8",
    )

    # Pretend rclone is installed.
    monkeypatch.setattr(
        backup.shutil,
        "which",
        lambda executable: "/usr/bin/rclone",
    )

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 0)

        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
            stderr="Simulated cloud upload failure",
        )

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        backup.upload_backup(backup_file)

    assert len(calls) == 2

    assert calls[0][-1].startswith("gdrive_crypt:")
    assert calls[1][-1].endswith(".sha256")

    captured = capsys.readouterr()
    assert "PASS: Encrypted offsite upload" not in captured.out

def test_verify_crypt_remote_accepts_valid_config(monkeypatch):
    monkeypatch.setattr(
        backup.shutil,
        "which",
        lambda executable: "/usr/bin/rclone",
    )

    def fake_run(command, **kwargs):
        assert command == [
            "rclone", "config", "show", "gdrive_crypt"
        ]

        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                "[gdrive_crypt]\n"
                "type = crypt\n"
                "remote = gdrive_backup:encrypted-postgres-backups\n"
                "filename_encryption = standard\n"
                "directory_name_encryption = true\n"
            ),
        )

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    backup.verify_crypt_remote()

def test_verify_crypt_remote_rejects_plaintext(monkeypatch):
    monkeypatch.setattr(
        backup.shutil,
        "which",
        lambda executable: "/usr/bin/rclone",
    )

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                "[gdrive_crypt]\n"
                "type = drive\n"
            ),
        )

    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError, match="Remote is not encrypted"
    ):
        backup.verify_crypt_remote()