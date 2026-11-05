import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from academic_engine.exceptions import StorageError
from academic_engine.models import Workspace

SCHEMA_VERSION = 1


class SQLiteStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def initialize(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS workspaces (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        document_type TEXT NOT NULL,
                        source_path TEXT NOT NULL,
                        workspace_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                    );
                    CREATE TABLE IF NOT EXISTS processing_history (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        mode TEXT,
                        provider TEXT,
                        output_path TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(document_id) REFERENCES documents(id)
                    );
                    CREATE TABLE IF NOT EXISTS provider_settings (
                        provider TEXT PRIMARY KEY,
                        model TEXT,
                        configured INTEGER NOT NULL DEFAULT 0,
                        is_default INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                row = connection.execute("SELECT COUNT(*) FROM schema_version").fetchone()
                if row and row[0] == 0:
                    connection.execute(
                        "INSERT INTO schema_version(version) VALUES (?)",
                        (SCHEMA_VERSION,),
                    )
        except sqlite3.Error as error:
            raise StorageError(f"Unable to initialize local database: {error}") from error

    def create_workspace(self, name: str) -> Workspace:
        workspace = Workspace(id=str(uuid4()), name=name, created_at=datetime.now(timezone.utc))
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO workspaces(id, name, created_at) VALUES (?, ?, ?)",
                (workspace.id, workspace.name, workspace.created_at.isoformat()),
            )
        return workspace

    def list_workspaces(self) -> list[Workspace]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT id, name, created_at FROM workspaces ORDER BY created_at"
            ).fetchall()
        return [
            Workspace(id=row[0], name=row[1], created_at=datetime.fromisoformat(row[2]))
            for row in rows
        ]

    def schema_version(self) -> int:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        return int(row[0]) if row else 0
