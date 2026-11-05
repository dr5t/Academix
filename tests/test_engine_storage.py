from pathlib import Path

from academic_engine.storage import SQLiteStore


def test_storage_initializes_and_creates_workspace(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "workspace.sqlite3")
    store.initialize()
    workspace = store.create_workspace("Test Workspace")
    assert store.schema_version() == 3
    assert store.list_workspaces()[0].id == workspace.id
