from __future__ import annotations

import getpass
import platform
import socket
from pathlib import Path

import typer

from ivy.app.commands.init import InitGardenCommand
from ivy.app.commands.init_bed import InitBedCommand
from ivy.app.commands.add import AddCommand
from ivy.app.commands.graft import GraftGardenCommand
from ivy.app.commands.plan import PlanCommand
from ivy.app.commands.pull import PullCommand
from ivy.app.commands.push import PushCommand
from ivy.app.commands.sync import SyncCommand
from ivy.app.commands.status import StatusCommand
from ivy.cli.render import print_json_result, print_result, print_welcome
from ivy.domain.models.context import ExecutionContext, RuntimeContext
from ivy.domain.models.enums import CommandName
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.paths import garden_config_path, garden_root

app = typer.Typer(help="Ivy CLI")


def _seed_impl(
    garden_id: str,
    path: Path | None,
    here: bool,
    force: bool,
) -> None:
    """Seed a garden in global ivy home by default."""
    context = _build_context(CommandName.INIT)
    if here and path is not None:
        print_result(CommandResult(exit_code=2, message="Use either --here or --path, not both."), title="Seed")
        raise typer.Exit(code=2)

    if here:
        target_dir = Path.cwd()
    elif path is not None:
        target_dir = path.resolve()
    else:
        target_dir = garden_root(garden_id)

    result = InitGardenCommand(target_dir=target_dir, garden_id=garden_id, force=force).execute(context)
    if result.exit_code == 0 and bool(result.payload.get("first_seed")):
        print_welcome()
    print_result(result, title="Seed")
    raise typer.Exit(code=result.exit_code)


