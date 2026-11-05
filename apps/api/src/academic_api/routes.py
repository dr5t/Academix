from pathlib import Path
from uuid import uuid4

from academic_engine.config import get_settings
from academic_engine.document_models import (
    DocumentAnalysis,
    DocumentDetail,
    DocumentRecord,
    DocumentUploadResult,
)
from academic_engine.document_service import DocumentService
from academic_engine.exceptions import DocumentNotFoundError
from academic_engine.models import ProviderMetadata
from academic_engine.providers import provider_metadata
from academic_engine.storage import SQLiteStore
from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter()


def document_service() -> DocumentService:
    settings = get_settings()
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    return DocumentService(settings, store)


@router.get("/providers", response_model=list[ProviderMetadata], tags=["providers"])
def providers() -> list[ProviderMetadata]:
    return list(provider_metadata(get_settings()))


@router.post(
    "/documents",
    response_model=DocumentUploadResult,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResult:
    settings = get_settings()
    settings.ensure_directories()
    suffix = Path(file.filename or "").suffix.lower()
    temporary_path = settings.temp_path / f"{uuid4().hex}{suffix}"
    try:
        size = 0
        with temporary_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="Uploaded file is too large.")
                target.write(chunk)
        return document_service().import_file(temporary_path, file.filename or "")
    finally:
        temporary_path.unlink(missing_ok=True)


@router.get("/documents", response_model=list[DocumentRecord], tags=["documents"])
def list_documents() -> list[DocumentRecord]:
    return document_service().list_documents()


@router.get("/documents/{document_id}", response_model=DocumentDetail, tags=["documents"])
def get_document(document_id: str) -> DocumentDetail:
    try:
        return document_service().get_document(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/documents/{document_id}/analysis",
    response_model=DocumentAnalysis,
    tags=["documents"],
)
def analyze_document(document_id: str) -> DocumentAnalysis:
    try:
        return document_service().get_analysis(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["documents"],
)
def delete_document(document_id: str) -> None:
    try:
        document_service().delete_document(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
