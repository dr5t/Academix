from __future__ import annotations

import re
from difflib import SequenceMatcher

from academic_engine.document_models import ElementType, ParsedDocument
from academic_engine.integrity_models import SimilarityMatch


def compare_documents(
    target: ParsedDocument, sources: list[tuple[str, ParsedDocument]]
) -> list[SimilarityMatch]:
    matches: list[SimilarityMatch] = []
    source_elements = [
        (source_id, element)
        for source_id, document in sources
        for element in document.elements
        if element.element_type in {ElementType.PARAGRAPH, ElementType.HEADING}
        and len(_tokens(element.original_content)) >= 8
    ]
    for target_element in target.elements:
        if target_element.element_type not in {ElementType.PARAGRAPH, ElementType.HEADING}:
            continue
        target_tokens = _tokens(target_element.original_content)
        if len(target_tokens) < 8:
            continue
        best: tuple[float, str, str, str] | None = None
        for source_id, source_element in source_elements:
            ratio = SequenceMatcher(
                None, target_tokens, _tokens(source_element.original_content)
            ).ratio()
            if best is None or ratio > best[0]:
                best = (ratio, source_id, source_element.id, source_element.original_content)
        if best and best[0] >= 0.72:
            matches.append(
                SimilarityMatch(
                    source_document_id=best[1],
                    source_name=best[1],
                    target_element_id=target_element.id,
                    source_location=best[2],
                    matching_text=best[3],
                    similarity=round(best[0], 3),
                    attribution_present=_has_attribution(target_element.original_content),
                )
            )
    return matches


def find_internal_repetition(document: ParsedDocument) -> list[SimilarityMatch]:
    elements = [
        element
        for element in document.elements
        if element.element_type in {ElementType.PARAGRAPH, ElementType.HEADING}
        and len(_tokens(element.original_content)) >= 8
    ]
    matches = []
    for index, left in enumerate(elements):
        for right in elements[index + 1 :]:
            ratio = SequenceMatcher(
                None, _tokens(left.original_content), _tokens(right.original_content)
            ).ratio()
            if ratio >= 0.82:
                matches.append(
                    SimilarityMatch(
                        source_name="This document",
                        target_element_id=right.id,
                        source_location=left.id,
                        matching_text=left.original_content,
                        similarity=round(ratio, 3),
                        attribution_present=True,
                    )
                )
    return matches


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _has_attribution(text: str) -> bool:
    return bool(re.search(r"\([A-Z][A-Za-z-]+.*\d{4}|\[\d+\]|https?://doi\.org/", text))
