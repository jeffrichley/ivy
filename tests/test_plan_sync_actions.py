from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_plan_and_sync_execute_copy_then_noop() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()

        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_root = root / ".ivy-home" / "gardens" / "default"
        garden_config_path = garden_root / "ivy.yaml"

        source_file = garden_root / "assets" / "hello.txt"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("hello ivy\n", encoding="utf-8")

        project = root / "project-a"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "project-a"], env=env).exit_code == 0
        finally:
            os.chdir(root)

        data = yaml.safe_load(garden_config_path.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "hello_file",
                "source": "assets/hello.txt",
                "direction": "one_way",
                "targets": [{"bed_id": "project-a", "path": "synced/hello.txt"}],
            }
        ]
        garden_config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            plan_first = runner.invoke(app, ["plan"], env=env)
            assert plan_first.exit_code == 0
            assert "CREATE" in plan_first.stdout
            assert "hello_file" in plan_first.stdout

            sync_result = runner.invoke(app, ["sync"], env=env)
            assert sync_result.exit_code == 0
            target = project / "synced" / "hello.txt"
            assert target.exists()
            assert target.read_text(encoding="utf-8") == "hello ivy\n"

            plan_second = runner.invoke(app, ["plan"], env=env)
            assert plan_second.exit_code == 0
            assert "SKIP" in plan_second.stdout
            assert "hello_file" in plan_second.stdout
        finally:
            os.chdir(root)


def test_plan_json_and_state_file_recorded_after_sync() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()

        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_root = root / ".ivy-home" / "gardens" / "default"
        config_path = garden_root / "ivy.yaml"
        (garden_root / "assets").mkdir(parents=True, exist_ok=True)
        (garden_root / "assets" / "hello.txt").write_text("v1\n", encoding="utf-8")

        project = root / "project-json"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            assert runner.invoke(app, ["plant", "--bed-id", "project-json"], env=env).exit_code == 0
        finally:
            os.chdir(root)

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "hello_json",
                "source": "assets/hello.txt",
                "direction": "one_way",
                "targets": [{"bed_id": "project-json", "path": "hello.txt"}],
            }
        ]
        config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            plan_json = runner.invoke(app, ["plan", "--json"], env=env)
            assert plan_json.exit_code == 0
            payload = json.loads(plan_json.stdout)
            assert payload["payload"]["summary"]["CREATE"] >= 1

            sync_result = runner.invoke(app, ["sync"], env=env)
            assert sync_result.exit_code == 0
        finally:
            os.chdir(root)

        state_path = root / ".ivy-home" / "state" / "state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["version"] == 1
        assert any(entry["artifact_id"] == "hello_json" for entry in state["entries"])


def test_directory_and_multi_target_sync() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src_dir = garden_root / "assets" / "pack"
        (src_dir / "nested").mkdir(parents=True, exist_ok=True)
        (src_dir / "a.txt").write_text("A\n", encoding="utf-8")
        (src_dir / "nested" / "b.txt").write_text("B\n", encoding="utf-8")

        p1 = root / "p1"
        p2 = root / "p2"
        p1.mkdir()
        p2.mkdir()
        os.chdir(p1)
        runner.invoke(app, ["plant", "--bed-id", "p1"], env=env)
        os.chdir(p2)
        runner.invoke(app, ["plant", "--bed-id", "p2"], env=env)
        os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "shared_pack",
                "source": "assets/pack",
                "direction": "one_way",
                "targets": [
                    {"bed_id": "p1", "path": "synced/pack"},
                    {"bed_id": "p2", "path": "synced/pack"},
                ],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        sync_all = runner.invoke(app, ["sync", "--all"], env=env)
        assert sync_all.exit_code == 0
        assert (p1 / "synced" / "pack" / "a.txt").exists()
        assert (p1 / "synced" / "pack" / "nested" / "b.txt").exists()
        assert (p2 / "synced" / "pack" / "a.txt").exists()
        assert (p2 / "synced" / "pack" / "nested" / "b.txt").exists()


def test_sync_blocks_unsafe_target_escape() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "unsafe.txt"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("unsafe\n", encoding="utf-8")

        project = root / "unsafe-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "unsafe-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "unsafe_artifact",
                "source": "assets/unsafe.txt",
                "direction": "one_way",
                "targets": [{"bed_id": "unsafe-bed", "path": "..\\escape.txt"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            sync_result = runner.invoke(app, ["sync"], env=env)
            assert sync_result.exit_code == 1
            assert "conflict" in sync_result.stdout.lower()
            assert "unsafe" in sync_result.stdout.lower()
        finally:
            os.chdir(root)

        assert not (root / "escape.txt").exists()


def test_sync_does_not_overwrite_local_changes_after_initial_sync() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "local-protect.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("v1 from garden\n", encoding="utf-8")

        project = root / "protect-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "protect-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "protect_file",
                "source": "assets/local-protect.md",
                "direction": "one_way",
                "targets": [{"bed_id": "protect-bed", "path": "testme.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            first_sync = runner.invoke(app, ["sync"], env=env)
            assert first_sync.exit_code == 0
            target = project / "testme.md"
            assert target.read_text(encoding="utf-8") == "v1 from garden\n"

            target.write_text("local edit that should not be overwritten\n", encoding="utf-8")

            plan_after_local_edit = runner.invoke(app, ["plan"], env=env)
            assert plan_after_local_edit.exit_code == 0
            assert "DRIFTED" in plan_after_local_edit.stdout

            second_sync = runner.invoke(app, ["sync"], env=env)
            assert second_sync.exit_code == 1
            assert "drifted" in second_sync.stdout.lower()
            assert "local edit that should not be overwritten" in target.read_text(encoding="utf-8")
        finally:
            os.chdir(root)
