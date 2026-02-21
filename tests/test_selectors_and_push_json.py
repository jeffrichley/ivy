from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_plan_sync_only_selector_filters_actions() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        (garden_root / "assets").mkdir(parents=True, exist_ok=True)
        (garden_root / "assets" / "a.txt").write_text("A\n", encoding="utf-8")
        (garden_root / "assets" / "b.txt").write_text("B\n", encoding="utf-8")

        project = root / "selector-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "selector-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {"id": "art_a", "source": "assets/a.txt", "direction": "one_way", "targets": [{"bed_id": "selector-bed", "path": "a.txt"}]},
            {"id": "art_b", "source": "assets/b.txt", "direction": "one_way", "targets": [{"bed_id": "selector-bed", "path": "b.txt"}]},
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            plan_only = runner.invoke(app, ["plan", "--only", "art_a"], env=env)
            assert plan_only.exit_code == 0
            assert "art_a" in plan_only.stdout
            assert "art_b" not in plan_only.stdout

            sync_only = runner.invoke(app, ["sync", "--only", "art_a"], env=env)
            assert sync_only.exit_code == 0
            assert (project / "a.txt").exists()
            assert not (project / "b.txt").exists()
        finally:
            os.chdir(root)


def test_plan_bed_selector_and_push_json_output() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "doc.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("base\n", encoding="utf-8")

        p1 = root / "bed1"
        p2 = root / "bed2"
        p1.mkdir()
        p2.mkdir()

        os.chdir(p1)
        runner.invoke(app, ["plant", "--bed-id", "bed1"], env=env)
        os.chdir(p2)
        runner.invoke(app, ["plant", "--bed-id", "bed2"], env=env)
        os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "doc",
                "source": "assets/doc.md",
                "direction": "one_way",
                "targets": [{"bed_id": "bed1", "path": "doc.md"}, {"bed_id": "bed2", "path": "doc.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(p1)
        try:
            runner.invoke(app, ["sync"], env=env)
            (p1 / "doc.md").write_text("local bed1 edit\n", encoding="utf-8")
            push_json = runner.invoke(app, ["push", "--json", "--bed", "bed1"], env=env)
            assert push_json.exit_code == 0
            payload = json.loads(push_json.stdout)
            assert payload["payload"]["operation"] == "push"
            assert payload["payload"]["scope"] == "current"
            assert any(item["id"] == "bed1" for item in payload["payload"]["beds"])
        finally:
            os.chdir(root)

