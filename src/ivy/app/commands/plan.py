from __future__ import annotations

from pathlib import Path

from ivy.app.commands.base import BaseCommand
from ivy.app.commands._actions import build_actions_filtered, summarize_actions
from ivy.domain.models.config import BedConfig, GardenBed, GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.paths import find_bed_root, garden_config_path
from ivy.infra.fs.yaml_io import read_yaml


class PlanCommand(BaseCommand):
    def __init__(
        self,
        cwd: Path,
        all_beds: bool,
        garden_id: str,
        only_artifact: str | None = None,
        bed_id: str | None = None,
    ) -> None:
        self._cwd = cwd
        self._all_beds = all_beds
        self._garden_id = garden_id
        self._only_artifact = only_artifact
        self._bed_id = bed_id

    def execute(self, context: ExecutionContext) -> CommandResult:
        if self._all_beds:
            return self._plan_all()
        return self._plan_current()

    def _plan_all(self) -> CommandResult:
        config_path = garden_config_path(self._garden_id)
        if not config_path.exists():
            return CommandResult(
                exit_code=1,
                message=f"Garden config not found: {config_path}",
                payload={"kind": "error"},
            )

        garden = GardenConfig.model_validate(read_yaml(config_path))
        beds = sorted(garden.beds, key=lambda bed: (bed.id, bed.path))
        if self._bed_id is not None:
            beds = [bed for bed in beds if bed.id == self._bed_id]
        actions = build_actions_filtered(garden, config_path, beds, only_artifact=self._only_artifact)
        summary = summarize_actions(actions)
        return CommandResult(
            exit_code=0,
            message=f"Plan scope: all beds (garden={self._garden_id})",
            payload={
                "kind": "action_plan",
                "operation": "plan",
                "scope": "all",
                "garden_id": self._garden_id,
                "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                "actions": [action.model_dump(mode="json") for action in actions],
                "summary": summary,
            },
        )

    def _plan_current(self) -> CommandResult:
        bed_root = find_bed_root(self._cwd)
        if bed_root is None:
            return CommandResult(
                exit_code=1,
                message="No .ivy/bed.yaml found in current directory or parents. Run `ivy plant` first.",
                payload={"kind": "error"},
            )

        bed_path = bed_root / ".ivy" / "bed.yaml"
        bed = BedConfig.model_validate(read_yaml(bed_path))
        config_path = garden_config_path(bed.garden.id)
        if not config_path.exists():
            return CommandResult(
                exit_code=1,
                message=f"Garden config not found: {config_path}",
                payload={"kind": "error"},
            )
        garden = GardenConfig.model_validate(read_yaml(config_path))
        selected_bed = next((item for item in garden.beds if item.id == bed.bed.id), None)
        effective_bed = selected_bed or GardenBed(id=bed.bed.id, path=str(bed_root.resolve()))
        if self._bed_id is not None and self._bed_id != effective_bed.id:
            return CommandResult(
                exit_code=1,
                message=f"--bed {self._bed_id} does not match current bed {effective_bed.id}",
                payload={"kind": "error"},
            )
        actions = build_actions_filtered(garden, config_path, [effective_bed], only_artifact=self._only_artifact)
        summary = summarize_actions(actions)
        bed_entry = (
            {"id": selected_bed.id, "path": selected_bed.path}
            if selected_bed
            else {"id": bed.bed.id, "path": str(bed_root.resolve())}
        )
        return CommandResult(
            exit_code=0,
            message="Plan scope: current bed",
            payload={
                "kind": "action_plan",
                "operation": "plan",
                "scope": "current",
                "garden_id": bed.garden.id,
                "beds": [bed_entry],
                "actions": [action.model_dump(mode="json") for action in actions],
                "summary": summary,
            },
        )
