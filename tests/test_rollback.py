import json
from pathlib import Path

from client.app.core import rollback


def test_rollback_restores_previous_version(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    installed_dir = state_dir / "installed"
    backup_dir = state_dir / "backup"

    installed_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)

    version_state_file = state_dir / "version_state.json"

    version_state_file.write_text(
        json.dumps({
            "current_version": "1.4.0",
            "previous_version": "1.0.0",
            "highest_version": "1.4.0",
        }),
        encoding="utf-8",
    )

    backup_package = backup_dir / "robot-app-1.0.0.bin"
    backup_package.write_text("dummy old version", encoding="utf-8")

    monkeypatch.setattr("client.app.core.VERSION_STATE_FILE", version_state_file)
    monkeypatch.setattr("client.app.core.INSTALLED_DIR", installed_dir)
    monkeypatch.setattr("client.app.core.BACKUP_DIR", backup_dir)

    restored_version = rollback()

    assert restored_version == "1.0.0"

    restored_file = installed_dir / "robot-app-1.0.0.bin"
    assert restored_file.exists()

    state_data = json.loads(version_state_file.read_text(encoding="utf-8"))
    assert state_data["current_version"] == "1.0.0"
