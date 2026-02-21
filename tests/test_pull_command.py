from __future__ import annotations

from pathlib import Path

from git import Repo
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def _configure_repo_identity(repo: Repo) -> None:
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "ivy-test")
        writer.set_value("user", "email", "ivy-test@example.com")


def test_pull_blocks_when_garden_repo_is_dirty() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        garden_root = Path(".ivy-home") / "gardens" / "default"
        repo = Repo.init(garden_root)
        _configure_repo_identity(repo)
        repo.index.add(["ivy.yaml"])
        repo.index.commit("init garden")
        (garden_root / "ivy.yaml").write_text("dirty: true\n", encoding="utf-8")

        result = runner.invoke(app, ["pull"], env=env)
        assert result.exit_code == 1
        assert "dirty" in result.stdout.lower()


def test_pull_ff_only_succeeds_for_clean_repo_with_remote() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed"], env=env).exit_code == 0

        root = Path.cwd()
        garden_root = root / ".ivy-home" / "gardens" / "default"
        origin_path = root / "origin.git"
        Repo.init(origin_path, bare=True)

        repo = Repo.init(garden_root)
        _configure_repo_identity(repo)
        repo.index.add(["ivy.yaml"])
        repo.index.commit("init garden")
        repo.create_remote("origin", str(origin_path.resolve()))
        repo.git.push("--set-upstream", "origin", repo.active_branch.name)

        result = runner.invoke(app, ["pull"], env=env)
        assert result.exit_code == 0
        assert "Pull complete" in result.stdout
