from __future__ import annotations

from pathlib import Path

from ivy.app.commands.base import BaseCommand
from ivy.app.commands._actions import build_actions_filtered
from ivy.domain.models.config import BedConfig, GardenBed, GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.enums import PlanActionType
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.paths import find_bed_root, garden_config_path
from ivy.infra.fs.yaml_io import read_yaml


class StatusCommand(BaseCommand):
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
            return self._status_all()
        return self._status_current()

    def _status_all(self) -> CommandResult:
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
        items = [_to_status_item(action.model_dump(mode="json")) for action in actions]
        return CommandResult(
            exit_code=0,
            message=f"Status scope: all beds (garden={self._garden_id})",
            payload={
                "kind": "status_report",
                "scope": "all",
                "garden_id": self._garden_id,
                "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                "statuses": items,
                "summary": _summarize_status(items),
            },
        )

    def _status_current(self) -> CommandResult:
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
        items = [_to_status_item(action.model_dump(mode="json")) for action in actions]
        return CommandResult(
            exit_code=0,
            message="Status scope: current bed",
            payload={
                "kind": "status_report",
                "scope": "current",
                "garden_id": bed.garden.id,
                "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                "statuses": items,
                "summary": _summarize_status(items),
            },
        )


def _to_status_item(action: dict[str, object]) -> dict[str, object]:
    raw_type = str(action.get("type", "SKIP"))
    mapping = {
        PlanActionType.SKIP.value: "IN_SYNC",
        PlanActionType.CREATE.value: "SOURCE_ONLY",
        PlanActionType.UPDATE.value: "SOURCE_ONLY",
        PlanActionType.DRIFTED.value: "DRIFTED",
        PlanActionType.BOTH_CHANGED.value: "BOTH_CHANGED",
        PlanActionType.CONFLICT.value: "CONFLICT",
    }
    status = mapping.get(raw_type, "UNKNOWN")
    return {
        "status": status,
        "bed_id": action.get("bed_id", ""),
        "artifact_id": action.get("artifact_id", ""),
        "source_path": action.get("source_path"),
        "target_path": action.get("target_path"),
        "reason": action.get("reason", ""),
    }


def _summarize_status(items: list[dict[str, object]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in items:
        key = str(item.get("status", "UNKNOWN"))
        summary[key] = summary.get(key, 0) + 1
    return dict(sorted(summary.items(), key=lambda entry: entry[0]))
