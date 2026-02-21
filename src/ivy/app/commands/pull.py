from __future__ import annotations

from pathlib import Path

from ivy.app.commands.base import BaseCommand
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.paths import garden_config_path
from ivy.infra.git.gateway import GitPythonGateway


class PullCommand(BaseCommand):
    def __init__(self, garden_id: str) -> None:
        self._garden_id = garden_id
        self._git = GitPythonGateway()

    def execute(self, context: ExecutionContext) -> CommandResult:
        config_path = garden_config_path(self._garden_id)
        if not config_path.exists():
            return CommandResult(exit_code=1, message=f"Garden config not found: {config_path}", payload={"kind": "error"})

        repo_path = config_path.parent
        if not self._git.is_repo(str(repo_path)):
            return CommandResult(
                exit_code=1,
                message=f"Garden is not a git repo: {repo_path}",
                payload={"kind": "error"},
            )
        if not self._git.status_clean(str(repo_path)):
            return CommandResult(
                exit_code=1,
                message=f"Garden repo is dirty: {repo_path}. Commit/stash changes before ivy pull.",
                payload={"kind": "error"},
            )
        result = self._git.pull_ff_only(str(repo_path))
        if result.exit_code != 0:
            return CommandResult(exit_code=1, message=result.message, payload={"kind": "error"})
        return CommandResult(
            exit_code=0,
            message=f"Pull complete for garden '{self._garden_id}' at {repo_path}",
            payload={"kind": "git_pull", "garden_id": self._garden_id, "repo_path": str(Path(repo_path).resolve())},
        )
