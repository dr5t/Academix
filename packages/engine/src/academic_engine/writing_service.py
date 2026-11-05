from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from academic_engine.ai_providers import AnthropicProvider, GeminiProvider, OllamaProvider, OpenAIProvider
from academic_engine.config import Settings
from academic_engine.document_parser import parse_document
from academic_engine.document_service import DocumentService
from academic_engine.exceptions import DocumentNotFoundError, DocumentValidationError
from academic_engine.storage import SQLiteStore
from academic_engine.writing_engine import AcademicWritingEngine
from academic_engine.writing_models import (
    ProviderRequest,
    SuggestionRecord,
    SuggestionRequest,
    SuggestionStatus,
)


class WritingService:
    def __init__(self, settings: Settings, store: SQLiteStore, documents: DocumentService):
        self.settings = settings
        self.store = store
        self.documents = documents

    def create_suggestion(self, document_id: str, request: SuggestionRequest) -> SuggestionRecord:
        detail = self.documents.get_document(document_id)
        path = self.documents._path_for(detail)
        parsed = parse_document(path)
        provider_name = request.provider or self._default_provider()
        model = request.model or self._default_model(provider_name)
        suggestion = AcademicWritingEngine(self._providers()).improve(
            parsed,
            request.element_id,
            request.mode,
            provider_name,
            request.generation,
            {
                "language": request.language,
                "formality": request.formality,
                "conciseness": request.conciseness,
                "sentence_complexity": request.sentence_complexity,
            },
        )
        return self.store.create_suggestion(
            SuggestionRecord(
                id=str(uuid4()),
                document_id=document_id,
                element_id=suggestion.element_id,
                original_text=suggestion.original_text,
                revised_text=suggestion.revised_text,
                mode=suggestion.mode,
                provider=provider_name,
                model=model,
                changes_made=suggestion.changes_made,
                explanation=suggestion.explanation,
                meaning_change_warning=suggestion.meaning_change_warning,
                citation_preservation_status=suggestion.citation_preservation_status,
                validation_warnings=suggestion.validation_warnings,
                created_at=datetime.now(timezone.utc),
            )
        )

    def suggestions(self, document_id: str) -> list[SuggestionRecord]:
        self.documents.get_document(document_id)
        return self.store.list_suggestions(document_id)

    def suggestion(self, document_id: str, suggestion_id: str) -> SuggestionRecord:
        suggestion = self.store.get_suggestion(suggestion_id)
        if suggestion is None or suggestion.document_id != document_id:
            raise DocumentNotFoundError("Suggestion was not found.")
        return suggestion

    def set_status(self, document_id: str, suggestion_id: str, status: SuggestionStatus) -> SuggestionRecord:
        suggestion = self.suggestion(document_id, suggestion_id)
        if status is SuggestionStatus.ACCEPTED:
            if suggestion.meaning_change_warning or suggestion.validation_warnings:
                raise DocumentValidationError("This suggestion has validation warnings and requires review.")
        updated = self.store.update_suggestion_status(suggestion_id, status)
        if updated is None:
            raise DocumentNotFoundError("Suggestion was not found.")
        return updated

    def regenerate(self, document_id: str, suggestion_id: str) -> SuggestionRecord:
        previous = self.suggestion(document_id, suggestion_id)
        return self.create_suggestion(
            document_id,
            SuggestionRequest(
                element_id=previous.element_id,
                mode=previous.mode,
                provider=previous.provider,
                model=previous.model,
            ),
        )

    def _providers(self):
        return {
            "openai": OpenAIProvider(self.settings.openai_api_key),
            "anthropic": AnthropicProvider(self.settings.anthropic_api_key),
            "google": GeminiProvider(self.settings.google_api_key),
            "ollama": OllamaProvider(self.settings.ollama_base_url),
        }

    def _default_provider(self) -> str:
        configured = [
            name
            for name, value in {
                "openai": self.settings.openai_api_key,
                "anthropic": self.settings.anthropic_api_key,
                "google": self.settings.google_api_key,
                "ollama": self.settings.ollama_base_url,
            }.items()
            if value
        ]
        if not configured:
            raise DocumentValidationError("No AI provider is configured.")
        return configured[0]

    @staticmethod
    def _default_model(provider: str) -> str:
        return {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
            "google": "gemini-1.5-flash",
            "ollama": "llama3.2",
        }[provider]
