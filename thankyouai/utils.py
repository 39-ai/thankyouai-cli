"""Output helpers: human-readable vs JSON."""

from __future__ import annotations

import json
import sys

import click


def emit(data, *, json_output: bool = False, message: str = "") -> None:
    """Print data in human or JSON form."""
    if json_output:
        click.echo(json.dumps(data, indent=2, default=str))
        return
    if message:
        click.echo(message)
    _print_value(data, indent=0)


def _print_value(v, indent: int) -> None:
    prefix = "  " * indent
    if isinstance(v, dict):
        for k, val in v.items():
            if isinstance(val, (dict, list)):
                click.echo(f"{prefix}{k}:")
                _print_value(val, indent + 1)
            else:
                click.echo(f"{prefix}{k}: {val}")
    elif isinstance(v, list):
        for i, item in enumerate(v):
            if isinstance(item, dict):
                click.echo(f"{prefix}[{i}]")
                _print_value(item, indent + 1)
            else:
                click.echo(f"{prefix}- {item}")
    else:
        click.echo(f"{prefix}{v}")


def error_exit(message: str) -> None:
    click.echo(f"Error: {message}", err=True)
    sys.exit(1)


def progress_bar(result: dict) -> None:
    status = result.get("status", "?")
    pct = int(result.get("progress", 0.0) * 100)
    click.echo(f"\r  [{status:10s}] {pct:3d}%", nl=False, err=True)
    if status in ("succeeded", "failed", "cancelled"):
        click.echo("", err=True)
