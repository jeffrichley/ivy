from __future__ import annotations

import json

from rich.box import HEAVY_EDGE
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ivy.domain.models.plan import CommandResult

console = Console()

WELCOME_BANNER = Text(
    "\n".join(
        [
"""                                                                                 
  ▄▄▄              ▄▄                                           ▄▄▄▄▄▄           
 █▀██  ██  ██▀▀     ██                              █▄         █▀ ██             
   ██  ██  ██       ██             ▄               ▄██▄           ██             
   ██  ██  ██ ▄█▀█▄ ██ ▄███▀ ▄███▄ ███▄███▄ ▄█▀█▄   ██ ▄███▄      ██ ▀█▄ ██▀██ ██
   ██▄ ██▄ ██ ██▄█▀ ██ ██    ██ ██ ██ ██ ██ ██▄█▀   ██ ██ ██      ██  ██▄██ ██▄██
   ▀████▀███▀▄▀█▄▄▄▄██▄▀███▄▄▀███▀▄██ ██ ▀█▄▀█▄▄▄  ▄██▄▀███▀    ▄▄██▄▄ ▀█▀ ▄▄▀██▀
                                                                              ██ 
                                                                            ▀▀▀  
"""        ]
    ),
    style="bold bright_green",
)


def print_welcome() -> None:
    panel = Panel(
        WELCOME_BANNER,
        title="[bold green]Welcome to Ivy[/bold green]",
        subtitle="[green]Seeded your first garden[/green]",
        border_style="green",
        box=HEAVY_EDGE,
        padding=(1, 2),
    )
    console.print(panel)


def print_json_result(result: CommandResult) -> None:
    console.print_json(
        json.dumps(
            {
                "exit_code": result.exit_code,
                "message": result.message,
                "payload": result.payload,
            }
        )
    )


def print_result(result: CommandResult, title: str | None = None) -> None:
    kind = result.payload.get("kind")
    if kind == "action_plan":
        _print_action_plan(result, title=title)
        return
    if kind == "status_report":
        _print_status_report(result, title=title)
        return

    if result.exit_code == 0:
        panel = Panel(result.message, title=title or "Ivy", border_style="green", box=HEAVY_EDGE)
    else:
        panel = Panel(result.message, title=title or "Ivy Error", border_style="red", box=HEAVY_EDGE)
    console.print(panel)


def _print_action_plan(result: CommandResult, title: str | None = None) -> None:
    operation = str(result.payload.get("operation", "plan")).upper()
    scope = str(result.payload.get("scope", "current"))
    garden_id = str(result.payload.get("garden_id", "default"))
    beds = list(result.payload.get("beds", []))
    actions = list(result.payload.get("actions", []))
    summary = dict(result.payload.get("summary", {}))
    publish = result.payload.get("publish")

    header = Panel(
        f"[bold]{operation}[/bold] scope: [cyan]{scope}[/cyan]\nGarden: [magenta]{garden_id}[/magenta]",
        title=title or "Ivy",
        border_style="bright_blue",
        box=HEAVY_EDGE,
    )
    console.print(header)

    table = Table(box=HEAVY_EDGE, border_style="blue", show_header=True, header_style="bold bright_cyan")
    table.add_column("Bed ID", style="bold white")
    table.add_column("Path", style="green")

    if beds:
        for bed in beds:
            table.add_row(str(bed.get("id", "")), str(bed.get("path", "")))
    else:
        table.add_row("No beds", "-")

    console.print(table)

    if summary:
        parts = [f"[bold]{k}[/bold]: {v}" for k, v in summary.items()]
        console.print(
            Panel(
                " | ".join(parts),
                title="Action Summary",
                border_style="bright_magenta",
                box=HEAVY_EDGE,
            )
        )

    if isinstance(publish, dict):
        console.print(
            Panel(
                (
                    f"requested_commit={bool(publish.get('requested_commit', False))} | "
                    f"requested_push={bool(publish.get('requested_push', False))}\n"
                    f"committed={bool(publish.get('committed', False))} | "
                    f"pushed={bool(publish.get('pushed', False))}\n"
                    f"commit_id={str(publish.get('commit_id', '')) or '-'}\n"
                    f"reason={str(publish.get('reason', '')) or '-'}"
                ),
                title="Publish",
                border_style="bright_green",
                box=HEAVY_EDGE,
            )
        )

    actions_table = Table(box=HEAVY_EDGE, border_style="magenta", show_header=True, header_style="bold bright_magenta")
    actions_table.add_column("Action", style="bold")
    actions_table.add_column("Bed", style="cyan")
    actions_table.add_column("Artifact", style="white", overflow="fold")
    actions_table.add_column("Source", style="green", overflow="fold")
    actions_table.add_column("Target", style="yellow", overflow="fold")
    actions_table.add_column("Reason", style="dim", overflow="fold")

    if actions:
        for item in actions:
            action = str(item.get("type", ""))
            if action == "CREATE":
                action_style = "green"
            elif action == "UPDATE":
                action_style = "yellow"
            elif action == "DRIFTED":
                action_style = "bright_yellow"
            elif action == "BOTH_CHANGED":
                action_style = "red"
            elif action == "PROMOTE_BED_TO_SOURCE":
                action_style = "bright_cyan"
            elif action == "SKIP":
                action_style = "dim"
            else:
                action_style = "cyan"
            actions_table.add_row(
                f"[{action_style}]{action}[/{action_style}]",
                str(item.get("bed_id", "")),
                str(item.get("artifact_id", "")),
                str(item.get("source_path", "")),
                str(item.get("target_path", "")),
                str(item.get("reason", "")),
            )
    else:
        actions_table.add_row("SKIP", "-", "-", "-", "-", "No actions")

    console.print(actions_table)


