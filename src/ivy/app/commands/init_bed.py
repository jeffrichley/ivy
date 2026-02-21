from __future__ import annotations

from pathlib import Path

from ivy.app.commands.base import BaseCommand
from ivy.domain.models.config import BedConfig, GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.yaml_io import read_yaml, write_yaml


class InitBedCommand(BaseCommand):
    def __init__(
        self,
        cwd: Path,
        bed_id: str,
        garden_config_path: Path | None = None,
        garden_id: str = "default",
        profile: str = "default",
        force: bool = False,
    ) -> None:
        self._cwd = cwd
        self._bed_id = bed_id
        self._garden_config_path = garden_config_path
        self._garden_id = garden_id
        self._profile = profile
        self._force = force

    def execute(self, context: ExecutionContext) -> CommandResult:
        config_path = self._cwd / ".ivy" / "bed.yaml"
        if config_path.exists() and not self._force:
            return CommandResult(exit_code=1, message=f"{config_path} already exists. Use --force to overwrite.")

        config = BedConfig.default(
            bed_id=self._bed_id,
            garden_id=self._garden_id,
            profile=self._profile,
            root=".",
        )
        write_yaml(config_path, config.model_dump(mode="json"))

        garden_config_path = self._garden_config_path
        if garden_config_path is None:
            return CommandResult(exit_code=0, message=f"Created {config_path}")

        if garden_config_path.exists():
            garden_config = GardenConfig.model_validate(read_yaml(garden_config_path))
            garden_config.upsert_bed(self._bed_id, str(self._cwd.resolve()))
            write_yaml(garden_config_path, garden_config.model_dump(mode="json"))
            return CommandResult(
                exit_code=0,
                message=f"Created {config_path} and updated {garden_config_path}",
            )

        return CommandResult(
            exit_code=0,
            message=f"Created {config_path}; garden config not found at {garden_config_path}",
        )
