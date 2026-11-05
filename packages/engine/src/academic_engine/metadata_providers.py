from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx

from academic_engine.exceptions import ProviderUnavailableError
from academic_engine.integrity_models import MetadataVerification


class ScholarlyMetadataProvider(ABC):
    name: str

    @abstractmethod
    def verify(self, query: str) -> MetadataVerification:
        raise NotImplementedError


class CrossrefProvider(ScholarlyMetadataProvider):
    name = "crossref"

    def __init__(self, timeout_seconds: float = 10):
        self.timeout_seconds = timeout_seconds

    def verify(self, query: str) -> MetadataVerification:
        try:
            response = httpx.get(
                "https://api.crossref.org/works",
                params={"query.bibliographic": query, "rows": 1},
                timeout=self.timeout_seconds,
                headers={"User-Agent": "AcademicHumanizer/0.1 (local research tool)"},
            )
            response.raise_for_status()
            item = response.json()["message"]["items"][0]
            metadata = {
                key: item.get(key)
                for key in ("DOI", "title", "author", "published", "container-title")
                if item.get(key) is not None
            }
            confidence = (
                1.0
                if item.get("DOI") and query.lower() in " ".join(item.get("title", [])).lower()
                else 0.65
            )
            return MetadataVerification(
                provider=self.name,
                query=query,
                retrieved_metadata=metadata,
                persistent_identifier=item.get("DOI"),
                verification_status="verified_metadata" if confidence >= 0.9 else "possible_match",
                retrieved_at=datetime.now(timezone.utc),
                match_confidence=confidence,
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderUnavailableError(f"Crossref metadata lookup failed: {error}") from error


class OpenAlexProvider(ScholarlyMetadataProvider):
    name = "openalex"

    def __init__(self, timeout_seconds: float = 10):
        self.timeout_seconds = timeout_seconds

    def verify(self, query: str) -> MetadataVerification:
        try:
            response = httpx.get(
                "https://api.openalex.org/works",
                params={"search": query, "per-page": 1},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            item: dict[str, Any] = response.json()["results"][0]
            doi = item.get("doi")
            metadata = {
                key: item.get(key)
                for key in ("id", "doi", "title", "publication_year", "authorships")
                if item.get(key) is not None
            }
            return MetadataVerification(
                provider=self.name,
                query=query,
                retrieved_metadata=metadata,
                persistent_identifier=doi,
                verification_status="verified_metadata" if doi else "incomplete_match",
                retrieved_at=datetime.now(timezone.utc),
                match_confidence=0.85 if doi else 0.6,
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderUnavailableError(f"OpenAlex metadata lookup failed: {error}") from error
