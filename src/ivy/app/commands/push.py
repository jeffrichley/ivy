from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

from ivy.app.commands._actions import summarize_actions
from ivy.app.commands.base import BaseCommand
from ivy.app.commands._conflicts import apply_conflict_policy
from ivy.domain.models.config import BedConfig, GardenBed, GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.enums import ConflictPolicy, Direction, PlanActionType
from ivy.domain.models.plan import CommandResult, PlanAction
from ivy.infra.fs.paths import find_bed_root, garden_config_path
from ivy.infra.fs.yaml_io import read_yaml
from ivy.infra.git.gateway import GitPythonGateway
from ivy.infra.state.store import load_state_index, now_utc_iso, record_applied


class PushCommand(BaseCommand):
    def __init__(
        self,
        cwd: Path,
        all_beds: bool,
        garden_id: str,
        only_artifact: str | None = None,
        bed_id: str | None = None,
        commit: bool = False,
        push: bool = False,
    ) -> None:
        self._cwd = cwd
        self._all_beds = all_beds
        self._garden_id = garden_id
        self._only_artifact = only_artifact
        self._bed_id = bed_id
        self._commit = commit
        self._push = push
        self._git = GitPythonGateway()

    def execute(self, context: ExecutionContext) -> CommandResult:
        if self._push and not self._commit:
            return CommandResult(
                exit_code=2,
                message="--push requires --commit.",
                payload={"kind": "error"},
            )
        if self._all_beds:
            return self._push_all()
        return self._push_current()

    def _push_all(self) -> CommandResult:
        config_path = garden_config_path(self._garden_id)
        if not config_path.exists():
            return CommandResult(exit_code=1, message=f"Garden config not found: {config_path}", payload={"kind": "error"})
        guard = self._guard_git_state(config_path.parent)
        if guard is not None:
            return guard

        garden = GardenConfig.model_validate(read_yaml(config_path))
        beds = sorted(garden.beds, key=lambda bed: (bed.id, bed.path))
        if self._bed_id is not None:
            beds = [bed for bed in beds if bed.id == self._bed_id]
        actions = _build_push_actions(garden, config_path, beds, only_artifact=self._only_artifact)
        policies = _artifact_policy_map(garden)
        resolved_actions, policy_error = apply_conflict_policy(
            actions=actions,
            mode="push",
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
                    "operation": "push",
                    "scope": "all",
                    "garden_id": self._garden_id,
                    "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                    "actions": [a.model_dump(mode="json") for a in resolved_actions],
                    "summary": summary,
                },
            )
        applied, error = _apply_push_actions(resolved_actions)
        if error:
            return CommandResult(
                exit_code=1,
                message=error,
                payload={
                    "kind": "action_plan",
                    "operation": "push",
                    "scope": "all",
                    "garden_id": self._garden_id,
                    "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                    "actions": [a.model_dump(mode="json") for a in resolved_actions],
                    "summary": summary,
                },
            )
        if applied:
            record_applied(applied)
        publish = self._publish_if_requested(config_path.parent, resolved_actions)
        if publish["exit_code"] != 0:
            return CommandResult(
                exit_code=1,
                message=str(publish.get("reason", "push publish failed")),
                payload={
                    "kind": "action_plan",
                    "operation": "push",
                    "scope": "all",
                    "garden_id": self._garden_id,
                    "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                    "actions": [a.model_dump(mode="json") for a in resolved_actions],
                    "summary": summary,
                    "publish": _publish_payload(publish),
                },
            )
        return CommandResult(
            exit_code=0,
            message=f"Push scope: all beds (garden={self._garden_id})",
            payload={
                "kind": "action_plan",
                "operation": "push",
                "scope": "all",
                "garden_id": self._garden_id,
                "beds": [{"id": bed.id, "path": bed.path} for bed in beds],
                "actions": [a.model_dump(mode="json") for a in resolved_actions],
                "summary": summary,
                "publish": _publish_payload(publish),
            },
        )

    def _push_current(self) -> CommandResult:
        bed_root = find_bed_root(self._cwd)
        if bed_root is None:
            return CommandResult(
                exit_code=1,
                message="No .ivy/bed.yaml found in current directory or parents. Run `ivy plant` first.",
                payload={"kind": "error"},
            )
        bed_cfg = BedConfig.model_validate(read_yaml(bed_root / ".ivy" / "bed.yaml"))
        config_path = garden_config_path(bed_cfg.garden.id)
        if not config_path.exists():
            return CommandResult(exit_code=1, message=f"Garden config not found: {config_path}", payload={"kind": "error"})
        guard = self._guard_git_state(config_path.parent)
        if guard is not None:
            return guard

        garden = GardenConfig.model_validate(read_yaml(config_path))
        selected = next((item for item in garden.beds if item.id == bed_cfg.bed.id), None)
        effective_bed = selected or GardenBed(id=bed_cfg.bed.id, path=str(bed_root.resolve()))
        if self._bed_id is not None and self._bed_id != effective_bed.id:
            return CommandResult(
                exit_code=1,
                message=f"--bed {self._bed_id} does not match current bed {effective_bed.id}",
                payload={"kind": "error"},
            )
        actions = _build_push_actions(garden, config_path, [effective_bed], only_artifact=self._only_artifact)
        policies = _artifact_policy_map(garden)
        resolved_actions, policy_error = apply_conflict_policy(
            actions=actions,
            mode="push",
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
                    "operation": "push",
                    "scope": "current",
                    "garden_id": bed_cfg.garden.id,
                    "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                    "actions": [a.model_dump(mode="json") for a in resolved_actions],
                    "summary": summary,
                },
            )
        applied, error = _apply_push_actions(resolved_actions)
        if error:
            return CommandResult(
                exit_code=1,
                message=error,
                payload={
                    "kind": "action_plan",
                    "operation": "push",
                    "scope": "current",
                    "garden_id": bed_cfg.garden.id,
                    "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                    "actions": [a.model_dump(mode="json") for a in resolved_actions],
                    "summary": summary,
                },
            )
        if applied:
            record_applied(applied)
        publish = self._publish_if_requested(config_path.parent, resolved_actions)
        if publish["exit_code"] != 0:
            return CommandResult(
                exit_code=1,
                message=str(publish.get("reason", "push publish failed")),
                payload={
                    "kind": "action_plan",
                    "operation": "push",
                    "scope": "current",
                    "garden_id": bed_cfg.garden.id,
                    "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                    "actions": [a.model_dump(mode="json") for a in resolved_actions],
                    "summary": summary,
                    "publish": _publish_payload(publish),
                },
            )
        return CommandResult(
            exit_code=0,
            message="Push scope: current bed",
            payload={
                "kind": "action_plan",
                "operation": "push",
                "scope": "current",
                "garden_id": bed_cfg.garden.id,
                "beds": [{"id": effective_bed.id, "path": effective_bed.path}],
                "actions": [a.model_dump(mode="json") for a in resolved_actions],
                "summary": summary,
                "publish": _publish_payload(publish),
            },
        )

    def _guard_git_state(self, garden_root: Path) -> CommandResult | None:
        if not self._git.is_repo(str(garden_root)):
            return None
        if self._commit:
            if self._git.has_staged_changes(str(garden_root)):
                return CommandResult(
                    exit_code=1,
                    message=(
                        f"Garden repo has pre-staged changes: {garden_root}. "
                        "Unstage or commit them before ivy push --commit."
                    ),
                    payload={"kind": "error"},
                )
            return None
        if self._git.status_clean(str(garden_root)):
            return None
        return CommandResult(
            exit_code=1,
            message=f"Garden repo is dirty: {garden_root}. Commit/stash changes before ivy push.",
            payload={"kind": "error"},
        )

    def _publish_if_requested(self, garden_root: Path, actions: list[PlanAction]) -> dict[str, str | bool | int]:
        requested_commit = self._commit
        requested_push = self._push
        publish: dict[str, str | bool | int] = {
            "exit_code": 0,
            "requested_commit": requested_commit,
            "requested_push": requested_push,
            "committed": False,
            "pushed": False,
            "commit_id": "",
            "reason": "",
        }
        if not requested_commit and not requested_push:
            publish["reason"] = "publish not requested"
            return publish
        if not self._git.is_repo(str(garden_root)):
            publish["exit_code"] = 1
            publish["reason"] = f"publish requested but garden is not a git repo: {garden_root}"
            return publish

        managed_source_candidates = sorted(
            {
                str(action.target_path)
                for action in actions
                if action.target_path is not None
            }
        )
        if not managed_source_candidates:
            publish["reason"] = "no promoted changes to publish"
            return publish

        commit_message = _commit_message(self._garden_id, actions)
        commit_result = self._git.commit_paths(str(garden_root), managed_source_candidates, commit_message)
        if commit_result.exit_code != 0:
            publish["exit_code"] = 1
            publish["reason"] = commit_result.message
            return publish

        committed = bool(commit_result.payload.get("committed", False))
        publish["committed"] = committed
        publish["commit_id"] = str(commit_result.payload.get("commit_id", ""))
        if not committed:
            publish["reason"] = "no changes to commit"
            return publish
        publish["reason"] = "commit created"

        if requested_push:
            if not self._git.has_remote(str(garden_root), remote_name="origin"):
                publish["exit_code"] = 1
                publish["reason"] = "push requested but no 'origin' remote configured"
                return publish
            push_result = self._git.push(str(garden_root))
            if push_result.exit_code != 0:
                publish["exit_code"] = 1
                publish["reason"] = push_result.message
                return publish
            publish["pushed"] = True
            publish["reason"] = "commit and push succeeded"
        return publish


