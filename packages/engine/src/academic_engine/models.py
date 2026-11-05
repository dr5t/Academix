from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProviderName(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str


class SafeConfiguration(BaseModel):
    environment: str
    api_host: str
    api_port: int
    cors_origins: list[str]
    max_upload_bytes: int
    configured_providers: list[ProviderName]


class Workspace(BaseModel):
    id: str
    name: str
    created_at: datetime


class DocumentMetadata(BaseModel):
    id: str
    filename: str
    document_type: str
    source_path: Path
    created_at: datetime
    workspace_id: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProcessingHistory(BaseModel):
    id: str
    document_id: str
    status: str
    mode: Optional[str] = None
    provider: Optional[ProviderName] = None
    output_path: Optional[Path] = None
    created_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProviderMetadata(BaseModel):
    provider: ProviderName
    configured: bool
    default: bool = False
    model: Optional[str] = None


class ProviderSettings(BaseModel):
    provider: ProviderName
    model: Optional[str] = None
    api_key: Optional[str] = Field(default=None, repr=False)


class DocumentService:
    def analyze(self, path: Path) -> DocumentMetadata:
        raise NotImplementedError
