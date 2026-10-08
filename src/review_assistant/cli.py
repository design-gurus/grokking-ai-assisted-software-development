"""The command line mode: review a patch file and print the findings."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from review_assistant.config import load_config
from review_assistant.diff.parser import parse
from review_assistant.ledger.db import connect, rows
from review_assistant.providers.base import get_provider
from review_assistant.review import review_files

app = typer.Typer(help="Review a unified diff and print findings.", no_args_is_help=True)


@app.command()
def review(
    patch: Path = typer.Argument(..., help="A unified diff to review."),
    format: str = typer.Option("table", "--format", help="table or json"),
    provider: str | None = typer.Option(None, "--provider", help="mock, anthropic or openai"),
    config_file: Path = typer.Option(Path(".review-assistant.yml"), "--config"),
    no_ledger: bool = typer.Option(False, "--no-ledger", help="Do not write a ledger row."),
) -> None:
    """Review PATCH and print the findings as a table or as JSON, with a one-line cost summary."""
    config = load_config(config_file)
    if provider:
        config.provider = provider
    files = parse(patch.read_text(encoding="utf-8"))
    engine = None if no_ledger else connect(config.ledger_path)
    result = review_files(files, config, get_provider(config), engine)
    for dropped in result.dropped:
        typer.echo(f"dropped {dropped}: over the token budget", err=True)
    if format == "json":
        payload = [
            {"path": f.path, "line": f.line, "severity": f.severity, "message": f.message}
            for f in result.findings
        ]
        typer.echo(json.dumps(payload, indent=2))
    elif format == "table":
        if not result.findings:
            typer.echo("No findings.")
        for f in result.findings:
            typer.echo(f"{f.severity:<9} {f.path}:{f.line}  {f.message}")
    else:
        typer.echo(f"unknown format {format!r}; use table or json", err=True)
        raise typer.Exit(code=2)
    typer.echo(
        f"cost: {result.cents} cents ({result.input_tokens} in, {result.output_tokens} out, "
        f"{config.provider}/{config.model})",
        err=format == "json",
    )


@app.command()
def ledger(config_file: Path = typer.Option(Path(".review-assistant.yml"), "--config")) -> None:
    """Print every ledger row: when, provider, model, pull request, tokens and cents."""
    config = load_config(config_file)
    for row in rows(connect(config.ledger_path)):
        pr = row.pull_request if row.pull_request is not None else "-"
        typer.echo(
            f"{row.created_at:%Y-%m-%d %H:%M} {row.provider}/{row.model} pr={pr} "
            f"in={row.input_tokens} out={row.output_tokens} cents={row.cents}"
        )


if __name__ == "__main__":
    app()
