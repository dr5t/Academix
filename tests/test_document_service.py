from pathlib import Path

from academic_engine.config import Settings
from academic_engine.document_service import DocumentService
from academic_engine.storage import SQLiteStore
from docx import Document


def test_import_keeps_original_and_persists_metadata(tmp_path: Path) -> None:
    source = tmp_path / "paper.docx"
    document = Document()
    document.add_heading("A Title", level=1)
    document.add_paragraph("Original paragraph.")
    document.save(source)
    original_bytes = source.read_bytes()
    settings = Settings(
        database_path=tmp_path / "db.sqlite3",
        documents_path=tmp_path / "documents",
        temp_path=tmp_path / "temp",
    )
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    result = DocumentService(settings, store).import_file(source, source.name)
    assert source.read_bytes() == original_bytes
    assert result.status == "ready"
    stored = store.get_document(result.id)
    assert stored is not None
    assert stored.file_hash == result.file_hash
    assert stored.analysis is not None


def test_invalid_docx_is_rejected(tmp_path: Path) -> None:
    from academic_engine.document_parser import detect_kind
    from academic_engine.exceptions import DocumentValidationError

    path = tmp_path / "broken.docx"
    path.write_bytes(b"not a zip package")
    try:
        detect_kind(path)
    except DocumentValidationError:
        pass
    else:
        raise AssertionError("Corrupt DOCX was accepted")
