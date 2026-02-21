from __future__ import annotations

from pathlib import Path

from ivy.app.commands.base import BaseCommand
from ivy.domain.models.config import GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.paths import garden_root
from ivy.infra.fs.yaml_io import write_yaml
from ivy.infra.git.gateway import GitPythonGateway


class GraftGardenCommand(BaseCommand):
    def __init__(
        self,
        garden_id: str,
        url: str | None,
        remote_name: str = "origin",
    ) -> None:
        self._garden_id = garden_id
        self._url = url
        self._remote_name = remote_name
        self._git = GitPythonGateway()

    def execute(self, context: ExecutionContext) -> CommandResult:
        root = garden_root(self._garden_id)
        config_path = root / "ivy.yaml"
        root_exists = root.exists()

        if not root_exists and self._url:
            clone_result = self._git.clone_repo(self._url, str(root))
            if clone_result.exit_code != 0:
                return CommandResult(exit_code=1, message=clone_result.message, payload={"kind": "error"})
        else:
            root.mkdir(parents=True, exist_ok=True)

        if not self._git.is_repo(str(root)):
            init_result = self._git.init_repo(str(root))
            if init_result.exit_code != 0:
                return CommandResult(exit_code=1, message=init_result.message, payload={"kind": "error"})

        if self._url:
            remote_result = self._git.set_remote(str(root), self._remote_name, self._url)
            if remote_result.exit_code != 0:
                return CommandResult(exit_code=1, message=remote_result.message, payload={"kind": "error"})

        created_config = False
        if not config_path.exists():
            config = GardenConfig.default(garden_id=self._garden_id)
            write_yaml(config_path, config.model_dump(mode="json"))
            created_config = True

        mode = "cloned" if not root_exists and self._url else ("initialized" if self._url else "local")
        remote_text = self._url if self._url else "none"
        return CommandResult(
            exit_code=0,
            message=(
                f"Garden '{self._garden_id}' grafted ({mode}) at {root}. "
                f"remote={remote_text}. ivy.yaml {'created' if created_config else 'present'}."
            ),
            payload={
                "kind": "garden_graft",
                "garden_id": self._garden_id,
                "path": str(Path(root).resolve()),
                "remote": remote_text,
                "created_config": created_config,
            },
        )
