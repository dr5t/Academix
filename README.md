<div align="center">
  <img src="assets/branding/academic-humanizer-horizontal.svg" alt="Academic Humanizer" width="520">
  <p><strong>Academic writing and document intelligence workspace</strong></p>
  <p>A local-first tool for inspecting research documents, improving selected paragraphs, reviewing citations, and exporting controlled revisions.</p>
  <p>
    <img src="https://img.shields.io/badge/Python-%3E%3D3.9-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9 or newer">
    <img src="https://img.shields.io/badge/Next.js-14.2.15-111111?style=flat-square&logo=next.js&logoColor=white" alt="Next.js 14.2.15">
    <img src="https://img.shields.io/badge/TypeScript-5.7.2-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript 5.7.2">
    <img src="https://img.shields.io/badge/License-not%20declared-92979D?style=flat-square" alt="License not declared">
  </p>
</div>

<p align="center"><img src="assets/branding/academic-humanizer-banner.svg" alt="Academic Humanizer document intelligence" width="100%"></p>

> Academic Humanizer is designed for reviewable, source-preserving work. It does not promise plagiarism scores, AI-detector scores, or automatic research validation.

## Contents

- [Overview](#-overview)
- [Capabilities](#-capabilities)
- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Processing workflow](#-processing-workflow)
- [Dashboard](#-dashboard)
- [CLI](#-cli)
- [Supported formats](#-supported-formats)
- [Writing modes](#-writing-modes)
- [Provider configuration](#-provider-configuration)
- [Academic integrity and citation review](#-academic-integrity-and-citation-review)
- [Formatting preservation](#-formatting-preservation)
- [Installation](#-installation)
- [Environment configuration](#-environment-configuration)
- [Running locally](#-running-locally)
- [Testing and verification](#-testing-and-verification)
- [Privacy and security](#-privacy-and-security)
- [Current limitations](#-current-limitations)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

## ![Overview](docs/assets/icons/overview.svg) Overview

Academic Humanizer is a monorepo with a Next.js dashboard, FastAPI service, shared Python engine, Typer CLI, and SQLite metadata store.

The application currently supports:

- Local DOCX, PDF, and TXT ingestion.
- Ordered document structure extraction.
- Paragraph-level provider-backed writing suggestions.
- Immutable originals and accepted-change DOCX export.
- Citation and bibliography analysis.
- DOI metadata lookup through Crossref and OpenAlex adapters.
- Internal repetition and explicit local-source similarity review.
- Finding review and dismissal with evidence and confidence.
- Provider connection tests without exposing credentials.

The source of truth is the implementation in `packages/engine`, `apps/api`, `apps/dashboard`, and `packages/cli`.

## ![Features](docs/assets/icons/features.svg) Capabilities

| Area | Implemented behavior |
| --- | --- |
| Document intelligence | DOCX structure, runs, styles, tables, sections, images, PDF text extraction, OCR-required detection |
| Writing intelligence | Seven modes, bounded context, structured provider output, validation warnings, paragraph-level review |
| Integrity review | Citation matching, DOI extraction, unsupported-claim heuristics, quotation attribution warnings, repeated passages |
| Preservation | Original hash tracking, separate revised output, stable element checks, conservative multi-run handling |
| Local operations | SQLite schema migrations, local files, Typer commands, FastAPI versioned API |

## ![Dashboard](docs/assets/icons/dashboard.svg) Screenshots

The screenshots below were captured from the running Next.js dashboard and FastAPI API using a non-sensitive demo DOCX.

### Overview

![Dashboard overview](docs/assets/screenshots/dashboard-overview.png)

### Document library

![Documents library](docs/assets/screenshots/documents-library.png)

### Upload

![Document upload](docs/assets/screenshots/document-upload.png)

### Analysis workspace

![Document analysis workspace](docs/assets/screenshots/document-analysis.png)

### Integrity review

![Academic integrity review](docs/assets/screenshots/integrity-review.png)

### Provider settings

![Provider settings](docs/assets/screenshots/provider-settings.png)

The writing comparison panel is implemented in the document workspace, but a genuine revised suggestion screenshot was not captured because no live AI provider was configured in this environment. The workspace therefore remains in its real pending-provider state rather than showing fabricated output.

## ![Architecture](docs/assets/icons/architecture.svg) Architecture

![System architecture](docs/assets/diagrams/system-architecture.svg)

| Layer | Location | Responsibility |
| --- | --- | --- |
| Dashboard | `apps/dashboard` | Browser UI, document library, writing review, integrity review, provider status |
| API | `apps/api` | FastAPI lifespan, validation, versioned routes, CORS, error boundary |
| Shared engine | `packages/engine` | Parsing, storage, providers, writing, integrity, similarity, export |
| CLI | `packages/cli` | Local commands using the same engine services |
| Storage | `storage/` | SQLite metadata and UUID-scoped original documents |

## ![Document processing](docs/assets/icons/document-processing.svg) Processing workflow

![Document processing pipeline](docs/assets/diagrams/document-processing-pipeline.svg)

Documents are copied into a UUID-named local directory after validation. The original upload is never overwritten. Provider calls occur only when a user requests a writing suggestion.

## ![Dashboard](docs/assets/icons/dashboard.svg) Dashboard

Routes currently present:

- `/` — overview and local workspace status.
- `/documents` — real document listing, upload, and deletion.
- `/documents/new` — drag-and-drop or file-browser upload.
- `/documents/[documentId]` — structure, writing workspace, export, and integrity review.
- `/settings` — local workspace settings.
- `/settings/providers` — provider readiness and connection tests.

The interface uses the existing obsidian palette, editorial serif document text, compact navigation, and custom inline SVG marks. It does not use Lucide, emoji, purple gradients, or fabricated analytics.

## ![Terminal](docs/assets/icons/terminal.svg) CLI

The installed `academix` command uses the same shared engine as the API:

```bash
academix --help
academix doctor
academix init --workspace "Research Workspace"
academix providers list
academix providers test --provider ollama
academix analyze research-paper.docx
academix analyze-writing research-paper.docx
academix compare research-paper.docx source-paper.docx
academix improve research-paper.docx --mode academic
academix export research-paper.docx --format docx
academix serve --port 8000
```

`improve` requests a real configured provider and asks for explicit approval before writing a separate revised DOCX. `providers test` reports connection failure when the configured endpoint cannot be reached.

## ![Document processing](docs/assets/icons/document-processing.svg) Supported formats

- **DOCX** — validated ZIP package, ordered paragraphs and tables, styles, runs, sections, relationships, images, citations, and references.
- **PDF** — text extraction with page and block analysis. Image-only pages report that OCR is required; OCR is not silently performed.
- **TXT** — UTF-8 text ingestion for lightweight analysis.

PDF layout-preserving editing is not implemented.

## ![Features](docs/assets/icons/features.svg) Writing modes

The writing engine supports:

1. Academic Research
2. Formal Academic
3. Technical Research
4. Simple Academic
5. Professional Report
6. Concise Academic
7. Research Explanation

The engine preserves numbers, dates, citations, technical terms, quotations, negation, and uncertainty where the provider response allows validation. Warnings block automatic acceptance.

## ![Providers](docs/assets/icons/providers.svg) Provider configuration

![Provider architecture](docs/assets/diagrams/provider-architecture.svg)

Supported adapters:

- OpenAI Chat Completions.
- Anthropic Messages API.
- Google Gemini `generateContent`.
- Ollama `/api/chat`.

Configure credentials in `.env`, never in browser code:

```dotenv
ACADEMIX_OPENAI_API_KEY=
ACADEMIX_ANTHROPIC_API_KEY=
ACADEMIX_GOOGLE_API_KEY=
ACADEMIX_OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Test a provider before requesting writing work:

```bash
academix providers test --provider openai
# or: ollama, anthropic, google
```

The provider page distinguishes `not configured`, `not tested`, `connection_successful`, and connection failure. In this repository environment, no live AI provider request has been verified.

## ![Academic integrity](docs/assets/icons/academic-integrity.svg) Academic integrity and citation review

![Integrity workflow](docs/assets/diagrams/integrity-workflow.svg)

The integrity service reports evidence for human review; it does not determine plagiarism.

Implemented checks include:

- APA/Harvard/Chicago-style author-year patterns.
- IEEE numeric citation patterns.
- Bibliography extraction.
- Citation-to-reference matching.
- Missing and unreferenced bibliography entries.
- DOI extraction.
- Citation consistency warnings.
- Potentially unattributed direct quotations.
- Potentially unsupported factual constructions.
- Repeated passages within a document.
- Similarity against explicitly supplied local source documents.
- Crossref and OpenAlex metadata verification adapters.

Metadata matches do not prove that a source supports a claim. The application does not access Turnitin, iThenticate, restricted academic databases, or the full internet.

## ![Security](docs/assets/icons/security.svg) Formatting preservation

![Controlled document processing](docs/assets/diagrams/document-processing-pipeline.svg)

Accepted suggestions are applied to a separate output DOCX. The source hash and source bytes remain unchanged.

Current safeguards:

- Stable positional element IDs plus original-text verification.
- Separate source and output paths.
- Tables and body-block ordering retained.
- Headers, footers, sections, images, and references retained through loading the original package.
- Incompatible multi-run formatting is rejected instead of flattened.
- Exported DOCX is reopened in automated tests.

Advanced OOXML fields, equation fidelity, complex numbering, and every layout edge case are not guaranteed and should be validated for high-stakes documents.

## ![Installation](docs/assets/icons/installation.svg) Installation

Requirements:

- Python 3.9 or newer.
- Node.js 18.17 or newer.
- npm.

```bash
git clone <repository-url>
cd Academix
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e packages/engine -e apps/api -e packages/cli
cp .env.example .env
cd apps/dashboard
npm install
cd ../..
```

## ![Configuration](docs/assets/icons/configuration.svg) Environment configuration

Supported environment variables are documented in [.env.example](.env.example):

| Variable | Purpose |
| --- | --- |
| `ACADEMIX_APP_ENV` | API environment label |
| `ACADEMIX_DATABASE_PATH` | SQLite database path |
| `ACADEMIX_DOCUMENTS_PATH` | Immutable local document storage |
| `ACADEMIX_TEMP_PATH` | Temporary upload storage |
| `ACADEMIX_API_HOST` / `ACADEMIX_API_PORT` | API bind address |
| `ACADEMIX_CORS_ORIGINS` | Allowed dashboard origins |
| `ACADEMIX_MAX_UPLOAD_BYTES` | Upload limit |
| `ACADEMIX_LOG_LEVEL` | Python logging level |
| `ACADEMIX_OPENAI_API_KEY` | Server-side OpenAI credential |
| `ACADEMIX_ANTHROPIC_API_KEY` | Server-side Anthropic credential |
| `ACADEMIX_GOOGLE_API_KEY` | Server-side Gemini credential |
| `ACADEMIX_OLLAMA_BASE_URL` | Local Ollama endpoint |

## ![Dashboard](docs/assets/icons/dashboard.svg) Running locally

Start API and dashboard together:

```bash
source .venv/bin/activate
./scripts/dev.sh
```

The script uses `.venv/bin/academix`, so shell activation is still required for the Python environment but the command itself does not depend on the caller's `PATH`.

Or run separately:

```bash
academix serve
cd apps/dashboard && npm run dev
```

Open `http://localhost:3000`. API health is available at `http://127.0.0.1:8000/api/v1/health`; OpenAPI documentation is at `http://127.0.0.1:8000/api/docs`.

## ![Testing](docs/assets/icons/testing.svg) Testing and verification

```bash
.venv/bin/ruff check packages/engine/src apps/api/src packages/cli/src tests
.venv/bin/ruff format --check packages/engine/src apps/api/src packages/cli/src tests
.venv/bin/pytest -q
cd apps/dashboard
npm test
npm run build
```

The repository currently has 22 passing Python tests. Dashboard TypeScript validation and the production build pass. Provider tests use mocked responses unless valid credentials and a reachable provider are configured.

## ![Security](docs/assets/icons/security.svg) Privacy and security

- Documents and metadata remain local by default.
- Original uploads are never overwritten.
- API keys stay server-side and are excluded from safe configuration responses.
- Uploads are extension- and structure-validated.
- Temporary uploads are removed after processing.
- Storage paths are UUID-scoped and traversal-checked.
- No uploaded document is sent externally unless a user requests a provider-backed writing suggestion.

`npm audit` currently reports one critical Next.js advisory chain and one high PostCSS advisory. The available fix requires a breaking Next.js 16 upgrade from the pinned Next.js 14 setup. It has not been applied blindly; this remains a documented upgrade task.

## ![Roadmap](docs/assets/icons/roadmap.svg) Current limitations

- No live AI provider was available during this documentation capture.
- OCR is not implemented.
- PDF editing is not implemented.
- Complex OOXML formatting requires conservative rejection or manual validation.
- Similarity review is limited to internal content and explicitly supplied local comparison files.
- Crossref/OpenAlex metadata verification does not validate claim support.
- No plagiarism score or AI-detector score is produced.
- Processing is synchronous; very large documents and slow providers need further operational benchmarking.

## ![Contributing](docs/assets/icons/contributing.svg) Contributing

Keep parsing, writing, integrity, storage, and preservation behavior in `packages/engine`. Add focused tests before changing API routes or dashboard behavior. Run the Python and dashboard verification commands above before submitting changes. Do not add credentials, private documents, generated `.next` output, or local SQLite data.

## ![License](docs/assets/icons/license.svg) License

No license file is currently declared in this repository. Add an explicit license before distributing the project as open-source software.

## Asset index

- Product identity: [`assets/branding/`](assets/branding/)
- README icons: [`docs/assets/icons/`](docs/assets/icons/)
- Architecture diagrams: [`docs/assets/diagrams/`](docs/assets/diagrams/)
- Captured dashboard screenshots: [`docs/assets/screenshots/`](docs/assets/screenshots/)
