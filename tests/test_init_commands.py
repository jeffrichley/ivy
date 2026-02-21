from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_seed_writes_default_ivy_yaml_to_global_location() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["seed"], env=_env_with_ivy_home())
        assert result.exit_code == 0
        config_path = Path(".ivy-home") / "gardens" / "default" / "ivy.yaml"
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["garden"]["id"] == "default"
        assert data["profiles"]["default"] == "default"
        assert data["beds"] == []
        assert data["artifacts"] == []


def test_seed_here_writes_ivy_yaml_to_current_directory() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["seed", "--here"])
        assert result.exit_code == 0
        assert Path("ivy.yaml").exists()


def test_plant_writes_default_bed_yaml() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["plant", "--bed-id", "demo-bed"])
        assert result.exit_code == 0
        config_path = Path(".ivy") / "bed.yaml"
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["bed"]["id"] == "demo-bed"
        assert data["bed"]["root"] == "."
        assert data["garden"]["id"] == "default"
        assert data["garden"]["profile"] == "default"
        assert data["overrides"]["targets"] == {}
        assert data["overrides"]["disabled_artifacts"] == []


def test_seed_does_not_overwrite_without_force() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        seed_result = runner.invoke(app, ["seed"], env=_env_with_ivy_home())
        assert seed_result.exit_code == 0

        config_path = Path(".ivy-home") / "gardens" / "default" / "ivy.yaml"
        original = config_path.read_text(encoding="utf-8")
        result = runner.invoke(app, ["seed"], env=_env_with_ivy_home())
        assert result.exit_code == 1
        assert config_path.read_text(encoding="utf-8") == original


def test_plant_force_overwrites_existing_file() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        bed_path = Path(".ivy") / "bed.yaml"
        bed_path.parent.mkdir(parents=True, exist_ok=True)
        bed_path.write_text("version: 99\n", encoding="utf-8")
        result = runner.invoke(app, ["plant", "--bed-id", "new-bed", "--force"])
        assert result.exit_code == 0
        data = yaml.safe_load(bed_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["bed"]["id"] == "new-bed"


def test_plant_updates_global_ivy_yaml_with_bed_location() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        init_result = runner.invoke(app, ["seed", "--garden-id", "work"], env=_env_with_ivy_home())
        assert init_result.exit_code == 0

        bed_result = runner.invoke(app, ["plant", "--bed-id", "demo-bed", "--garden-id", "work"], env=_env_with_ivy_home())
        assert bed_result.exit_code == 0

        garden_path = Path(".ivy-home") / "gardens" / "work" / "ivy.yaml"
        garden = yaml.safe_load(garden_path.read_text(encoding="utf-8"))
        beds = garden["beds"]
        assert len(beds) == 1
        assert beds[0]["id"] == "demo-bed"
        assert beds[0]["path"] == str(Path.cwd().resolve())


def test_init_and_init_bed_aliases_still_work() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        seed_alias = runner.invoke(app, ["init"], env=_env_with_ivy_home())
        assert seed_alias.exit_code == 0
        assert (Path(".ivy-home") / "gardens" / "default" / "ivy.yaml").exists()

        plant_alias = runner.invoke(app, ["init-bed", "--bed-id", "legacy-bed"], env=_env_with_ivy_home())
        assert plant_alias.exit_code == 0
        assert (Path(".ivy") / "bed.yaml").exists()


def test_seed_first_run_prints_welcome_banner() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        first = runner.invoke(app, ["seed"], env=_env_with_ivy_home())
        assert first.exit_code == 0
        assert "Welcome to Ivy" in first.stdout
        assert "Created" in first.stdout

        second = runner.invoke(app, ["seed"], env=_env_with_ivy_home())
        assert second.exit_code == 1
        assert "Welcome to Ivy" not in second.stdout
