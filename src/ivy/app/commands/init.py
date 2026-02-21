from __future__ import annotations

from pathlib import Path

from ivy.app.commands.base import BaseCommand
from ivy.domain.models.config import GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.yaml_io import write_yaml


class InitGardenCommand(BaseCommand):
    def __init__(self, target_dir: Path, garden_id: str, force: bool = False) -> None:
        self._target_dir = target_dir
        self._garden_id = garden_id
        self._force = force

    def execute(self, context: ExecutionContext) -> CommandResult:
        config_path = self._target_dir / "ivy.yaml"
        existed = config_path.exists()
        if existed and not self._force:
            return CommandResult(exit_code=1, message=f"{config_path} already exists. Use --force to overwrite.")

        config = GardenConfig.default(garden_id=self._garden_id)
        write_yaml(config_path, config.model_dump(mode="json"))
        return CommandResult(
            exit_code=0,
            message=f"Created {config_path}",
            payload={"first_seed": not existed},
        )
