from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from ivy.domain.models.artifact import ArtifactSpec, BedTarget
from ivy.domain.models.context import ExecutionContext, RuntimeContext
from ivy.domain.models.plan import ExecutionPlan, PlanAction
from ivy.domain.models.state import StateEntry


def test_execution_context_builds() -> None:
    runtime = RuntimeContext(
        os="windows",
        arch="x86_64",
        hostname="box",
        username="jeff",
        box_id="box-1",
        project_root=Path("E:/workspaces/dream/ivy"),
    )
    ctx = ExecutionContext(command="plan", runtime=runtime, dry_run=True)
    assert ctx.command == "plan"
    assert ctx.dry_run is True


def test_artifact_default_direction_and_policy() -> None:
    artifact = ArtifactSpec(id="cursor_commands", source=Path("assets/cursor"))
    assert artifact.direction == "one_way"
    assert artifact.conflict_policy == "prompt"


def test_artifact_rejects_invalid_direction() -> None:
    try:
        ArtifactSpec(id="x", source=Path("a"), direction="invalid")  # type: ignore[arg-type]
        raised = False
    except ValidationError:
        raised = True
    assert raised is True


def test_plan_and_state_models_build() -> None:
    plan = ExecutionPlan(
        items=[
            PlanAction(
                type="COPY",
                bed_id="demo-bed",
                artifact_id="cursor_commands",
                source_path=Path("assets/a"),
                target_path=Path(".cursor/commands/a"),
                reason="source changed",
            )
        ]
    )
    state = StateEntry(
        artifact_id="cursor_commands",
        bed_path=".cursor/commands/a",
        last_applied_hash="abc123",
        last_applied_at=datetime.now(UTC),
        last_direction="source_to_bed",
    )
    assert len(plan.items) == 1
    assert state.artifact_id == "cursor_commands"
