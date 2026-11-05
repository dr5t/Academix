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

For the API and dashboard together:

```bash
source .venv/bin/activate
./scripts/dev.sh
```

Or run them separately:

```bash
academix serve
```

```bash
cd apps/dashboard && npm run dev
```

Open `http://localhost:3000`. The API health endpoint is `http://127.0.0.1:8000/api/v1/health` and interactive API documentation is available at `http://127.0.0.1:8000/api/docs`.

## CLI

```bash
academix --help
academix doctor
academix init --workspace "Research Workspace"
academix providers list
academix providers test --provider ollama
academix analyze research-paper.docx
academix compare research-paper.docx source-paper.docx
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

Provider adapter tests use mocked responses. Use the provider settings screen or `academix providers test --provider <name>` to test credentials and model availability. A provider is not shown as verified merely because a key is present. No live OpenAI, Anthropic, Gemini, or Ollama request was verified in this environment because valid credentials or a running local model were unavailable.

## Privacy and limitations

Documents, analysis reports, suggestions, and review history remain in the configured local storage directory. Only a user-triggered writing request sends the selected paragraph and bounded context to the selected provider. Integrity review uses local parsing and explicitly configured metadata providers; it does not access Turnitin, iThenticate, restricted academic databases, or the full internet.

DOCX export preserves the original upload and writes a separate revised file. Paragraphs with incompatible formatting runs are rejected instead of flattened. Tables, images, headers, footers, sections, numbering, and references are retained by modifying the original package in place through `python-docx`; unsupported OOXML constructs remain a limitation and should be validated before relying on a revised file.

## Troubleshooting

- `academix doctor` initializes the database and required local directories.
- If upload fails, confirm the file is a valid DOCX, PDF, or TXT file and is below `ACADEMIX_MAX_UPLOAD_BYTES`.
- If a provider is unavailable, run `academix providers list` and then `academix providers test --provider <name>`. Credentials belong in `.env`, never in the dashboard.
- If port 8000 or 3000 is occupied, stop the existing process or run the API with `academix serve --port <port>` and set `NEXT_PUBLIC_API_URL` for the dashboard.
- Failed imports are cleaned up without deleting existing source documents.

## Academic integrity review

The document workspace can run a citation and originality review against the local document. It detects common APA/Harvard/Chicago author-year and IEEE numeric citations, extracts bibliography entries and DOI values, matches citations to references, flags probable missing attribution, reports repeated passages, and compares against explicitly supplied local source documents. Findings include evidence, confidence, a recommended action, and a review or dismissal state.

Crossref metadata verification is integrated and was verified live during Phase 4. OpenAlex is available as a fallback adapter but was not reachable during verification. Metadata matches validate bibliographic records only; they do not prove that a source supports a claim. The system does not scan the internet, access Turnitin or iThenticate, calculate plagiarism percentages, or make plagiarism determinations.

## Dependency audit status

`npm audit` currently reports one critical `next` advisory chain and one high `postcss` advisory. The available automated fix upgrades Next.js from 14 to 16.4.5, which is a breaking major-version change. It was not applied blindly because this application uses the Next 14 App Router and requires a separately tested framework-upgrade task. Dashboard type checking and production builds pass on the current pinned versions.
