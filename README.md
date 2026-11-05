# Academic Humanizer

Academic Humanizer is a local-first academic document workspace. The shared Python engine powers the FastAPI service, Typer CLI, SQLite metadata store, document intelligence pipeline, and Next.js dashboard.

## Requirements

- Python 3.9 or newer
- Node.js 18.17 or newer
- npm

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e packages/engine -e apps/api -e packages/cli
cp .env.example .env
cd apps/dashboard && npm install && cd ../..
```

The API and CLI use the same `academic-humanizer-engine` package. Local metadata is stored in `storage/academix.sqlite3`, and uploaded source documents are stored beneath `ACADEMIX_DOCUMENTS_PATH`.

## Run locally

Terminal one:

```bash
source .venv/bin/activate
academix serve
```

Terminal two:

```bash
cd apps/dashboard
npm run dev
```

Open `http://localhost:3000`. The API health endpoint is `http://127.0.0.1:8000/api/v1/health` and interactive API documentation is available at `/api/docs`.

## CLI

```bash
academix --help
academix doctor
academix init --workspace "Research Workspace"
academix providers list
academix serve --port 8000
```

Provider credentials belong in the local `.env` file and are never exposed by the configuration endpoint or dashboard bundle. Configure only providers you explicitly intend to use.

Phase 3 supports provider-backed paragraph suggestions through OpenAI, Anthropic, Google Gemini, and Ollama. Set the corresponding API key or local Ollama URL in `.env`, then select the provider in the document workspace. Provider requests are bounded to the selected paragraph and nearby context; the original upload is never sent to a provider by the storage layer.

## Verification

```bash
pytest
ruff check packages/engine/src apps/api/src packages/cli/src tests
cd apps/dashboard
npm test
npm run build
```

## Development workflow

1. Keep document parsing and writing behavior in `packages/engine`.
2. Expose engine services through versioned FastAPI routes in `apps/api`.
3. Call the same services from `packages/cli`.
4. Keep dashboard state and presentation in `apps/dashboard`.
5. Add fixtures and preservation tests before implementing document transformation.

## Document intelligence

Phase 2 supports local DOCX, PDF, and TXT ingestion:

```bash
academix serve
curl -F "file=@research-paper.docx" http://127.0.0.1:8000/api/v1/documents
```

Documents are copied into a UUID-named directory under `ACADEMIX_DOCUMENTS_PATH`. The source upload is never modified. The engine validates DOCX package structure, computes a SHA-256 hash, extracts ordered DOCX elements and formatting metadata, and identifies text-free PDF pages where OCR may be required. SQLite stores metadata and serialized analysis facts, not full document content.

The dashboard document library and new-analysis screen support browsing and drag-and-drop upload. Open a document to review its detected outline, counts, facts, and extraction warnings.

## Writing intelligence

The writing workspace supports seven modes, structured provider responses, paragraph-level suggestions, validation warnings, accept/reject review, and revised DOCX export:

```bash
academix analyze-writing research-paper.docx
academix improve research-paper.docx --mode academic_research
academix export research-paper.docx --format docx
```

Only explicitly accepted suggestions are applied to a separate revised DOCX. Original uploads remain immutable. Suggestions with numeric, citation, or other validation warnings require review and cannot be accepted automatically. Multi-run paragraphs with incompatible formatting are conservatively rejected during export rather than flattened.

Provider adapter tests use mocked responses. No live OpenAI, Anthropic, Gemini, or Ollama request was verified in this environment because valid credentials or a running local model were unavailable. Configure a provider and run a real suggestion request to perform live verification.
