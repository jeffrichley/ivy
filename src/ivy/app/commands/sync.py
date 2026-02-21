from __future__ import annotations

from pathlib import Path
import shutil
import sys

from ivy.app.commands.base import BaseCommand
from ivy.app.commands._actions import build_actions_filtered, summarize_actions
from ivy.app.commands._conflicts import apply_conflict_policy
from ivy.domain.models.config import BedConfig, GardenBed, GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.enums import ConflictPolicy
from ivy.domain.models.enums import PlanActionType
from ivy.domain.models.plan import CommandResult, PlanAction
from ivy.infra.fs.paths import find_bed_root, garden_config_path
from ivy.infra.state.store import file_sha256, now_utc_iso, record_applied
from ivy.infra.fs.yaml_io import read_yaml


class SyncCommand(BaseCommand):
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
            return self._sync_all()
        return self._sync_current()

    def _sync_all(self) -> CommandResult:
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
        policies = _artifact_policy_map(garden)
        resolved_actions, policy_error = apply_conflict_policy(
            actions=actions,
            mode="sync",
            policies=policies,
            interactive=sys.stdin.isatty(),
        )
        summary = summarize_actions(resolved_actions)
        if policy_error:
            return CommandResult(
                exit_code=1,
                message=policy_error,
                payload={
                    "kind": "action_plan",
                    "operation": "sync",
                    "scope": "all",
                    "garden_id": self._garden_id,
                    "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                    "actions": [action.model_dump(mode="json") for action in resolved_actions],
                    "summary": summary,
                },
            )
        applied, error = _apply_actions(resolved_actions)
        if error:
            return CommandResult(
                exit_code=1,
                message=error,
                payload={
                    "kind": "action_plan",
                    "operation": "sync",
                    "scope": "all",
                    "garden_id": self._garden_id,
                    "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                    "actions": [action.model_dump(mode="json") for action in resolved_actions],
                    "summary": summary,
                },
            )
        if applied:
            record_applied(applied)
        return CommandResult(
            exit_code=0,
            message=f"Sync scope: all beds (garden={self._garden_id})",
            payload={
                "kind": "action_plan",
                "operation": "sync",
                "scope": "all",
                "garden_id": self._garden_id,
                "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                "actions": [action.model_dump(mode="json") for action in resolved_actions],
                "summary": summary,
            },
        )

    def _sync_current(self) -> CommandResult:
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
        policies = _artifact_policy_map(garden)
        resolved_actions, policy_error = apply_conflict_policy(
            actions=actions,
            mode="sync",
            policies=policies,
            interactive=sys.stdin.isatty(),
        )
        summary = summarize_actions(resolved_actions)
        if policy_error:
            return CommandResult(
                exit_code=1,
                message=policy_error,
                payload={
                    "kind": "action_plan",
                    "operation": "sync",
                    "scope": "current",
                    "garden_id": bed.garden.id,
                    "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                    "actions": [action.model_dump(mode="json") for action in resolved_actions],
                    "summary": summary,
                },
            )
        applied, error = _apply_actions(resolved_actions)
        if error:
            return CommandResult(
                exit_code=1,
                message=error,
                payload={
                    "kind": "action_plan",
                    "operation": "sync",
                    "scope": "current",
                    "garden_id": bed.garden.id,
                    "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                    "actions": [action.model_dump(mode="json") for action in resolved_actions],
                    "summary": summary,
                },
            )
        if applied:
            record_applied(applied)
        return CommandResult(
            exit_code=0,
            message="Sync scope: current bed",
            payload={
                "kind": "action_plan",
                "operation": "sync",
                "scope": "current",
                "garden_id": bed.garden.id,
                "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                "actions": [action.model_dump(mode="json") for action in resolved_actions],
                "summary": summary,
            },
        )


def _apply_actions(actions: list[PlanAction]) -> tuple[list[dict[str, str]], str | None]:
    applied: list[dict[str, str]] = []
    for action in actions:
        if action.type in (PlanActionType.CONFLICT, PlanActionType.DRIFTED, PlanActionType.BOTH_CHANGED):
            return applied, (
                f"Sync blocked by conflict: bed={action.bed_id} artifact={action.artifact_id} "
                f"target={action.target_path} reason={action.reason}"
            )
        if action.type not in (PlanActionType.CREATE, PlanActionType.UPDATE, PlanActionType.COPY):
            continue
        if action.source_path is None or action.target_path is None:
            continue
        try:
            action.target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(action.source_path, action.target_path)
            applied.append(
                {
                    "bed_id": action.bed_id,
                    "artifact_id": action.artifact_id,
                    "target_path": str(action.target_path),
                    "last_applied_hash": file_sha256(action.target_path),
                    "last_applied_at": now_utc_iso(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return applied, (
                f"Sync failed: bed={action.bed_id} artifact={action.artifact_id} "
                f"target={action.target_path} error={exc}"
            )
    return applied, None


def _artifact_policy_map(garden: GardenConfig) -> dict[str, ConflictPolicy]:
    return {artifact.id: artifact.conflict_policy for artifact in garden.artifacts}
