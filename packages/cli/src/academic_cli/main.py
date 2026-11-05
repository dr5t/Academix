from pathlib import Path

import typer
from academic_engine.config import get_settings
from academic_engine.logging import configure_logging
from academic_engine.providers import provider_metadata
from academic_engine.storage import SQLiteStore
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Local-first academic document intelligence workspace.")
console = Console()


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
) -> None:
    """List configured AI providers."""
    if action.lower() != "list":
        raise typer.BadParameter("Only the 'list' action is available in Phase 1.")
    table = Table("Provider", "Status")
    for metadata in provider_metadata(get_settings()):
        status = "configured" if metadata.configured else "not configured"
        table.add_row(metadata.provider.value, status)
    console.print(table)


@app.command()
def serve(
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port", min=1, max=65535),
) -> None:
    """Start the local FastAPI service."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "academic_api.main:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
    )


def _path_is_safe(path: Path) -> bool:
    return path.exists() and path.is_file()
