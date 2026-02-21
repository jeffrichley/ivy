from __future__ import annotations

import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_sync_source_wins_overwrites_local_drift() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "policy.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("garden\n", encoding="utf-8")

        project = root / "policy-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "policy-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "policy_file",
                "source": "assets/policy.md",
                "direction": "one_way",
                "conflict_policy": "source_wins",
                "targets": [{"bed_id": "policy-bed", "path": "policy.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "policy.md").write_text("local edit\n", encoding="utf-8")
            resync = runner.invoke(app, ["sync"], env=env)
            assert resync.exit_code == 0
            assert (project / "policy.md").read_text(encoding="utf-8") == "garden\n"
        finally:
            os.chdir(root)


def test_sync_prompt_policy_falls_back_to_abort_non_interactive() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "prompt.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("garden\n", encoding="utf-8")

        project = root / "prompt-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "prompt-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "prompt_file",
                "source": "assets/prompt.md",
                "direction": "one_way",
                "conflict_policy": "prompt",
                "targets": [{"bed_id": "prompt-bed", "path": "prompt.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "prompt.md").write_text("local drift\n", encoding="utf-8")
            sync_result = runner.invoke(app, ["sync"], env=env)
            assert sync_result.exit_code == 1
            assert "DRIFTED" in sync_result.stdout
            assert "prompt_file" in sync_result.stdout
        finally:
            os.chdir(root)


def test_push_bed_wins_promotes_when_both_changed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "push-policy.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("base\n", encoding="utf-8")

        project = root / "push-policy-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "push-policy-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "push_policy_file",
                "source": "assets/push-policy.md",
                "direction": "one_way",
                "conflict_policy": "bed_wins",
                "targets": [{"bed_id": "push-policy-bed", "path": "push-policy.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "push-policy.md").write_text("bed update\n", encoding="utf-8")
        finally:
            os.chdir(root)

        src.write_text("garden update\n", encoding="utf-8")

        os.chdir(project)
        try:
            push_result = runner.invoke(app, ["push"], env=env)
            assert push_result.exit_code == 0
        finally:
            os.chdir(root)

        assert src.read_text(encoding="utf-8") == "bed update\n"


def test_push_source_wins_skips_when_both_changed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0
        garden_root = root / ".ivy-home" / "gardens" / "default"
        cfg = garden_root / "ivy.yaml"
        src = garden_root / "assets" / "push-source-wins.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("base\n", encoding="utf-8")

        project = root / "push-source-bed"
        project.mkdir(parents=True, exist_ok=True)
        os.chdir(project)
        try:
            runner.invoke(app, ["plant", "--bed-id", "push-source-bed"], env=env)
        finally:
            os.chdir(root)

        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        data["artifacts"] = [
            {
                "id": "push_source_wins_file",
                "source": "assets/push-source-wins.md",
                "direction": "one_way",
                "conflict_policy": "source_wins",
                "targets": [{"bed_id": "push-source-bed", "path": "push-source-wins.md"}],
            }
        ]
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        os.chdir(project)
        try:
            assert runner.invoke(app, ["sync"], env=env).exit_code == 0
            (project / "push-source-wins.md").write_text("bed update\n", encoding="utf-8")
        finally:
            os.chdir(root)

        src.write_text("garden update\n", encoding="utf-8")

        os.chdir(project)
        try:
            push_result = runner.invoke(app, ["push"], env=env)
            assert push_result.exit_code == 0
            assert "SKIP" in push_result.stdout
        finally:
            os.chdir(root)

        assert src.read_text(encoding="utf-8") == "garden update\n"
