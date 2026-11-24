import subprocess
from pathlib import Path

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