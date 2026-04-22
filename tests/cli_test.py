"""Smoke tests for the Typer-based ``rohe`` CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from rohe.cli.main import app


def test_cli_help_exits_cleanly() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ROHE" in result.stdout


def test_cli_subcommands_registered() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for subcommand in ("start", "orchestration", "observation"):
        assert subcommand in result.stdout
