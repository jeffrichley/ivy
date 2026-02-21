from __future__ import annotations

from typing import Literal

from ivy.domain.models.enums import ConflictPolicy, PlanActionType
from ivy.domain.models.plan import PlanAction

ConflictMode = Literal["sync", "push"]


def apply_conflict_policy(
    actions: list[PlanAction],
    mode: ConflictMode,
    policies: dict[str, ConflictPolicy],
    interactive: bool,
) -> tuple[list[PlanAction], str | None]:
    resolved: list[PlanAction] = []
    for action in actions:
        if action.type not in (PlanActionType.CONFLICT, PlanActionType.DRIFTED, PlanActionType.BOTH_CHANGED):
            resolved.append(action)
            continue

        policy = policies.get(action.artifact_id, ConflictPolicy.PROMPT)
        if policy == ConflictPolicy.PROMPT:
            if not interactive:
                return resolved + [action], (
                    f"{mode} blocked by conflict policy: artifact={action.artifact_id} policy=prompt "
                    f"requires interaction; non-interactive fallback=abort"
                )
            return resolved + [action], (
                f"{mode} blocked by conflict policy: artifact={action.artifact_id} policy=prompt "
                f"interactive prompt flow not implemented yet"
            )

        if policy == ConflictPolicy.ABORT:
            return resolved + [action], (
                f"{mode} blocked by conflict policy: artifact={action.artifact_id} policy=abort "
                f"reason={action.reason}"
            )

        if policy == ConflictPolicy.MERGE:
            return resolved + [action], (
                f"{mode} blocked by conflict policy: artifact={action.artifact_id} policy=merge "
                f"merge strategy not implemented"
            )

        if mode == "sync":
            if policy == ConflictPolicy.SOURCE_WINS:
                resolved.append(
                    action.model_copy(update={"type": PlanActionType.UPDATE, "reason": f"{action.reason}; policy=source_wins"})
                )
                continue
            if policy == ConflictPolicy.BED_WINS:
                resolved.append(
                    action.model_copy(update={"type": PlanActionType.SKIP, "reason": f"{action.reason}; policy=bed_wins"})
                )
                continue
            return resolved, f"sync blocked: unsupported conflict policy '{policy.value}'"

        if mode == "push":
            if policy == ConflictPolicy.BED_WINS:
                resolved.append(
                    action.model_copy(
                        update={"type": PlanActionType.PROMOTE_BED_TO_SOURCE, "reason": f"{action.reason}; policy=bed_wins"}
                    )
                )
                continue
            if policy == ConflictPolicy.SOURCE_WINS:
                resolved.append(
                    action.model_copy(update={"type": PlanActionType.SKIP, "reason": f"{action.reason}; policy=source_wins"})
                )
                continue
            return resolved, f"push blocked: unsupported conflict policy '{policy.value}'"

    return resolved, None