def _print_status_report(result: CommandResult, title: str | None = None) -> None:
    scope = str(result.payload.get("scope", "current"))
    garden_id = str(result.payload.get("garden_id", "default"))
    beds = list(result.payload.get("beds", []))
    statuses = list(result.payload.get("statuses", []))
    summary = dict(result.payload.get("summary", {}))

    header = Panel(
        f"[bold]STATUS[/bold] scope: [cyan]{scope}[/cyan]\nGarden: [magenta]{garden_id}[/magenta]",
        title=title or "Ivy",
        border_style="bright_blue",
        box=HEAVY_EDGE,
    )
    console.print(header)

    bed_table = Table(box=HEAVY_EDGE, border_style="blue", show_header=True, header_style="bold bright_cyan")
    bed_table.add_column("Bed ID", style="bold white")
    bed_table.add_column("Path", style="green")
    if beds:
        for bed in beds:
            bed_table.add_row(str(bed.get("id", "")), str(bed.get("path", "")))
    else:
        bed_table.add_row("No beds", "-")
    console.print(bed_table)

    if summary:
        parts = [f"[bold]{k}[/bold]: {v}" for k, v in summary.items()]
        console.print(
            Panel(
                " | ".join(parts),
                title="Status Summary",
                border_style="bright_magenta",
                box=HEAVY_EDGE,
            )
        )

    status_table = Table(box=HEAVY_EDGE, border_style="magenta", show_header=True, header_style="bold bright_magenta")
    status_table.add_column("Status", style="bold")
    status_table.add_column("Bed", style="cyan")
    status_table.add_column("Artifact", style="white", overflow="fold")
    status_table.add_column("Source", style="green", overflow="fold")
    status_table.add_column("Target", style="yellow", overflow="fold")
    status_table.add_column("Reason", style="dim", overflow="fold")

    if statuses:
        for item in statuses:
            status = str(item.get("status", "UNKNOWN"))
            if status == "IN_SYNC":
                status_style = "green"
            elif status == "SOURCE_ONLY":
                status_style = "yellow"
            elif status == "DRIFTED":
                status_style = "bright_yellow"
            elif status == "BOTH_CHANGED":
                status_style = "red"
            elif status == "CONFLICT":
                status_style = "red"
            else:
                status_style = "cyan"
            status_table.add_row(
                f"[{status_style}]{status}[/{status_style}]",
                str(item.get("bed_id", "")),
                str(item.get("artifact_id", "")),
                str(item.get("source_path", "")),
                str(item.get("target_path", "")),
                str(item.get("reason", "")),
            )
    else:
        status_table.add_row("IN_SYNC", "-", "-", "-", "-", "No managed artifacts")

    console.print(status_table)
