from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class DocumentKind(str, Enum):
    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"


class ElementType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    TABLE_CELL = "table_cell"
    IMAGE = "image"
    HEADER = "header"
    FOOTER = "footer"
    SECTION = "section"
    PAGE_BREAK = "page_break"


class TextRun(BaseModel):
    text: str
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None


class StyleInfo(BaseModel):
    name: Optional[str] = None
    heading_level: Optional[int] = Field(default=None, ge=1, le=9)
    numbering: Optional[str] = None


class DocumentElement(BaseModel):
    id: str
    element_type: ElementType
    position: int = Field(ge=0)
    original_content: str = ""
    text_runs: list[TextRun] = Field(default_factory=list)
    style: StyleInfo = Field(default_factory=StyleInfo)
    relationships: list[str] = Field(default_factory=list)
    processing_status: str = "original"
    metadata: Dict[str, Union[str, int, float, bool, None]] = Field(default_factory=dict)


class DocumentSection(BaseModel):
    index: int
    page_width_twips: Optional[int] = None
    page_height_twips: Optional[int] = None
    margin_top_twips: Optional[int] = None
    margin_bottom_twips: Optional[int] = None
    margin_left_twips: Optional[int] = None
    margin_right_twips: Optional[int] = None
    start_type: Optional[str] = None


class DocumentAnalysis(BaseModel):
    document_type: DocumentKind
    title: Optional[str] = None
    page_count: Optional[int] = None
    paragraph_count: int = 0
    heading_count: int = 0
    heading_structure: list[str] = Field(default_factory=list)
    table_count: int = 0
    image_count: int = 0
    reference_section_detected: bool = False
    citation_patterns: list[str] = Field(default_factory=list)
    empty_sections: list[str] = Field(default_factory=list)
    unsupported_elements: list[str] = Field(default_factory=list)
    extraction_issues: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    document_type: DocumentKind
    title: Optional[str] = None
    elements: list[DocumentElement] = Field(default_factory=list)
    sections: list[DocumentSection] = Field(default_factory=list)
    analysis: DocumentAnalysis
    source_hash: str
    file_size: int


class DocumentRecord(BaseModel):
    id: str
    filename: str
    document_type: DocumentKind
    file_size: int
    file_hash: str
    status: str
    created_at: datetime
    workspace_id: str


class DocumentDetail(DocumentRecord):
    analysis: Optional[DocumentAnalysis] = None


class DocumentUploadResult(DocumentRecord):
    pass
