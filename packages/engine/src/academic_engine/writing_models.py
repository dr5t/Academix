from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class WritingMode(str, Enum):
    ACADEMIC_RESEARCH = "academic_research"
    FORMAL_ACADEMIC = "formal_academic"
    TECHNICAL_RESEARCH = "technical_research"
    SIMPLE_ACADEMIC = "simple_academic"
    PROFESSIONAL_REPORT = "professional_report"
    CONCISE_ACADEMIC = "concise_academic"
    RESEARCH_EXPLANATION = "research_explanation"


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProviderRequest(BaseModel):
    model: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1200, ge=100, le=8000)
    timeout_seconds: float = Field(default=60, gt=0, le=300)


class WritingContext(BaseModel):
    title: Optional[str] = None
    section_heading: Optional[str] = None
    selected_text: str
    previous_text: Optional[str] = None
    following_text: Optional[str] = None
    terminology: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    mode: WritingMode = WritingMode.ACADEMIC_RESEARCH
    language: str = "English"
    formality: str = "high"
    conciseness: str = "balanced"
    sentence_complexity: str = "moderate"


class WritingSuggestion(BaseModel):
    element_id: str
    original_text: str
    revised_text: str
    mode: WritingMode
    changes_made: List[str] = Field(default_factory=list)
    explanation: str
    meaning_change_warning: Optional[str] = None
    citation_preservation_status: str
    validation_warnings: List[str] = Field(default_factory=list)


class SuggestionRecord(BaseModel):
    id: str
    document_id: str
    element_id: str
    original_text: str
    revised_text: str
    mode: WritingMode
    provider: str
    model: str
    changes_made: List[str] = Field(default_factory=list)
    explanation: str
    meaning_change_warning: Optional[str] = None
    citation_preservation_status: str
    validation_warnings: List[str] = Field(default_factory=list)
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime


class SuggestionRequest(BaseModel):
    element_id: str
    mode: WritingMode = WritingMode.ACADEMIC_RESEARCH
    provider: Optional[str] = None
    model: Optional[str] = None
    generation: ProviderRequest = Field(default_factory=ProviderRequest)
    language: str = "English"
    formality: str = "high"
    conciseness: str = "balanced"
    sentence_complexity: str = "moderate"


class AnalyzeWritingRequest(BaseModel):
    element_ids: List[str] = Field(min_length=1, max_length=10)
    mode: WritingMode = WritingMode.ACADEMIC_RESEARCH
    provider: Optional[str] = None
    model: Optional[str] = None
    generation: ProviderRequest = Field(default_factory=ProviderRequest)
