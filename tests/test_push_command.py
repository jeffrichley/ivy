from __future__ import annotations

import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_push_promotes_local_bed_change_to_garden() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "testme.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("hey 1\n", encoding="utf-8")

        project = root / "push-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "push-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "testme",
                "source": "assets/testme.md",
                "direction": "one_way",
                "targets": [{"bed_id": "push-bed", "path": "testme.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "testme.md").write_text("hey local\n", encoding="utf-8")
            push = runner.invoke(app, ["push"], env=env)
            assert push.exit_code == 0
            assert "PROMOTE_BED_TO_SOURCE" in push.stdout
        finally:
            os.chdir(root)

        assert src.read_text(encoding="utf-8") == "hey local\n"


def test_push_blocks_when_bed_and_garden_both_changed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "dual.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("base\n", encoding="utf-8")

        project = root / "dual-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "dual-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "dual",
                "source": "assets/dual.md",
                "direction": "one_way",
                "targets": [{"bed_id": "dual-bed", "path": "dual.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "dual.md").write_text("bed changed\n", encoding="utf-8")
        finally:
            os.chdir(root)

        src.write_text("garden changed\n", encoding="utf-8")

        os.chdir(project)
        try:
            push = runner.invoke(app, ["push"], env=env)
            assert push.exit_code == 1
            assert "both_changed" in push.stdout.lower()
        finally:
            os.chdir(root)

        assert src.read_text(encoding="utf-8") == "garden changed\n"
