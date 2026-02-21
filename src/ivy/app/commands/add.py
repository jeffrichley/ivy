from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from ivy.app.commands.base import BaseCommand
from ivy.domain.models.config import ArtifactTarget, BedConfig, GardenArtifact, GardenConfig
from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.enums import ConflictPolicy, Direction
from ivy.domain.models.plan import CommandResult
from ivy.infra.fs.paths import find_bed_root, garden_config_path
from ivy.infra.fs.yaml_io import read_yaml, write_yaml


class AddCommand(BaseCommand):
    def __init__(self, cwd: Path, files: list[Path], all_files: bool = False, dry_run: bool = False) -> None:
        self._cwd = cwd
        self._files = files
        self._all_files = all_files
        self._dry_run = dry_run

    def execute(self, context: ExecutionContext) -> CommandResult:
        if self._all_files and self._files:
            return CommandResult(exit_code=2, message="Use explicit files or --all, not both.")
        if not self._all_files and not self._files:
            return CommandResult(exit_code=2, message="No files provided.")

        bed_root = find_bed_root(self._cwd)
        if bed_root is None:
            return CommandResult(
                exit_code=1,
                message="No .ivy/bed.yaml found in current directory or parents. Run `ivy plant` first.",
            )

        bed_cfg_path = bed_root / ".ivy" / "bed.yaml"
        bed_cfg = BedConfig.model_validate(read_yaml(bed_cfg_path))
        garden_cfg_path = garden_config_path(bed_cfg.garden.id)
        if not garden_cfg_path.exists():
            return CommandResult(exit_code=1, message=f"Garden config not found: {garden_cfg_path}")

        garden_cfg = GardenConfig.model_validate(read_yaml(garden_cfg_path))
        working_cfg = garden_cfg.model_copy(deep=True)
        requested_files = self._files if not self._all_files else _discover_bed_files(bed_root)
        if not requested_files:
            return CommandResult(
                exit_code=0,
                message="No candidate files found to add.",
                payload={"kind": "add_result", "garden_id": bed_cfg.garden.id, "files": [], "dry_run": self._dry_run},
            )

        added: list[str] = []

        for requested in requested_files:
            try:
                rel = _resolve_relative_target(requested, bed_root=bed_root, cwd=self._cwd)
            except ValueError as exc:
                return CommandResult(exit_code=1, message=str(exc))
            bed_file = (bed_root / rel).resolve()
            if not bed_file.exists() or not bed_file.is_file():
                return CommandResult(exit_code=1, message=f"File not found for add: {bed_file}")

            source_rel = Path("assets") / "shared" / rel
            source_abs = (garden_cfg_path.parent / source_rel).resolve()
            if not self._dry_run:
                source_abs.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bed_file, source_abs)

            artifact_id = _artifact_id_for(rel)
            artifact = next((item for item in working_cfg.artifacts if item.id == artifact_id), None)
            if artifact is None:
                artifact = GardenArtifact(
                    id=artifact_id,
                    source=source_rel.as_posix(),
                    direction=Direction.ONE_WAY,
                    conflict_policy=ConflictPolicy.PROMPT,
                    targets=[ArtifactTarget(path=rel.as_posix())],
                )
                working_cfg.artifacts.append(artifact)
            else:
                artifact.source = source_rel.as_posix()
                artifact.direction = Direction.ONE_WAY
                if not any(target.path == rel.as_posix() and target.bed_id is None for target in artifact.targets):
                    artifact.targets.append(ArtifactTarget(path=rel.as_posix()))

            added.append(rel.as_posix())

        working_cfg.artifacts = sorted(working_cfg.artifacts, key=lambda item: item.id)
        if not self._dry_run:
            write_yaml(garden_cfg_path, working_cfg.model_dump(mode="json", exclude_none=True))

        return CommandResult(
            exit_code=0,
            message=f"{'Planned' if self._dry_run else 'Added'} {len(added)} file(s) to managed artifacts.",
            payload={
                "kind": "add_result",
                "garden_id": bed_cfg.garden.id,
                "files": added,
                "dry_run": self._dry_run,
            },
        )


def _resolve_relative_target(requested: Path, bed_root: Path, cwd: Path) -> Path:
    candidate = requested
    if not candidate.is_absolute():
        candidate = (cwd / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        rel = candidate.relative_to(bed_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path must be inside bed root: {candidate}") from exc
    return rel


def _artifact_id_for(rel: Path) -> str:
    token = rel.as_posix().replace("/", "_").replace(".", "_").replace("-", "_")
    return f"shared_{token}".lower()


def _discover_bed_files(bed_root: Path) -> list[Path]:
    excluded = {".git", ".ivy", ".venv", "__pycache__"}
    found: list[Path] = []
    for candidate in bed_root.rglob("*"):
        if not candidate.is_file():
            continue
        if any(part in excluded for part in candidate.parts):
            continue
        found.append(candidate)
    return sorted(found)
