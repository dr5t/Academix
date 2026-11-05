from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from academic_engine.document_models import (
    DocumentAnalysis,
    DocumentDetail,
    DocumentKind,
    DocumentRecord,
)
from academic_engine.exceptions import StorageError
from academic_engine.models import Workspace
from academic_engine.writing_models import SuggestionRecord, SuggestionStatus, WritingMode
from academic_engine.integrity_models import (
    FindingStatus,
    IntegrityFinding,
    IntegrityReport,
)

SCHEMA_VERSION = 4


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
                        integrity_json TEXT,
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
                    CREATE TABLE IF NOT EXISTS suggestions (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        element_id TEXT NOT NULL,
                        original_text TEXT NOT NULL,
                        revised_text TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        changes_json TEXT NOT NULL,
                        explanation TEXT NOT NULL,
                        meaning_change_warning TEXT,
                        citation_preservation_status TEXT NOT NULL,
                        validation_warnings_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(document_id) REFERENCES documents(id)
                    );
                    CREATE TABLE IF NOT EXISTS integrity_findings (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        element_id TEXT,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        explanation TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        recommended_action TEXT NOT NULL,
                        evidence_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        dismissal_reason TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(document_id) REFERENCES documents(id)
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
                        "file_size": (
                            "ALTER TABLE documents ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0"
                        ),
                        "file_hash": (
                            "ALTER TABLE documents ADD COLUMN file_hash TEXT NOT NULL DEFAULT ''"
                        ),
                        "status": (
                            "ALTER TABLE documents ADD COLUMN status TEXT NOT NULL DEFAULT 'ready'"
                        ),
                        "analysis_json": "ALTER TABLE documents ADD COLUMN analysis_json TEXT",
                        "integrity_json": "ALTER TABLE documents ADD COLUMN integrity_json TEXT",
                    }
                    for column, statement in migrations.items():
                        if column not in columns:
                            connection.execute(statement)
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS integrity_findings (
                            id TEXT PRIMARY KEY,
                            document_id TEXT NOT NULL,
                            element_id TEXT,
                            category TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            explanation TEXT NOT NULL,
                            confidence REAL NOT NULL,
                            recommended_action TEXT NOT NULL,
                            evidence_json TEXT NOT NULL,
                            status TEXT NOT NULL,
                            dismissal_reason TEXT,
                            created_at TEXT NOT NULL,
                            FOREIGN KEY(document_id) REFERENCES documents(id)
                        )
                        """
                    )
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

    def update_integrity(self, document_id: str, report: IntegrityReport) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE documents SET integrity_json = ? WHERE id = ?",
                (report.model_dump_json(), document_id),
            )

    def get_integrity(self, document_id: str) -> IntegrityReport | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT integrity_json FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
        return IntegrityReport.model_validate_json(row[0]) if row and row[0] else None

    def create_integrity_finding(self, finding: IntegrityFinding) -> IntegrityFinding:
        import json

        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO integrity_findings(
                    id, document_id, element_id, category, severity, explanation,
                    confidence, recommended_action, evidence_json, status,
                    dismissal_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding.id,
                    finding.document_id,
                    finding.element_id,
                    finding.category,
                    finding.severity,
                    finding.explanation,
                    finding.confidence,
                    finding.recommended_action,
                    json.dumps(finding.evidence),
                    finding.status.value,
                    finding.dismissal_reason,
                    finding.created_at.isoformat(),
                ),
            )
        return finding

    def list_integrity_findings(self, document_id: str) -> list[IntegrityFinding]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM integrity_findings WHERE document_id = ? ORDER BY created_at DESC",
                (document_id,),
            ).fetchall()
        return [self._finding_from_row(row) for row in rows]

    def get_integrity_finding(self, finding_id: str) -> IntegrityFinding | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM integrity_findings WHERE id = ?", (finding_id,)
            ).fetchone()
        return self._finding_from_row(row) if row else None

    def update_integrity_finding(
        self, finding_id: str, status: FindingStatus, dismissal_reason: str | None
    ) -> IntegrityFinding | None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE integrity_findings SET status = ?, dismissal_reason = ? WHERE id = ?",
                (status.value, dismissal_reason, finding_id),
            )
        return self.get_integrity_finding(finding_id)

    @staticmethod
    def _finding_from_row(row: tuple) -> IntegrityFinding:
        import json

        return IntegrityFinding(
            id=row[0],
            document_id=row[1],
            element_id=row[2],
            category=row[3],
            severity=row[4],
            explanation=row[5],
            confidence=row[6],
            recommended_action=row[7],
            evidence=json.loads(row[8]),
            status=FindingStatus(row[9]),
            dismissal_reason=row[10],
            created_at=datetime.fromisoformat(row[11]),
        )

    def delete_document(self, document_id: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "DELETE FROM processing_history WHERE document_id = ?",
                (document_id,),
            )
            connection.execute(
                "DELETE FROM integrity_findings WHERE document_id = ?",
                (document_id,),
            )
            connection.execute(
                "DELETE FROM suggestions WHERE document_id = ?",
                (document_id,),
            )
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

    def create_suggestion(self, suggestion: SuggestionRecord) -> SuggestionRecord:
        import json

        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO suggestions(
                        id, document_id, element_id, original_text, revised_text, mode,
                        provider, model, changes_json, explanation, meaning_change_warning,
                        citation_preservation_status, validation_warnings_json, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        suggestion.id,
                        suggestion.document_id,
                        suggestion.element_id,
                        suggestion.original_text,
                        suggestion.revised_text,
                        suggestion.mode.value,
                        suggestion.provider,
                        suggestion.model,
                        json.dumps(suggestion.changes_made),
                        suggestion.explanation,
                        suggestion.meaning_change_warning,
                        suggestion.citation_preservation_status,
                        json.dumps(suggestion.validation_warnings),
                        suggestion.status.value,
                        suggestion.created_at.isoformat(),
                    ),
                )
        except sqlite3.Error as error:
            raise StorageError(f"Unable to store writing suggestion: {error}") from error
        return suggestion

    def list_suggestions(self, document_id: str) -> list[SuggestionRecord]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM suggestions WHERE document_id = ? ORDER BY created_at DESC",
                (document_id,),
            ).fetchall()
        return [self._suggestion_from_row(row) for row in rows]

    def get_suggestion(self, suggestion_id: str) -> SuggestionRecord | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM suggestions WHERE id = ?", (suggestion_id,)
            ).fetchone()
        return self._suggestion_from_row(row) if row else None

    def update_suggestion_status(
        self, suggestion_id: str, status: SuggestionStatus
    ) -> SuggestionRecord | None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE suggestions SET status = ? WHERE id = ?",
                (status.value, suggestion_id),
            )
        return self.get_suggestion(suggestion_id)

    @staticmethod
    def _suggestion_from_row(row: tuple) -> SuggestionRecord:
        import json

        return SuggestionRecord(
            id=row[0],
            document_id=row[1],
            element_id=row[2],
            original_text=row[3],
            revised_text=row[4],
            mode=WritingMode(row[5]),
            provider=row[6],
            model=row[7],
            changes_made=json.loads(row[8]),
            explanation=row[9],
            meaning_change_warning=row[10],
            citation_preservation_status=row[11],
            validation_warnings=json.loads(row[12]),
            status=SuggestionStatus(row[13]),
            created_at=datetime.fromisoformat(row[14]),
        )
