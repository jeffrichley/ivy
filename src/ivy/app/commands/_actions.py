from __future__ import annotations

import hashlib
from pathlib import Path

from ivy.domain.models.config import GardenArtifact, GardenBed, GardenConfig
from ivy.domain.models.enums import Direction, PlanActionType
from ivy.domain.models.plan import PlanAction
from ivy.infra.diff.content import text_changed
from ivy.infra.state.store import load_state_index


def build_actions(garden_config: GardenConfig, garden_config_file: Path, beds: list[GardenBed]) -> list[PlanAction]:
    return build_actions_filtered(garden_config, garden_config_file, beds, only_artifact=None)


def build_actions_filtered(
    garden_config: GardenConfig,
    garden_config_file: Path,
    beds: list[GardenBed],
    only_artifact: str | None,
) -> list[PlanAction]:
    garden_root = garden_config_file.parent
    state_index = load_state_index()
    actions: list[PlanAction] = []
    ordered_beds = sorted(beds, key=lambda bed: (bed.id, bed.path))
    ordered_artifacts = sorted(
        [artifact for artifact in garden_config.artifacts if only_artifact is None or artifact.id == only_artifact],
        key=lambda artifact: artifact.id,
    )

    for bed in ordered_beds:
        bed_root = Path(bed.path)
        for artifact in ordered_artifacts:
            if artifact.direction != Direction.ONE_WAY:
                continue
            actions.extend(
                _build_artifact_actions_for_bed(
                    artifact,
                    bed_root=bed_root,
                    bed_id=bed.id,
                    garden_root=garden_root,
                    state_index=state_index,
                )
            )

    return actions


def summarize_actions(actions: list[PlanAction]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for action in actions:
        key = action.type.value
        summary[key] = summary.get(key, 0) + 1
    return dict(sorted(summary.items(), key=lambda item: item[0]))


def _build_artifact_actions_for_bed(
    artifact: GardenArtifact,
    bed_root: Path,
    bed_id: str,
    garden_root: Path,
    state_index: dict[tuple[str, str, str], str],
) -> list[PlanAction]:
    actions: list[PlanAction] = []
    source_root = (garden_root / artifact.source).resolve()
    targets = [target for target in artifact.targets if target.bed_id in (None, bed_id)]

    if not targets:
        return []

    for target in sorted(targets, key=lambda t: (t.bed_id or "", t.path)):
        target_root = (bed_root / target.path).resolve()
        if not _is_within(bed_root.resolve(), target_root):
            actions.append(
                PlanAction(
                    type=PlanActionType.CONFLICT,
                    bed_id=bed_id,
                    artifact_id=artifact.id,
                    source_path=source_root,
                    target_path=target_root,
                    reason="unsafe target path escapes bed root",
                )
            )
            continue

        if not source_root.exists():
            actions.append(
                PlanAction(
                    type=PlanActionType.SKIP,
                    bed_id=bed_id,
                    artifact_id=artifact.id,
                    source_path=source_root,
                    target_path=target_root,
                    reason="source missing",
                )
            )
            continue

        if source_root.is_file():
            last_applied_hash = state_index.get((bed_id, artifact.id, str(target_root.resolve())))
            actions.append(_classify_file_action(artifact.id, bed_id, source_root, target_root, last_applied_hash))
            continue

        for source_file in sorted(path for path in source_root.rglob("*") if path.is_file()):
            rel = source_file.relative_to(source_root)
            target_file = target_root / rel
            last_applied_hash = state_index.get((bed_id, artifact.id, str(target_file.resolve())))
            actions.append(
                _classify_file_action(
                    artifact.id,
                    bed_id,
                    source_file,
                    target_file,
                    last_applied_hash,
                )
            )

    return actions


def _classify_file_action(
    artifact_id: str,
    bed_id: str,
    source_file: Path,
    target_file: Path,
    last_applied_hash: str | None,
) -> PlanAction:
    if not target_file.exists():
        return PlanAction(
            type=PlanActionType.CREATE,
            bed_id=bed_id,
            artifact_id=artifact_id,
            source_path=source_file,
            target_path=target_file,
            reason="target missing",
        )

    if target_file.is_dir():
        action_type = PlanActionType.CONFLICT if last_applied_hash else PlanActionType.UPDATE
        reason = "target type changed locally" if last_applied_hash else "target type mismatch"
        return PlanAction(type=action_type, bed_id=bed_id, artifact_id=artifact_id, source_path=source_file, target_path=target_file, reason=reason)

    source_hash = _file_sha256(source_file)
    target_hash = _file_sha256(target_file)
    if source_hash == target_hash:
        return PlanAction(
            type=PlanActionType.SKIP,
            bed_id=bed_id,
            artifact_id=artifact_id,
            source_path=source_file,
            target_path=target_file,
            reason="already in sync",
        )

    if last_applied_hash:
        source_changed = source_hash != last_applied_hash
        target_changed = target_hash != last_applied_hash
        if not source_changed and target_changed:
            return PlanAction(
                type=PlanActionType.DRIFTED,
                bed_id=bed_id,
                artifact_id=artifact_id,
                source_path=source_file,
                target_path=target_file,
                reason="local target modified since last sync",
            )
        if source_changed and not target_changed:
            return PlanAction(
                type=PlanActionType.UPDATE,
                bed_id=bed_id,
                artifact_id=artifact_id,
                source_path=source_file,
                target_path=target_file,
                reason="source changed since last sync",
            )
        if source_changed and target_changed:
            return PlanAction(
                type=PlanActionType.BOTH_CHANGED,
                bed_id=bed_id,
                artifact_id=artifact_id,
                source_path=source_file,
                target_path=target_file,
                reason="both source and target changed since last sync",
            )

    if _contents_different(source_file, target_file):
        return PlanAction(
            type=PlanActionType.UPDATE,
            bed_id=bed_id,
            artifact_id=artifact_id,
            source_path=source_file,
            target_path=target_file,
            reason="content differs",
        )

    return PlanAction(
        type=PlanActionType.SKIP,
        bed_id=bed_id,
        artifact_id=artifact_id,
        source_path=source_file,
        target_path=target_file,
        reason="already in sync",
    )


def _contents_different(source_file: Path, target_file: Path) -> bool:
    source_bytes = source_file.read_bytes()
    target_bytes = target_file.read_bytes()
    if source_bytes == target_bytes:
        return False

    try:
        source_text = source_bytes.decode("utf-8")
        target_text = target_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return True

    return text_changed(source_text, target_text)


def _is_within(base: Path, path: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
