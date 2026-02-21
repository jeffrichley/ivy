from __future__ import annotations

import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home(root: Path) -> dict[str, str]:
    return {"IVY_HOME": str((root / ".ivy-home").resolve())}


def test_add_registers_managed_artifact_and_copies_source() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home(root)

        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        project = root / "project-a"
        project.mkdir(parents=True, exist_ok=True)
        (project / "AGENTS.md").write_text("hello from bed\n", encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "project-a"], env=env).exit_code == 0
            add_result = runner.invoke(app, ["add", "AGENTS.md"], env=env)
            assert add_result.exit_code == 0
        finally:
            os.chdir(root)

        garden_root = root / ".ivy-home" / "gardens" / "default"
        source = garden_root / "assets" / "shared" / "AGENTS.md"
        assert source.exists()
        assert source.read_text(encoding="utf-8") == "hello from bed\n"

        cfg = yaml.safe_load((garden_root / "ivy.yaml").read_text(encoding="utf-8"))
        artifact = next(item for item in cfg["artifacts"] if item["id"] == "shared_agents_md")
        assert artifact["source"] == "assets/shared/AGENTS.md"
        assert artifact["targets"] == [{"path": "AGENTS.md"}]


def test_add_with_sync_spreads_to_other_beds() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home(root)
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        p1 = root / "p1"
        p2 = root / "p2"
        p1.mkdir()
        p2.mkdir()
        (p1 / "README.shared.md").write_text("shared content\n", encoding="utf-8")

        os.chdir(p1)
        runner.invoke(app, ["plant", "--bed-id", "p1"], env=env)
        os.chdir(p2)
        runner.invoke(app, ["plant", "--bed-id", "p2"], env=env)

        os.chdir(p1)
        try:
            result = runner.invoke(app, ["add", "README.shared.md", "--sync"], env=env)
            assert result.exit_code == 0
        finally:
            os.chdir(root)

        assert (p2 / "README.shared.md").exists()
        assert (p2 / "README.shared.md").read_text(encoding="utf-8") == "shared content\n"


def test_add_all_discovers_multiple_files_and_excludes_ivy_internal() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home(root)
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        project = root / "project-all"
        project.mkdir(parents=True, exist_ok=True)
        (project / "A.md").write_text("A\n", encoding="utf-8")
        (project / "nested").mkdir(parents=True, exist_ok=True)
        (project / "nested" / "B.md").write_text("B\n", encoding="utf-8")
        (project / ".git").mkdir(parents=True, exist_ok=True)
        (project / ".git" / "ignored.txt").write_text("ignored\n", encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "project-all"], env=env).exit_code == 0
            add_result = runner.invoke(app, ["add", "--all"], env=env)
            assert add_result.exit_code == 0
        finally:
            os.chdir(root)

        garden_cfg = yaml.safe_load((root / ".ivy-home" / "gardens" / "default" / "ivy.yaml").read_text(encoding="utf-8"))
        artifact_ids = {item["id"] for item in garden_cfg["artifacts"]}
        assert "shared_a_md" in artifact_ids
        assert "shared_nested_b_md" in artifact_ids
        assert "shared__git_ignored_txt" not in artifact_ids


def test_add_dry_run_makes_no_changes() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home(root)
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_cfg_path = root / ".ivy-home" / "gardens" / "default" / "ivy.yaml"

        project = root / "project-dry"
        project.mkdir(parents=True, exist_ok=True)
        (project / "DRY.md").write_text("dry\n", encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "project-dry"], env=env).exit_code == 0
            before = garden_cfg_path.read_text(encoding="utf-8")
            result = runner.invoke(app, ["add", "DRY.md", "--dry-run"], env=env)
            assert result.exit_code == 0
            assert "Planned 1 file" in result.stdout
        finally:
            os.chdir(root)

        after = garden_cfg_path.read_text(encoding="utf-8")
        assert before == after
        staged_source = root / ".ivy-home" / "gardens" / "default" / "assets" / "shared" / "DRY.md"
        assert not staged_source.exists()


def test_add_rejects_sync_with_dry_run() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home(root)
        result = runner.invoke(app, ["add", "X.md", "--dry-run", "--sync"], env=env)
        assert result.exit_code == 2
        assert "--sync cannot be used with --dry-run" in result.stdout