@app.command("seed")
def seed_command(
    garden_id: str = typer.Option("default", "--garden-id"),
    path: Path | None = typer.Option(None, "--path", help="Directory where ivy.yaml will be written."),
    here: bool = typer.Option(False, "--here", help="Write ivy.yaml in current directory."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing ivy.yaml."),
) -> None:
    """Seed a new Ivy garden (global by default)."""
    _seed_impl(garden_id=garden_id, path=path, here=here, force=force)


@app.command("init", hidden=True)
def init_command_alias(
    garden_id: str = typer.Option("default", "--garden-id"),
    path: Path | None = typer.Option(None, "--path", help="Directory where ivy.yaml will be written."),
    here: bool = typer.Option(False, "--here", help="Write ivy.yaml in current directory."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing ivy.yaml."),
) -> None:
    """Deprecated alias for seed."""
    _seed_impl(garden_id=garden_id, path=path, here=here, force=force)


def _plant_impl(
    bed_id: str | None,
    garden_id: str,
    garden_path: Path | None,
    profile: str,
    force: bool,
) -> None:
    """Register current directory as an Ivy bed."""
    resolved_bed_id = bed_id or Path.cwd().name
    resolved_garden_config = garden_path.resolve() if garden_path else garden_config_path(garden_id)
    context = _build_context(CommandName.INIT_BED)
    result = InitBedCommand(
        cwd=Path.cwd(),
        bed_id=resolved_bed_id,
        garden_config_path=resolved_garden_config,
        garden_id=garden_id,
        profile=profile,
        force=force,
    ).execute(context)
    print_result(result, title="Plant")
    raise typer.Exit(code=result.exit_code)


@app.command("plant")
def plant_command(
    bed_id: str | None = typer.Option(None, "--bed-id"),
    garden_id: str = typer.Option("default", "--garden-id"),
    garden_path: Path | None = typer.Option(
        None,
        "--garden-path",
        help="Path to garden ivy.yaml (default: global garden path from --garden-id).",
    ),
    profile: str = typer.Option("default", "--profile"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing .ivy/bed.yaml."),
) -> None:
    """Plant this project as an Ivy bed (writes .ivy/bed.yaml)."""
    _plant_impl(bed_id=bed_id, garden_id=garden_id, garden_path=garden_path, profile=profile, force=force)


@app.command("init-bed", hidden=True)
def init_bed_command_alias(
    bed_id: str | None = typer.Option(None, "--bed-id"),
    garden_id: str = typer.Option("default", "--garden-id"),
    garden_path: Path | None = typer.Option(
        None,
        "--garden-path",
        help="Path to garden ivy.yaml (default: global garden path from --garden-id).",
    ),
    profile: str = typer.Option("default", "--profile"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing .ivy/bed.yaml."),
) -> None:
    """Deprecated alias for plant."""
    _plant_impl(bed_id=bed_id, garden_id=garden_id, garden_path=garden_path, profile=profile, force=force)


@app.command("plan")
def plan_command(
    all_beds: bool = typer.Option(False, "--all", help="Plan for all beds listed in garden ivy.yaml."),
    garden_id: str = typer.Option("default", "--garden-id"),
    only: str | None = typer.Option(None, "--only", help="Limit to a single artifact id."),
    bed: str | None = typer.Option(None, "--bed", help="Limit to a single bed id."),
    json_output: bool = typer.Option(False, "--json", help="Render machine-readable JSON output."),
) -> None:
    """Show planned changes."""
    context = _build_context(CommandName.PLAN)
    result = PlanCommand(
        cwd=Path.cwd(),
        all_beds=all_beds,
        garden_id=garden_id,
        only_artifact=only,
        bed_id=bed,
    ).execute(context)
    if json_output:
        print_json_result(result)
    else:
        print_result(result, title="Plan")
    raise typer.Exit(code=result.exit_code)


@app.command("add")
def add_command(
    files: list[Path] | None = typer.Argument(None, help="File(s) in current bed to manage with Ivy."),
    all_files: bool = typer.Option(False, "--all", help="Auto-discover all candidate files in this bed."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview add registration without writing changes."),
    sync: bool = typer.Option(False, "--sync", help="Run sync after add."),
) -> None:
    """Add file(s) as managed artifacts in the garden config."""
    if sync and dry_run:
        print_result(CommandResult(exit_code=2, message="--sync cannot be used with --dry-run."), title="Add")
        raise typer.Exit(code=2)
    context = _build_context(CommandName.ADD)
    result = AddCommand(cwd=Path.cwd(), files=files or [], all_files=all_files, dry_run=dry_run).execute(context)
    print_result(result, title="Add")
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)

    if sync:
        garden_id = str(result.payload.get("garden_id", "default"))
        sync_result = SyncCommand(cwd=Path.cwd(), all_beds=True, garden_id=garden_id).execute(context)
        print_result(sync_result, title="Sync")
        raise typer.Exit(code=sync_result.exit_code)


@app.command("sync")
def sync_command(
    all_beds: bool = typer.Option(False, "--all", help="Sync all beds listed in garden ivy.yaml."),
    garden_id: str = typer.Option("default", "--garden-id"),
    only: str | None = typer.Option(None, "--only", help="Limit to a single artifact id."),
    bed: str | None = typer.Option(None, "--bed", help="Limit to a single bed id."),
) -> None:
    """Apply planned changes."""
    context = _build_context(CommandName.SYNC)
    result = SyncCommand(
        cwd=Path.cwd(),
        all_beds=all_beds,
        garden_id=garden_id,
        only_artifact=only,
        bed_id=bed,
    ).execute(context)
    print_result(result, title="Sync")
    raise typer.Exit(code=result.exit_code)


@app.command("push")
def push_command(
    all_beds: bool = typer.Option(False, "--all", help="Push from all beds listed in garden ivy.yaml."),
    garden_id: str = typer.Option("default", "--garden-id"),
    only: str | None = typer.Option(None, "--only", help="Limit to a single artifact id."),
    bed: str | None = typer.Option(None, "--bed", help="Limit to a single bed id."),
    commit: bool = typer.Option(False, "--commit", help="Stage and commit promoted garden changes."),
    push: bool = typer.Option(False, "--push", help="Push committed changes to remote (requires --commit)."),
    json_output: bool = typer.Option(False, "--json", help="Render machine-readable JSON output."),
) -> None:
    """Promote bed-side managed changes up into the garden source."""
    if push and not commit:
        print_result(CommandResult(exit_code=2, message="--push requires --commit."), title="Push")
        raise typer.Exit(code=2)
    context = _build_context(CommandName.PUSH)
    result = PushCommand(
        cwd=Path.cwd(),
        all_beds=all_beds,
        garden_id=garden_id,
        only_artifact=only,
        bed_id=bed,
        commit=commit,
        push=push,
    ).execute(context)
    if json_output:
        print_json_result(result)
    else:
        print_result(result, title="Push")
    raise typer.Exit(code=result.exit_code)


@app.command("pull")
def pull_command(
    garden_id: str = typer.Option("default", "--garden-id"),
) -> None:
    """Pull latest garden changes from git using ff-only policy."""
    context = _build_context(CommandName.PULL)
    result = PullCommand(garden_id=garden_id).execute(context)
    print_result(result, title="Pull")
    raise typer.Exit(code=result.exit_code)


@app.command("graft")
def graft_command(
    garden_id: str = typer.Option("default", "--garden-id"),
    url: str | None = typer.Option(None, "--url", help="Git remote URL to connect for this garden."),
    remote_name: str = typer.Option("origin", "--remote-name"),
) -> None:
    """Attach a garden to a git repo (init or clone by garden id)."""
    context = _build_context(CommandName.INIT)
    result = GraftGardenCommand(garden_id=garden_id, url=url, remote_name=remote_name).execute(context)
    print_result(result, title="Graft")
    raise typer.Exit(code=result.exit_code)


@app.command("status")
def status_command(
    all_beds: bool = typer.Option(False, "--all", help="Show status for all beds listed in garden ivy.yaml."),
    garden_id: str = typer.Option("default", "--garden-id"),
    only: str | None = typer.Option(None, "--only", help="Limit to a single artifact id."),
    bed: str | None = typer.Option(None, "--bed", help="Limit to a single bed id."),
    json_output: bool = typer.Option(False, "--json", help="Render machine-readable JSON output."),
) -> None:
    """Show current sync status."""
    context = _build_context(CommandName.STATUS)
    result = StatusCommand(
        cwd=Path.cwd(),
        all_beds=all_beds,
        garden_id=garden_id,
        only_artifact=only,
        bed_id=bed,
    ).execute(context)
    if json_output:
        print_json_result(result)
    else:
        print_result(result, title="Status")
    raise typer.Exit(code=result.exit_code)


def _build_context(command: CommandName) -> ExecutionContext:
    runtime = RuntimeContext(
        os=platform.system().lower(),
        arch=platform.machine().lower(),
        hostname=socket.gethostname(),
        username=getpass.getuser(),
        box_id=socket.gethostname(),
        project_root=Path.cwd(),
        garden_id=None,
        profile=None,
    )
    return ExecutionContext(command=command, runtime=runtime)
