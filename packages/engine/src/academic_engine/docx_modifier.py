from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document

from academic_engine.document_parser import parse_document
from academic_engine.exceptions import DocumentValidationError
from academic_engine.writing_models import SuggestionRecord, SuggestionStatus


def export_accepted_changes(source: Path, destination: Path, suggestions: list[SuggestionRecord]) -> None:
    accepted = {item.element_id: item for item in suggestions if item.status is SuggestionStatus.ACCEPTED}
    if source.suffix.lower() != ".docx":
        raise DocumentValidationError("Only DOCX export is supported for accepted changes.")
    parsed = parse_document(source)
    for element in parsed.elements:
        proposal = accepted.get(element.id)
        if proposal and proposal.original_text != element.original_content:
            raise DocumentValidationError("A suggestion no longer matches the original document.")
    document = Document(source)
    paragraphs = list(document.paragraphs)
    for element in parsed.elements:
        proposal = accepted.get(element.id)
        if not proposal or not element.id.startswith("p-"):
            continue
        paragraph_index = int(element.id[2:])
        if paragraph_index >= len(paragraphs):
            raise DocumentValidationError("Document structure changed since analysis.")
        paragraph = paragraphs[paragraph_index]
        if len(paragraph.runs) > 1 and not _same_formatting(paragraph):
            raise DocumentValidationError(
                "This paragraph uses multiple formatting runs and cannot be safely rewritten."
            )
        if paragraph.runs:
            paragraph.runs[0].text = proposal.revised_text
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.add_run(proposal.revised_text)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination)


def _same_formatting(paragraph) -> bool:
    first = paragraph.runs[0]
    return all(
        (run.bold, run.italic, run.underline, run.font.name, run.font.size)
        == (first.bold, first.italic, first.underline, first.font.name, first.font.size)
        for run in paragraph.runs[1:]
    )
