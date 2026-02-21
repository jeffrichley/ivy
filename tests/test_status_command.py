from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_status_reports_in_sync_after_sync() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "status.txt"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("hello\n", encoding="utf-8")

        project = root / "status-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "status-bed"], env=env).exit_code == 0
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "status_file",
                "source": "assets/status.txt",
                "direction": "one_way",
                "targets": [{"bed_id": "status-bed", "path": "status.txt"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            status_result = runner.invoke(app, ["status"], env=env)
            assert status_result.exit_code == 0
            assert "IN_SYNC" in status_result.stdout
            assert "status_file" in status_result.stdout
        finally:
            os.chdir(root)


def test_status_reports_drifted_after_local_edit() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "status-local.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("base\n", encoding="utf-8")

        project = root / "status-local-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "status-local-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "status_local_file",
                "source": "assets/status-local.md",
                "direction": "one_way",
                "targets": [{"bed_id": "status-local-bed", "path": "status-local.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "status-local.md").write_text("local edit\n", encoding="utf-8")
            status_result = runner.invoke(app, ["status", "--json"], env=env)
            assert status_result.exit_code == 0
            payload = json.loads(status_result.stdout)
            statuses = payload["payload"]["statuses"]
            assert any(item["status"] == "DRIFTED" for item in statuses)
            assert any(item["artifact_id"] == "status_local_file" for item in statuses)
        finally:
            os.chdir(root)


def test_status_walks_up_directories_to_find_bed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        project = root / "walkup-bed"
        nested = project / "src" / "pkg"
        nested.mkdir(parents=True, exist_ok=True)

        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "walkup-bed"], env=env).exit_code == 0
        finally:
            os.chdir(root)

        os.chdir(nested)
        try:
            result = runner.invoke(app, ["status"], env=env)
            assert result.exit_code == 0
            assert "STATUS scope: current" in result.stdout
            assert "walkup-bed" in result.stdout
        finally:
            os.chdir(root)
