import base64
from pathlib import Path

from academic_engine.document_models import DocumentKind, ElementType
from academic_engine.document_parser import file_hash, parse_document
from docx import Document
from docx.shared import Inches, Pt

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def create_sample_docx(path: Path) -> None:
    document = Document()
    document.core_properties.title = "Preservation Sample"
    section = document.sections[0]
    section.top_margin = Inches(1)
    document.add_heading("Research Overview", level=1)
    paragraph = document.add_paragraph()
    paragraph.style = "Normal"
    first = paragraph.add_run("Bold context")
    first.bold = True
    second = paragraph.add_run(" and italic evidence.")
    second.italic = True
    first.font.name = "Arial"
    first.font.size = Pt(11)
    document.add_paragraph("1. Numbered research item", style="List Number")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Measure"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Sample"
    table.cell(1, 1).text = "42"
    document.add_page_break()
    document.add_heading("References", level=1)
    document.add_paragraph("(Smith, 2024)")
    image_path = path.with_suffix(".png")
    image_path.write_bytes(PNG_1X1)
    document.add_picture(str(image_path), width=Inches(1))
    document.sections[0].header.paragraphs[0].text = "Academic Humanizer"
    document.sections[0].footer.paragraphs[0].text = "Confidential"
    document.save(path)


def test_docx_parser_preserves_order_and_structure(tmp_path: Path) -> None:
    path = tmp_path / "sample.docx"
    create_sample_docx(path)
    parsed = parse_document(path)
    types = [element.element_type for element in parsed.elements]
    assert parsed.document_type is DocumentKind.DOCX
    assert parsed.title == "Preservation Sample"
    assert ElementType.HEADING in types
    assert ElementType.TABLE in types
    assert parsed.analysis.reference_section_detected is True
    assert parsed.analysis.citation_patterns == ["(Smith, 2024)"]
    assert parsed.elements[1].text_runs[0].bold is True
    assert parsed.elements[1].text_runs[1].italic is True
    assert parsed.sections[0].margin_top_twips is not None


def test_file_hash_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("unchanged", encoding="utf-8")
    first = file_hash(path)
    parsed = parse_document(path)
    assert file_hash(path) == first == parsed.source_hash


def test_pdf_parser_reports_image_only_pages(tmp_path: Path) -> None:
    import fitz

    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(0, 0, 20, 20), stream=PNG_1X1)
    document.save(path)
    document.close()
    parsed = parse_document(path)
    assert parsed.document_type is DocumentKind.PDF
    assert parsed.analysis.page_count == 1
    assert "OCR may be required" in parsed.analysis.extraction_issues[0]
