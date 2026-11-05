from academic_cli.main import app
from typer.testing import CliRunner


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "academic document intelligence" in result.stdout.lower()


def test_cli_providers_list() -> None:
    result = CliRunner().invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    assert "OpenAI" in result.stdout
