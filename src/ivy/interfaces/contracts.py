from __future__ import annotations

from typing import Protocol

from ivy.domain.models.artifact import ArtifactSpec
from ivy.domain.models.context import ExecutionContext, RuntimeContext
from ivy.domain.models.plan import CommandResult, ExecutionPlan
from ivy.domain.models.state import StateEntry


class ContextResolver(Protocol):
    def resolve(self, request: dict[str, str]) -> RuntimeContext: ...


class ConfigResolver(Protocol):
    def resolve(self, context: RuntimeContext, cli_overrides: dict[str, str]) -> dict: ...


class ArtifactCatalog(Protocol):
    def list_artifacts(self, effective_config: dict) -> list[ArtifactSpec]: ...


class SelectorEngine(Protocol):
    def select(
        self,
        catalog: list[ArtifactSpec],
        context: RuntimeContext,
        filters: list[str],
    ) -> list[ArtifactSpec]: ...


class PlanBuilder(Protocol):
    def build(self, artifacts: list[ArtifactSpec], context: ExecutionContext) -> ExecutionPlan: ...


class ApplyEngine(Protocol):
    def apply(self, plan: ExecutionPlan, dry_run: bool = False) -> CommandResult: ...


class StateStore(Protocol):
    def get(self, artifact_key: str, bed_key: str) -> StateEntry | None: ...

    def put(self, artifact_key: str, bed_key: str, entry: StateEntry) -> None: ...


class GitGateway(Protocol):
    def status_clean(self, repo_path: str) -> bool: ...

    def pull_ff_only(self, repo_path: str) -> CommandResult: ...

    def push(self, repo_path: str) -> CommandResult: ...

