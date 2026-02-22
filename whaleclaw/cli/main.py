"""WhaleClaw CLI — Typer application entry point."""

from __future__ import annotations

import typer

from whaleclaw.cli.gateway_cmd import gateway_app

app = typer.Typer(
    name="whaleclaw",
    help="WhaleClaw — Personal AI Assistant",
    no_args_is_help=True,
)

app.add_typer(gateway_app, name="gateway", help="Gateway 服务管理")
