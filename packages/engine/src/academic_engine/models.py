from datetime import datetime
from enum import Enum
from pathlib import Path

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
    mode: str | None = None
    provider: ProviderName | None = None
    output_path: Path | None = None
    created_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProviderMetadata(BaseModel):
    provider: ProviderName
    configured: bool
    default: bool = False
    model: str | None = None


class ProviderSettings(BaseModel):
    provider: ProviderName
    model: str | None = None
    api_key: str | None = Field(default=None, repr=False)


class DocumentService:
    def analyze(self, path: Path) -> DocumentMetadata:
        raise NotImplementedError
