from __future__ import annotations

import hashlib
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

import fitz
from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from academic_engine.document_models import (
    DocumentAnalysis,
    DocumentElement,
    DocumentKind,
    DocumentSection,
    ElementType,
    ParsedDocument,
    StyleInfo,
    TextRun,
)
from academic_engine.exceptions import DocumentValidationError

_CITATION_PATTERNS = (
    r"\([A-Z][A-Za-z-]+(?:\s+et al\.)?,?\s+\d{4}[a-z]?\)",
    r"\[[0-9]+(?:\s*,\s*[0-9]+)*\]",
)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_kind(path: Path) -> DocumentKind:
    suffix = path.suffix.lower()
    try:
        if suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise DocumentValidationError("The DOCX package is missing its document body.")
                if archive.testzip() is not None:
                    raise DocumentValidationError("The DOCX package is corrupted.")
            return DocumentKind.DOCX
        if suffix == ".pdf":
            with fitz.open(path) as pdf:
                if pdf.page_count == 0:
                    raise DocumentValidationError("The PDF contains no pages.")
            return DocumentKind.PDF
        if suffix == ".txt":
            return DocumentKind.TXT
    except (OSError, zipfile.BadZipFile, fitz.FileDataError) as error:
        raise DocumentValidationError(f"Unable to validate document: {error}") from error
    raise DocumentValidationError("Unsupported document type. Use DOCX, PDF, or TXT.")


def parse_document(path: Path) -> ParsedDocument:
    kind = detect_kind(path)
    source_hash = file_hash(path)
    if kind is DocumentKind.DOCX:
        return _parse_docx(path, source_hash)
    if kind is DocumentKind.PDF:
        return _parse_pdf(path, source_hash)
    return _parse_text(path, source_hash)


def _parse_docx(path: Path, source_hash: str) -> ParsedDocument:
    try:
        document = Document(path)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise DocumentValidationError(f"Unable to read DOCX: {error}") from error

    elements: list[DocumentElement] = []
    position = 0
    references: list[str] = []
    heading_structure: list[str] = []
    title: str | None = document.core_properties.title or None
    table_count = 0
    image_count = 0
    for block in _iter_body_blocks(document):
        if isinstance(block, Paragraph):
            element = _paragraph_element(block, position)
            if element.element_type is ElementType.HEADING:
                heading_structure.append(element.original_content)
                if title is None:
                    title = element.original_content
                if element.original_content.strip().lower() in {"references", "bibliography"}:
                    references.append(element.original_content)
            image_count += len(element.relationships)
        else:
            element = _table_element(block, position)
            table_count += 1
            image_count += len(element.relationships)
        elements.append(element)
        position += 1

    sections = [
        DocumentSection(
            index=index,
            page_width_twips=section.page_width,
            page_height_twips=section.page_height,
            margin_top_twips=section.top_margin,
            margin_bottom_twips=section.bottom_margin,
            margin_left_twips=section.left_margin,
            margin_right_twips=section.right_margin,
            start_type=str(section.start_type),
        )
        for index, section in enumerate(document.sections)
    ]
    unsupported = []
    if document.element.body.xpath(".//w:footnoteReference"):
        unsupported.append("Footnote content requires a lower-level OOXML reader.")
    if document.element.body.xpath(".//w:endnoteReference"):
        unsupported.append("Endnote content requires a lower-level OOXML reader.")
    citations = _find_citations(" ".join(element.original_content for element in elements))
    analysis = DocumentAnalysis(
        document_type=DocumentKind.DOCX,
        title=title,
        paragraph_count=sum(
            element.element_type in {ElementType.PARAGRAPH, ElementType.HEADING}
            for element in elements
        ),
        heading_count=len(heading_structure),
        heading_structure=heading_structure,
        table_count=table_count,
        image_count=image_count,
        reference_section_detected=bool(references),
        citation_patterns=citations,
        unsupported_elements=unsupported,
        facts=[
            f"Extracted {len(elements)} ordered body elements.",
            f"Detected {len(document.sections)} document section(s).",
        ],
        inferences=["The first level-one heading is treated as the document title."]
        if title
        else [],
    )
    return ParsedDocument(
        document_type=DocumentKind.DOCX,
        title=title,
        elements=elements,
        sections=sections,
        analysis=analysis,
        source_hash=source_hash,
        file_size=path.stat().st_size,
    )


