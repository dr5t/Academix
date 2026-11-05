from datetime import datetime, timezone
from pathlib import Path

from academic_engine.document_parser import parse_document
from academic_engine.docx_modifier import export_accepted_changes
from academic_engine.writing_models import SuggestionRecord, SuggestionStatus, WritingMode
from docx import Document


def test_export_applies_only_accepted_change_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    output = tmp_path / "revised.docx"
    document = Document()
    document.add_paragraph("Original paragraph.")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Table content"
    document.save(source)
    original = source.read_bytes()
    parsed = parse_document(source)
    suggestion = SuggestionRecord(
        id="s1",
        document_id="d1",
        element_id=parsed.elements[0].id,
        original_text="Original paragraph.",
        revised_text="Revised paragraph.",
        mode=WritingMode.ACADEMIC_RESEARCH,
        provider="fake",
        model="test",
        explanation="Clearer wording.",
        citation_preservation_status="preserved",
        created_at=datetime.now(timezone.utc),
    )
    export_accepted_changes(
        source, output, [suggestion.model_copy(update={"status": SuggestionStatus.ACCEPTED})]
    )
    assert source.read_bytes() == original
    revised = parse_document(output)
    assert revised.elements[0].original_content == "Revised paragraph."
    assert revised.elements[1].original_content == "Table content"
