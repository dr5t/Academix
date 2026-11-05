from pathlib import Path

from docx import Document

from academic_engine.citation_intelligence import analyze_citations
from academic_engine.document_parser import parse_document
from academic_engine.similarity import compare_documents, find_internal_repetition


def _document(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    document.add_heading("Research", level=1)
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.add_heading("References", level=1)
    document.add_paragraph("Doe, J. (2022). A useful study. Journal of Testing. https://doi.org/10.1234/example")
    document.save(path)


def test_citation_analysis_matches_reference_and_extracts_doi(tmp_path: Path) -> None:
    path = tmp_path / "paper.docx"
    _document(path, ["The result is reliable (Doe, 2022)."])
    analysis = analyze_citations(parse_document(path))
    assert analysis.detected_style.value == "apa7"
    assert analysis.missing_references == []
    assert analysis.doi_values == ["10.1234/example"]


def test_similarity_detects_internal_repetition_and_explicit_source_overlap(tmp_path: Path) -> None:
    target_path = tmp_path / "target.docx"
    source_path = tmp_path / "source.docx"
    repeated = "This paragraph contains a repeated academic statement with enough words for comparison."
    _document(target_path, [repeated, repeated])
    _document(source_path, [repeated])
    target = parse_document(target_path)
    source = parse_document(source_path)
    assert find_internal_repetition(target)
    assert compare_documents(target, [("source-doc", source)])