def _build_push_actions(
    garden: GardenConfig,
    garden_config_file: Path,
    beds: list[GardenBed],
    only_artifact: str | None,
) -> list[PlanAction]:
    actions: list[PlanAction] = []
    state_index = load_state_index()
    garden_root = garden_config_file.parent.resolve()

    for bed in sorted(beds, key=lambda item: (item.id, item.path)):
        bed_root = Path(bed.path).resolve()
        for artifact in sorted(
            [item for item in garden.artifacts if only_artifact is None or item.id == only_artifact],
            key=lambda item: item.id,
        ):
            if artifact.direction != Direction.ONE_WAY:
                continue
            for target in sorted([t for t in artifact.targets if t.bed_id in (None, bed.id)], key=lambda t: (t.bed_id or "", t.path)):
                bed_file = (bed_root / target.path).resolve()
                source_file = (garden_root / artifact.source).resolve()
                if not bed_file.exists() or not bed_file.is_file():
                    actions.append(
                        PlanAction(
                            type=PlanActionType.SKIP,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="bed target missing",
                        )
                    )
                    continue

                key = (bed.id, artifact.id, str(bed_file))
                last = state_index.get(key)

                if not source_file.exists():
                    actions.append(
                        PlanAction(
                            type=PlanActionType.PROMOTE_BED_TO_SOURCE,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="garden source missing",
                        )
                    )
                    continue

                if not source_file.is_file():
                    actions.append(
                        PlanAction(
                            type=PlanActionType.CONFLICT,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="garden source is not a file",
                        )
                    )
                    continue

                source_hash = _sha256(source_file)
                bed_hash = _sha256(bed_file)
                if source_hash == bed_hash:
                    actions.append(
                        PlanAction(
                            type=PlanActionType.SKIP,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="already in sync",
                        )
                    )
                    continue

                if not last:
                    actions.append(
                        PlanAction(
                            type=PlanActionType.CONFLICT,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="no baseline for safe promotion",
                        )
                    )
                    continue

                source_changed = source_hash != last
                bed_changed = bed_hash != last
                if bed_changed and not source_changed:
                    actions.append(
                        PlanAction(
                            type=PlanActionType.PROMOTE_BED_TO_SOURCE,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="local target changed since last sync",
                        )
                    )
                elif source_changed and not bed_changed:
                    actions.append(
                        PlanAction(
                            type=PlanActionType.SKIP,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="garden source changed since last sync",
                        )
                    )
                else:
                    actions.append(
                        PlanAction(
                            type=PlanActionType.BOTH_CHANGED,
                            bed_id=bed.id,
                            artifact_id=artifact.id,
                            source_path=bed_file,
                            target_path=source_file,
                            reason="both bed and source changed since last sync",
                        )
                    )
    return actions


