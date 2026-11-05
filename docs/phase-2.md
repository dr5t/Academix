# Phase 2 document intelligence

Phase 2 adds a shared ingestion service used by the FastAPI routes and future CLI commands. DOCX, PDF, and TXT uploads are validated before they are copied into UUID-scoped local storage. Originals are immutable; the service records a SHA-256 hash and only stores metadata and serialized analysis in SQLite.

DOCX parsing preserves ordered paragraphs and tables, heading levels, styles, runs, basic font attributes, image relationship IDs, section page settings, page breaks, and citation patterns. PDF parsing extracts page text and block counts and reports pages without a text layer as OCR-required warnings. PDF editing is intentionally not implemented.

The dashboard calls the versioned document endpoints and displays real local records. It provides browse and drag-and-drop upload, analysis outlines, document counts, extraction notes, and deletion with confirmation.

```text
POST   /api/v1/documents
GET    /api/v1/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/analysis
DELETE /api/v1/documents/{document_id}
```

Phase 2 does not contact AI providers or rewrite document content.
