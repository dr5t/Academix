from __future__ import annotations

import re
from typing import Dict, Optional

from academic_engine.ai_providers import AIProvider
from academic_engine.document_models import DocumentElement, ParsedDocument
from academic_engine.exceptions import DocumentValidationError
from academic_engine.writing_models import (
    ProviderRequest,
    WritingContext,
    WritingMode,
    WritingSuggestion,
)

MODE_INSTRUCTIONS: Dict[WritingMode, str] = {
    WritingMode.ACADEMIC_RESEARCH: "Use precise scholarly prose and preserve the author's evidence.",
    WritingMode.FORMAL_ACADEMIC: "Use formal, impersonal academic language with clear logical structure.",
    WritingMode.TECHNICAL_RESEARCH: "Prioritize technical precision, terminology, units, and reproducibility.",
    WritingMode.SIMPLE_ACADEMIC: "Improve clarity with accessible wording without reducing academic accuracy.",
    WritingMode.PROFESSIONAL_REPORT: "Use concise professional report language and explicit transitions.",
    WritingMode.CONCISE_ACADEMIC: "Reduce unnecessary words while retaining every claim and qualification.",
    WritingMode.RESEARCH_EXPLANATION: "Explain the research clearly for an informed non-specialist reader.",
}


def build_context(
    document: ParsedDocument, element_id: str, mode: WritingMode, **options
) -> WritingContext:
    index = next(
        (i for i, element in enumerate(document.elements) if element.id == element_id), None
    )
    if index is None:
        raise DocumentValidationError("Selected document element was not found.")
    element = document.elements[index]
    previous = document.elements[index - 1].original_content if index > 0 else None
    following = (
        document.elements[index + 1].original_content
        if index + 1 < len(document.elements)
        else None
    )
    terminology = sorted(
        {
            token
            for token in re.findall(r"\b[A-Za-z][A-Za-z0-9-]{5,}\b", element.original_content)
            if token.lower() not in {"should", "could", "because", "research"}
        }
    )[:30]
    return WritingContext(
        title=document.title,
        section_heading=_section_heading(document.elements, index),
        selected_text=element.original_content,
        previous_text=previous,
        following_text=following,
        terminology=terminology,
        citations=document.analysis.citation_patterns,
        mode=mode,
        **options,
    )


def _section_heading(elements: list[DocumentElement], index: int) -> Optional[str]:
    for element in reversed(elements[:index]):
        if element.style.heading_level:
            return element.original_content
    return None


class AcademicWritingEngine:
    def __init__(self, providers: Dict[str, AIProvider]):
        self.providers = providers

    def improve(
        self,
        document: ParsedDocument,
        element_id: str,
        mode: WritingMode,
        provider_name: str,
        request: ProviderRequest,
        options: Optional[dict] = None,
    ) -> WritingSuggestion:
        context = build_context(document, element_id, mode, **(options or {}))
        provider = self.providers.get(provider_name)
        if provider is None:
            raise DocumentValidationError(f"Provider '{provider_name}' is not available.")
        suggestion = provider.improve(context, request)
        suggestion.element_id = element_id
        return self._validate_preservation(suggestion, context)

    @staticmethod
    def _validate_preservation(
        suggestion: WritingSuggestion, context: WritingContext
    ) -> WritingSuggestion:
        warnings = list(suggestion.validation_warnings)
        original_numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", context.selected_text)
        revised_numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", suggestion.revised_text)
        if original_numbers != revised_numbers:
            warnings.append("Numeric values differ from the original and require review.")
            suggestion.meaning_change_warning = suggestion.meaning_change_warning or (
                "The proposed text changes numeric values."
            )
        missing_citations = [
            citation
            for citation in context.citations
            if citation in context.selected_text and citation not in suggestion.revised_text
        ]
        if missing_citations:
            warnings.append("One or more citations from the selected text are missing.")
            suggestion.citation_preservation_status = "warning"
        return suggestion.model_copy(update={"validation_warnings": warnings})
