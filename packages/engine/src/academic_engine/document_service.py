from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from academic_engine.config import Settings
from academic_engine.document_models import (
    DocumentAnalysis,
    DocumentDetail,
    DocumentRecord,
    DocumentUploadResult,
)
from academic_engine.document_parser import detect_kind, file_hash, parse_document
from academic_engine.exceptions import DocumentNotFoundError, DocumentValidationError
from academic_engine.storage import SQLiteStore


class DocumentService:
    def __init__(self, settings: Settings, store: SQLiteStore):
        self.settings = settings
        self.store = store

    def import_file(self, source: Path, filename: str) -> DocumentUploadResult:
        if not source.is_file():
            raise DocumentValidationError("Uploaded file is not available.")
        if source.stat().st_size > self.settings.max_upload_bytes:
            raise DocumentValidationError("The uploaded file exceeds the configured size limit.")
        kind = detect_kind(source)
        document_id = str(uuid4())
        destination = self.settings.documents_path / document_id / self._safe_filename(filename)
        destination.parent.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copyfile(source, destination)
            parsed = parse_document(destination)
            workspace = self._default_workspace()
            record = self.store.create_document(
                document_id=document_id,
                filename=destination.name,
                document_type=kind.value,
                source_path=destination,
                file_size=destination.stat().st_size,
                file_hash=file_hash(destination),
                workspace_id=workspace.id,
                status="ready",
                analysis=parsed.analysis.model_dump_json(),
            )
            return DocumentUploadResult.model_validate(record.model_dump())
        except Exception:
            shutil.rmtree(destination.parent, ignore_errors=True)
            raise

    def list_documents(self) -> list[DocumentRecord]:
        return self.store.list_documents()

    def get_document(self, document_id: str) -> DocumentDetail:
        record = self.store.get_document(document_id)
        if record is None:
            raise DocumentNotFoundError("Document was not found.")
        return record

    def get_analysis(self, document_id: str) -> DocumentAnalysis:
        detail = self.get_document(document_id)
        if detail.analysis is not None:
            return detail.analysis
        parsed = parse_document(self._path_for(detail))
        self.store.update_analysis(document_id, parsed.analysis.model_dump_json())
        return parsed.analysis

    def delete_document(self, document_id: str) -> None:
        detail = self.get_document(document_id)
        self.store.delete_document(document_id)
        shutil.rmtree(self._path_for(detail).parent, ignore_errors=True)

    def _default_workspace(self):
        workspaces = self.store.list_workspaces()
        return workspaces[0] if workspaces else self.store.create_workspace("Academic Workspace")

    def _path_for(self, detail: DocumentDetail) -> Path:
        path = self.settings.documents_path / detail.id / detail.filename
        try:
            path.resolve().relative_to(self.settings.documents_path.resolve())
        except ValueError as error:
            raise DocumentValidationError("Document path is outside local storage.") from error
        if not path.is_file():
            raise DocumentNotFoundError("Document source is no longer available.")
        return path

    @staticmethod
    def _safe_filename(filename: str) -> str:
        safe_name = Path(filename).name
        if not safe_name or safe_name in {".", ".."}:
            raise DocumentValidationError("Uploaded filename is invalid.")
        return safe_name[:200]
