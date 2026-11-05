from pathlib import Path
from uuid import uuid4

from academic_engine.config import get_settings
from academic_engine.document_models import (
    DocumentAnalysis,
    DocumentDetail,
    DocumentRecord,
    DocumentUploadResult,
    DocumentElement,
)
from academic_engine.document_parser import parse_document
from academic_engine.document_service import DocumentService
from academic_engine.exceptions import DocumentNotFoundError
from academic_engine.models import ProviderMetadata
from academic_engine.providers import provider_metadata
from academic_engine.storage import SQLiteStore
from academic_engine.writing_models import (
    AnalyzeWritingRequest,
    SuggestionRecord,
    SuggestionRequest,
    SuggestionStatus,
)
from academic_engine.writing_service import WritingService
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

router = APIRouter()


def document_service() -> DocumentService:
    settings = get_settings()
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    return DocumentService(settings, store)


def writing_service() -> WritingService:
    settings = get_settings()
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    return WritingService(settings, store, document_service())


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


@router.post(
    "/documents/{document_id}/analyze-writing",
    response_model=list[SuggestionRecord],
    tags=["writing"],
)
def analyze_writing(document_id: str, request: AnalyzeWritingRequest) -> list[SuggestionRecord]:
    service = writing_service()
    return [
        service.create_suggestion(
            document_id,
            SuggestionRequest(
                element_id=element_id,
                mode=request.mode,
                provider=request.provider,
                model=request.model,
                generation=request.generation,
            ),
        )
        for element_id in request.element_ids
    ]


@router.post(
    "/documents/{document_id}/suggestions",
    response_model=SuggestionRecord,
    tags=["writing"],
)
def create_suggestion(document_id: str, request: SuggestionRequest) -> SuggestionRecord:
    return writing_service().create_suggestion(document_id, request)


@router.get(
    "/documents/{document_id}/suggestions",
    response_model=list[SuggestionRecord],
    tags=["writing"],
)
def list_suggestions(document_id: str) -> list[SuggestionRecord]:
    return writing_service().suggestions(document_id)


@router.get(
    "/documents/{document_id}/suggestions/{suggestion_id}",
    response_model=SuggestionRecord,
    tags=["writing"],
)
def get_suggestion(document_id: str, suggestion_id: str) -> SuggestionRecord:
    return writing_service().suggestion(document_id, suggestion_id)


@router.post(
    "/documents/{document_id}/suggestions/{suggestion_id}/accept",
    response_model=SuggestionRecord,
    tags=["writing"],
)
def accept_suggestion(document_id: str, suggestion_id: str) -> SuggestionRecord:
    return writing_service().set_status(document_id, suggestion_id, SuggestionStatus.ACCEPTED)


@router.post(
    "/documents/{document_id}/suggestions/{suggestion_id}/reject",
    response_model=SuggestionRecord,
    tags=["writing"],
)
def reject_suggestion(document_id: str, suggestion_id: str) -> SuggestionRecord:
    return writing_service().set_status(document_id, suggestion_id, SuggestionStatus.REJECTED)


@router.post(
    "/documents/{document_id}/suggestions/{suggestion_id}/regenerate",
    response_model=SuggestionRecord,
    tags=["writing"],
)
def regenerate_suggestion(document_id: str, suggestion_id: str) -> SuggestionRecord:
    return writing_service().regenerate(document_id, suggestion_id)


@router.post("/documents/{document_id}/export", response_class=FileResponse, tags=["writing"])
def export_document(document_id: str) -> FileResponse:
    service = writing_service()
    detail = service.documents.get_document(document_id)
    source = service.documents._path_for(detail)
    output = source.parent / f"{source.stem}.revised.docx"
    from academic_engine.docx_modifier import export_accepted_changes

    export_accepted_changes(source, output, service.suggestions(document_id))
    return FileResponse(output, filename=output.name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


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


@router.get(
    "/documents/{document_id}/elements",
    response_model=list[DocumentElement],
    tags=["documents"],
)
def document_elements(document_id: str) -> list[DocumentElement]:
    service = document_service()
    detail = service.get_document(document_id)
    return parse_document(service._path_for(detail)).elements


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
