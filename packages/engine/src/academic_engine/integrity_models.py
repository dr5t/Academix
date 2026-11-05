from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CitationStyle(str, Enum):
    APA = "apa7"
    IEEE = "ieee"
    HARVARD = "harvard"
    MLA = "mla"
    CHICAGO = "chicago"
    UNKNOWN = "unknown"


class FindingStatus(str, Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


class CitationRecord(BaseModel):
    raw_text: str
    style: CitationStyle
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    reference_key: Optional[str] = None
    element_id: Optional[str] = None


class ReferenceRecord(BaseModel):
    raw_text: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    title: Optional[str] = None
    doi: Optional[str] = None
    element_id: Optional[str] = None


class CitationAnalysis(BaseModel):
    detected_style: CitationStyle
    citations: list[CitationRecord] = Field(default_factory=list)
    references: list[ReferenceRecord] = Field(default_factory=list)
    missing_references: list[str] = Field(default_factory=list)
    unreferenced_entries: list[str] = Field(default_factory=list)
    doi_values: list[str] = Field(default_factory=list)
    consistency_warnings: list[str] = Field(default_factory=list)


class IntegrityFinding(BaseModel):
    id: str
    document_id: str
    element_id: Optional[str] = None
    category: str
    severity: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    recommended_action: str
    evidence: list[str] = Field(default_factory=list)
    status: FindingStatus = FindingStatus.OPEN
    dismissal_reason: Optional[str] = None
    created_at: datetime


class MetadataVerification(BaseModel):
    provider: str
    query: str
    retrieved_metadata: dict[str, object] = Field(default_factory=dict)
    persistent_identifier: Optional[str] = None
    verification_status: str
    retrieved_at: datetime
    match_confidence: float = Field(ge=0, le=1)


class SimilarityMatch(BaseModel):
    source_document_id: Optional[str] = None
    source_name: str
    target_element_id: str
    source_location: str
    matching_text: str
    similarity: float = Field(ge=0, le=1)
    attribution_present: bool


class IntegrityReport(BaseModel):
    document_id: str
    analyzed_at: datetime
    citation_analysis: CitationAnalysis
    findings: list[IntegrityFinding] = Field(default_factory=list)
    internal_similarity: list[SimilarityMatch] = Field(default_factory=list)
    external_matches: list[SimilarityMatch] = Field(default_factory=list)
    metadata_verifications: list[MetadataVerification] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class IntegrityRequest(BaseModel):
    style: CitationStyle = CitationStyle.UNKNOWN
    source_document_ids: list[str] = Field(default_factory=list, max_length=10)
    verify_metadata: bool = True


class FindingReviewRequest(BaseModel):
    status: FindingStatus
    dismissal_reason: Optional[str] = None