def _apply_push_actions(actions: list[PlanAction]) -> tuple[list[dict[str, str]], str | None]:
    applied: list[dict[str, str]] = []
    for action in actions:
        if action.type in (PlanActionType.CONFLICT, PlanActionType.DRIFTED, PlanActionType.BOTH_CHANGED):
            return applied, (
                f"Push blocked by conflict: bed={action.bed_id} artifact={action.artifact_id} "
                f"target={action.target_path} reason={action.reason}"
            )
        if action.type != PlanActionType.PROMOTE_BED_TO_SOURCE:
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
                    "target_path": str(action.source_path),
                    "last_applied_hash": _sha256(action.source_path),
                    "last_applied_at": now_utc_iso(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return applied, (
                f"Push failed: bed={action.bed_id} artifact={action.artifact_id} "
                f"target={action.target_path} error={exc}"
            )
    return applied, None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_policy_map(garden: GardenConfig) -> dict[str, ConflictPolicy]:
    return {artifact.id: artifact.conflict_policy for artifact in garden.artifacts}


def _publish_payload(publish: dict[str, str | bool | int]) -> dict[str, str | bool]:
    return {
        "requested_commit": bool(publish.get("requested_commit", False)),
        "requested_push": bool(publish.get("requested_push", False)),
        "committed": bool(publish.get("committed", False)),
        "pushed": bool(publish.get("pushed", False)),
        "commit_id": str(publish.get("commit_id", "")),
        "reason": str(publish.get("reason", "")),
    }


def _commit_message(garden_id: str, actions: list[PlanAction]) -> str:
    promoted = sum(1 for action in actions if action.type == PlanActionType.PROMOTE_BED_TO_SOURCE)
    artifacts = sorted({action.artifact_id for action in actions if action.type == PlanActionType.PROMOTE_BED_TO_SOURCE})
    details = ", ".join(artifacts[:5])
    if len(artifacts) > 5:
        details = f"{details}, +{len(artifacts) - 5} more"
    suffix = f" ({details})" if details else ""
    return f"ivy push: promote {promoted} artifact(s) for garden {garden_id}{suffix}"