def _iter_body_blocks(document: DocumentObject) -> Iterable[Paragraph | Table]:
    parent = document.element.body
    for child in parent.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _paragraph_element(paragraph: Paragraph, position: int) -> DocumentElement:
    style_name = paragraph.style.name if paragraph.style else None
    heading_level = _heading_level(style_name)
    element_type = ElementType.HEADING if heading_level else ElementType.PARAGRAPH
    relationships = [
        relation_id for relation_id in paragraph._p.xpath(".//a:blip/@r:embed") if relation_id
    ]
    runs = [
        TextRun(
            text=run.text,
            bold=run.bold,
            italic=run.italic,
            underline=run.underline,
            font_name=run.font.name,
            font_size_pt=run.font.size.pt if run.font.size else None,
        )
        for run in paragraph.runs
    ]
    if paragraph._p.xpath(".//w:br"):
        element_metadata = {"contains_break": True}
    else:
        element_metadata = {}
    return DocumentElement(
        id=f"p-{uuid4().hex}",
        element_type=element_type,
        position=position,
        original_content=paragraph.text,
        text_runs=runs,
        style=StyleInfo(name=style_name, heading_level=heading_level),
        relationships=relationships,
        metadata=element_metadata,
    )


def _table_element(table: Table, position: int) -> DocumentElement:
    rows = [" | ".join(cell.text for cell in row.cells) for row in table.rows]
    relationships = [
        relation_id for relation_id in table._tbl.xpath(".//a:blip/@r:embed") if relation_id
    ]
    return DocumentElement(
        id=f"tbl-{uuid4().hex}",
        element_type=ElementType.TABLE,
        position=position,
        original_content="\n".join(rows),
        relationships=relationships,
        metadata={"row_count": len(table.rows), "column_count": len(table.columns)},
    )


def _heading_level(style_name: str | None) -> int | None:
    if not style_name:
        return None
    match = re.match(r"Heading ([1-9])$", style_name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _parse_pdf(path: Path, source_hash: str) -> ParsedDocument:
    try:
        pdf = fitz.open(path)
    except (OSError, fitz.FileDataError) as error:
        raise DocumentValidationError(f"Unable to read PDF: {error}") from error
    elements: list[DocumentElement] = []
    empty_pages = []
    for page_index, page in enumerate(pdf):
        text = page.get_text("text").strip()
        if not text:
            empty_pages.append(
                f"Page {page_index + 1} has no extractable text; OCR may be required."
            )
        blocks = page.get_text("blocks")
        elements.append(
            DocumentElement(
                id=f"page-{uuid4().hex}",
                element_type=ElementType.PARAGRAPH,
                position=page_index,
                original_content=text,
                metadata={
                    "page_number": page_index + 1,
                    "text_block_count": len(blocks),
                    "image_only": not bool(text) and bool(page.get_images(full=True)),
                },
            )
        )
    metadata = pdf.metadata or {}
    title = metadata.get("title") or None
    image_only = bool(empty_pages)
    analysis = DocumentAnalysis(
        document_type=DocumentKind.PDF,
        title=title,
        page_count=pdf.page_count,
        paragraph_count=sum(bool(element.original_content) for element in elements),
        extraction_issues=empty_pages,
        facts=[f"Extracted {pdf.page_count} PDF page(s)."],
        inferences=["OCR may be required for pages without an extractable text layer."]
        if image_only
        else [],
    )
    pdf.close()
    return ParsedDocument(
        document_type=DocumentKind.PDF,
        title=title,
        elements=elements,
        analysis=analysis,
        source_hash=source_hash,
        file_size=path.stat().st_size,
    )


def _parse_text(path: Path, source_hash: str) -> ParsedDocument:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise DocumentValidationError(f"Unable to read text document: {error}") from error
    elements = [
        DocumentElement(
            id=f"p-{uuid4().hex}",
            element_type=ElementType.PARAGRAPH,
            position=index,
            original_content=paragraph,
        )
        for index, paragraph in enumerate(content.splitlines())
    ]
    analysis = DocumentAnalysis(
        document_type=DocumentKind.TXT,
        paragraph_count=len(elements),
        citation_patterns=_find_citations(content),
        facts=[f"Extracted {len(elements)} text line(s)."],
    )
    return ParsedDocument(
        document_type=DocumentKind.TXT,
        elements=elements,
        analysis=analysis,
        source_hash=source_hash,
        file_size=path.stat().st_size,
    )


def _find_citations(text: str) -> list[str]:
    return sorted(
        {match.group(0) for pattern in _CITATION_PATTERNS for match in re.finditer(pattern, text)}
    )
