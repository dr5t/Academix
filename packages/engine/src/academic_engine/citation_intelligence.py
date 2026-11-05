from __future__ import annotations

import re

from academic_engine.document_models import ElementType, ParsedDocument
from academic_engine.integrity_models import (
    CitationAnalysis,
    CitationRecord,
    CitationStyle,
    ReferenceRecord,
)

_APA = re.compile(
    r"\(([A-Z][A-Za-z'’-]+(?:\s+et al\.)?(?:\s*&\s*[A-Z][A-Za-z'’-]+)?),?\s+(19|20)\d{2}[a-z]?\)"
)
_IEEE = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
_DOI = re.compile(r"\b(?:https?://doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)
_YEAR = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")


def analyze_citations(
    document: ParsedDocument, requested_style: CitationStyle = CitationStyle.UNKNOWN
) -> CitationAnalysis:
    references_start = _references_start(document)
    references = _references(document, references_start)
    body = (
        document.elements[:references_start] if references_start is not None else document.elements
    )
    citations: list[CitationRecord] = []
    for element in body:
        citations.extend(_citations_in(element.original_content, element.id, requested_style))
    style = (
        requested_style
        if requested_style is not CitationStyle.UNKNOWN
        else _detect_style(citations)
    )
    if style is not CitationStyle.UNKNOWN:
        citations = [item.model_copy(update={"style": style}) for item in citations]
    reference_keys = {_reference_key(reference) for reference in references}
    cited_keys = {_citation_key(citation) for citation in citations}
    missing = sorted(key for key in cited_keys if key and key not in reference_keys)
    used_reference_keys = {key for key in cited_keys if key}
    unreferenced = [
        reference.raw_text
        for reference in references
        if _reference_key(reference) not in used_reference_keys
    ]
    dois = sorted({reference.doi for reference in references if reference.doi})
    warnings = _consistency_warnings(citations, references, style)
    return CitationAnalysis(
        detected_style=style,
        citations=citations,
        references=references,
        missing_references=missing,
        unreferenced_entries=unreferenced,
        doi_values=dois,
        consistency_warnings=warnings,
    )


def _references_start(document: ParsedDocument) -> int | None:
    for index, element in enumerate(document.elements):
        if (
            element.element_type is ElementType.HEADING
            and element.original_content.strip().lower()
            in {
                "references",
                "bibliography",
                "works cited",
                "references and bibliography",
            }
        ):
            return index + 1
    return None


def _references(document: ParsedDocument, start: int | None) -> list[ReferenceRecord]:
    if start is None:
        return []
    return [
        ReferenceRecord(
            raw_text=element.original_content,
            authors=_authors(element.original_content),
            year=_YEAR.search(element.original_content).group(0)
            if _YEAR.search(element.original_content)
            else None,
            title=_reference_title(element.original_content),
            doi=_doi(element.original_content),
            element_id=element.id,
        )
        for element in document.elements[start:]
        if element.element_type in {ElementType.PARAGRAPH, ElementType.HEADING}
        and element.original_content.strip()
    ]


def _citations_in(text: str, element_id: str, style: CitationStyle) -> list[CitationRecord]:
    records: list[CitationRecord] = []
    if style in {
        CitationStyle.UNKNOWN,
        CitationStyle.APA,
        CitationStyle.HARVARD,
        CitationStyle.CHICAGO,
    }:
        for match in _APA.finditer(text):
            records.append(
                CitationRecord(
                    raw_text=match.group(0),
                    style=style if style is not CitationStyle.UNKNOWN else CitationStyle.APA,
                    authors=[match.group(1)],
                    year=_YEAR.search(match.group(0)).group(0),
                    reference_key=match.group(1).split()[0].lower(),
                    element_id=element_id,
                )
            )
    if style in {CitationStyle.UNKNOWN, CitationStyle.IEEE}:
        for match in _IEEE.finditer(text):
            for number in re.findall(r"\d+", match.group(1)):
                records.append(
                    CitationRecord(
                        raw_text=match.group(0),
                        style=CitationStyle.IEEE,
                        reference_key=number,
                        element_id=element_id,
                    )
                )
    return records


def _detect_style(citations: list[CitationRecord]) -> CitationStyle:
    if any(item.style is CitationStyle.IEEE for item in citations):
        return CitationStyle.IEEE
    if citations:
        return CitationStyle.APA
    return CitationStyle.UNKNOWN


def _authors(text: str) -> list[str]:
    prefix = text.split("(", 1)[0].strip()
    return [prefix.split(",")[0].strip()] if prefix else []


def _reference_key(reference: ReferenceRecord) -> str | None:
    if reference.authors and reference.authors[0]:
        return reference.authors[0].split()[-1].lower().rstrip(".")
    return None


def _citation_key(citation: CitationRecord) -> str | None:
    return citation.reference_key.lower() if citation.reference_key else None


def _doi(text: str) -> str | None:
    match = _DOI.search(text)
    return match.group(1).rstrip(".,)") if match else None


def _reference_title(text: str) -> str | None:
    parts = [part.strip() for part in text.split(".") if part.strip()]
    return parts[1] if len(parts) > 1 else None


def _consistency_warnings(
    citations: list[CitationRecord], references: list[ReferenceRecord], style: CitationStyle
) -> list[str]:
    warnings = []
    if style is CitationStyle.UNKNOWN and references:
        warnings.append("Citation style could not be determined confidently.")
    if citations and not references:
        warnings.append("In-text citations were detected but no bibliography section was found.")
    if len({item.style for item in citations}) > 1:
        warnings.append("Multiple in-text citation conventions appear in the same document.")
    if any(
        reference.doi and reference.doi.lower().startswith("10.") is False
        for reference in references
    ):
        warnings.append("One or more DOI values do not match the expected DOI format.")
    return warnings
