from pathlib import Path
from typing import Optional

import typer
from academic_engine.config import get_settings
from academic_engine.document_parser import parse_document
from academic_engine.document_service import DocumentService
from academic_engine.docx_modifier import export_accepted_changes
from academic_engine.exceptions import DocumentValidationError, ProviderUnavailableError
from academic_engine.integrity_models import IntegrityRequest
from academic_engine.integrity_service import IntegrityService
from academic_engine.logging import configure_logging
from academic_engine.providers import provider_metadata
from academic_engine.similarity import compare_documents
from academic_engine.storage import SQLiteStore
from academic_engine.writing_models import SuggestionRequest, SuggestionStatus, WritingMode
from academic_engine.writing_service import WritingService
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Local-first academic document intelligence workspace.")
console = Console()
PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google Gemini",
    "ollama": "Ollama",
}
MODE_ALIASES = {
    "academic": WritingMode.ACADEMIC_RESEARCH,
}


@app.callback()
def main() -> None:
    configure_logging(get_settings())


@app.command()
def doctor() -> None:
    """Check local runtime and storage readiness."""
    settings = get_settings()
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    console.print("[bold green]Ready[/bold green] Academic Humanizer local services are available.")
    console.print(f"Database: {settings.database_path}")


@app.command()
def init(
    workspace: str = typer.Option("Academic Workspace", "--workspace", "-w"),
) -> None:
    """Initialize local storage and create a workspace."""
    settings = get_settings()
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    existing = store.list_workspaces()
    created = store.create_workspace(workspace) if not existing else existing[0]
    console.print(f"Workspace ready: [bold]{created.name}[/bold]")


@app.command("providers")
def providers_command(
    action: str = typer.Argument("list", help="Provider action.", case_sensitive=False),
    provider: Optional[str] = typer.Option(None, "--provider"),
) -> None:
    """List configured AI providers."""
    if action.lower() == "test":
        if not provider:
            raise typer.BadParameter("--provider is required for the test action.")
        _test_provider(provider)
        return
    if action.lower() != "list":
        raise typer.BadParameter("Supported actions are 'list' and 'test'.")
    table = Table("Provider", "Status")
    for metadata in provider_metadata(get_settings()):
        status = "configured" if metadata.configured else "not configured"
        table.add_row(PROVIDER_LABELS[metadata.provider.value], status)
    console.print(table)


def _test_provider(provider: str) -> None:
    from academic_api.routes import _provider
    from academic_engine.models import ProviderName

    try:
        result = _provider(ProviderName(provider.lower())).test_connection()
    except ProviderUnavailableError as error:
        raise typer.BadParameter(str(error)) from error
    except (ValueError, KeyError) as error:
        raise typer.BadParameter(f"Unsupported provider: {provider}") from error
    console.print(f"{result.provider.value}: {result.status}")
    console.print(result.message)
    if result.models:
        console.print("Models: " + ", ".join(result.models))


@app.command()
def serve(
    host: Optional[str] = typer.Option(None, "--host"),
    port: Optional[int] = typer.Option(None, "--port", min=1, max=65535),
) -> None:
    """Start the local FastAPI service."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "academic_api.main:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
    )


@app.command()
def improve(
    path: Path = typer.Argument(..., exists=True, readable=True),
    mode: str = typer.Option("academic", "--mode"),
    provider: Optional[str] = typer.Option(None, "--provider"),
) -> None:
    """Create a paragraph-level suggestion and request explicit approval."""
    settings = get_settings()
    try:
        selected_mode = MODE_ALIASES.get(mode.lower())
        if selected_mode is None:
            selected_mode = WritingMode(mode.lower())
    except ValueError as error:
        raise typer.BadParameter(f"Unsupported writing mode: {mode}") from error
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    documents = DocumentService(settings, store)
    imported = documents.import_file(path, path.name)
    detail = documents.get_document(imported.id)
    parsed = _parse_or_fail(documents._path_for(detail))
    element = next(
        (
            item
            for item in parsed.elements
            if item.element_type.value in {"paragraph", "heading"} and item.original_content.strip()
        ),
        None,
    )
    if element is None:
        raise typer.BadParameter("The document has no editable paragraph.")
    try:
        suggestion = WritingService(settings, store, documents).create_suggestion(
            imported.id,
            SuggestionRequest(element_id=element.id, mode=selected_mode, provider=provider),
        )
    except ProviderUnavailableError as error:
        raise typer.BadParameter(str(error)) from error
    console.print(
        f"\nOriginal:\n{suggestion.original_text}\n\nProposed:\n{suggestion.revised_text}"
    )
    if suggestion.validation_warnings:
        console.print(
            "[yellow]Review warnings:[/yellow] " + "; ".join(suggestion.validation_warnings)
        )
    if not typer.confirm("Accept this suggestion?"):
        console.print("Suggestion retained as pending.")
        return
    store.update_suggestion_status(suggestion.id, SuggestionStatus.ACCEPTED)
    output = path.with_name(f"{path.stem}.revised{path.suffix}")
    stored_suggestion = store.get_suggestion(suggestion.id)
    if stored_suggestion is None:
        raise typer.BadParameter("The accepted suggestion could not be loaded.")
    export_accepted_changes(documents._path_for(detail), output, [stored_suggestion])
    console.print(f"Exported: {output}")


@app.command("analyze-writing")
def analyze_writing(path: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Inspect the first editable paragraph and report provider readiness."""
    settings = get_settings()
    document = _parse_or_fail(path)
    editable = sum(
        item.element_type.value in {"paragraph", "heading"} and bool(item.original_content.strip())
        for item in document.elements
    )
    configured = [item.provider.value for item in provider_metadata(settings) if item.configured]
    console.print(f"Editable elements: {editable}")
    console.print(f"Configured providers: {', '.join(configured) or 'none'}")


@app.command()
def analyze(
    path: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Run local academic integrity and citation analysis."""
    settings = get_settings()
    settings.ensure_directories()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    documents = DocumentService(settings, store)
    imported = documents.import_file(path, path.name)
    report = IntegrityService(store, documents).analyze(
        imported.id, IntegrityRequest(verify_metadata=False)
    )
    console.print(f"Findings: {len(report.findings)}")
    console.print(f"Citations: {len(report.citation_analysis.citations)}")
    console.print(f"References: {len(report.citation_analysis.references)}")


@app.command()
def compare(
    target: Path = typer.Argument(..., exists=True, readable=True),
    source: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Compare two local documents for substantial overlapping passages."""
    matches = compare_documents(_parse_or_fail(target), [("source", _parse_or_fail(source))])
    console.print(f"Matches: {len(matches)}")
    for match in matches:
        console.print(
            f"{match.target_element_id} · {match.similarity:.0%} · {match.source_location}"
        )


@app.command()
def export(
    path: Path = typer.Argument(..., exists=True, readable=True),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    format: str = typer.Option("docx", "--format"),
) -> None:
    """Export accepted local suggestions for a document."""
    if format.lower() != "docx":
        raise typer.BadParameter("Only DOCX export is supported.")
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    records = [item for item in store.list_documents() if item.filename == path.name]
    if not records:
        raise typer.BadParameter("No local processing record matches this filename.")
    suggestions = store.list_suggestions(records[0].id)
    destination = output or path.with_name(f"{path.stem}.revised.docx")
    export_accepted_changes(path, destination, suggestions)
    console.print(f"Exported: {destination}")


def _path_is_safe(path: Path) -> bool:
    return path.exists() and path.is_file()


def _parse_or_fail(path: Path):
    try:
        return parse_document(path)
    except DocumentValidationError as error:
        raise typer.BadParameter(str(error)) from error
