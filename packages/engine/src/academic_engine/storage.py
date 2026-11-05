from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from academic_engine.exceptions import StorageError
from academic_engine.document_models import DocumentAnalysis, DocumentDetail, DocumentKind, DocumentRecord
from academic_engine.models import Workspace

SCHEMA_VERSION = 2


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
                        file_size INTEGER NOT NULL DEFAULT 0,
                        file_hash TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'ready',
                        analysis_json TEXT,
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
                elif row and row[0] < SCHEMA_VERSION:
                    columns = {
                        item[1]
                        for item in connection.execute("PRAGMA table_info(documents)").fetchall()
                    }
                    migrations = {
                        "file_size": "ALTER TABLE documents ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0",
                        "file_hash": "ALTER TABLE documents ADD COLUMN file_hash TEXT NOT NULL DEFAULT ''",
                        "status": "ALTER TABLE documents ADD COLUMN status TEXT NOT NULL DEFAULT 'ready'",
                        "analysis_json": "ALTER TABLE documents ADD COLUMN analysis_json TEXT",
                    }
                    for column, statement in migrations.items():
                        if column not in columns:
                            connection.execute(statement)
                    connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
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

    def create_document(
        self,
        document_id: str,
        filename: str,
        document_type: str,
        source_path: Path,
        file_size: int,
        file_hash: str,
        workspace_id: str,
        status: str,
        analysis: str,
    ) -> DocumentRecord:
        created_at = datetime.now(timezone.utc)
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO documents(
                        id, filename, document_type, source_path, workspace_id,
                        file_size, file_hash, status, analysis_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        filename,
                        document_type,
                        str(source_path),
                        workspace_id,
                        file_size,
                        file_hash,
                        status,
                        analysis,
                        created_at.isoformat(),
                    ),
                )
        except sqlite3.Error as error:
            raise StorageError(f"Unable to store document metadata: {error}") from error
        return DocumentRecord(
            id=document_id,
            filename=filename,
            document_type=DocumentKind(document_type),
            file_size=file_size,
            file_hash=file_hash,
            status=status,
            created_at=created_at,
            workspace_id=workspace_id,
        )

    def list_documents(self) -> list[DocumentRecord]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, filename, document_type, file_size, file_hash,
                       status, created_at, workspace_id
                FROM documents ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def get_document(self, document_id: str) -> DocumentDetail | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT id, filename, document_type, file_size, file_hash,
                       status, created_at, workspace_id, analysis_json
                FROM documents WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        analysis = DocumentAnalysis.model_validate_json(row[8]) if row[8] else None
        return DocumentDetail(
            **self._record_from_row(row[:8]).model_dump(),
            analysis=analysis,
        )

    def update_analysis(self, document_id: str, analysis: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE documents SET analysis_json = ?, status = 'ready' WHERE id = ?",
                (analysis, document_id),
            )

    def delete_document(self, document_id: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DELETE FROM processing_history WHERE document_id = ?", (document_id,))
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    @staticmethod
    def _record_from_row(row: tuple) -> DocumentRecord:
        return DocumentRecord(
            id=row[0],
            filename=row[1],
            document_type=DocumentKind(row[2]),
            file_size=row[3],
            file_hash=row[4],
            status=row[5],
            created_at=datetime.fromisoformat(row[6]),
            workspace_id=row[7],
        )
