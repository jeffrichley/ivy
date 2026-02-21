from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def test_sync_walks_up_directories_to_find_bed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = {"IVY_HOME": str((root / ".ivy-home").resolve())}
        project = root / "project-a"
        nested = project / "src" / "module"
        nested.mkdir(parents=True)

        os.chdir(project)
        try:
            assert runner.invoke(app, ["seed"], env=env).exit_code == 0
            plant_result = runner.invoke(app, ["plant", "--bed-id", "project-a"], env=env)
            assert plant_result.exit_code == 0

            os.chdir(nested)
            sync_result = runner.invoke(app, ["sync"], env=env)
            assert sync_result.exit_code == 0
            assert "SYNC scope: current" in sync_result.stdout
            assert "project-a" in sync_result.stdout
        finally:
            os.chdir(root)


def test_plan_all_scopes_to_all_registered_beds_in_stable_order() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()

        runner.invoke(app, ["seed", "--garden-id", "work"], env=env)

        beta = root / "beta"
        alpha = root / "alpha"
        beta.mkdir(parents=True)
        alpha.mkdir(parents=True)

        os.chdir(beta)
        runner.invoke(app, ["plant", "--garden-id", "work", "--bed-id", "beta-bed"], env=env)
        os.chdir(alpha)
        runner.invoke(app, ["plant", "--garden-id", "work", "--bed-id", "alpha-bed"], env=env)
        os.chdir(root)

        plan_result = runner.invoke(app, ["plan", "--all", "--garden-id", "work"], env=env)
        assert plan_result.exit_code == 0
        assert "PLAN scope: all" in plan_result.stdout
        assert "work" in plan_result.stdout

        alpha_idx = plan_result.stdout.find("alpha-bed")
        beta_idx = plan_result.stdout.find("beta-bed")
        assert alpha_idx != -1
        assert beta_idx != -1
        assert alpha_idx < beta_idx
