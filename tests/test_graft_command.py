from __future__ import annotations

import os
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


def _normalize_remote_url(value: str) -> str:
    cleaned = value.replace("\\\\", "\\")
    return os.path.normcase(os.path.normpath(cleaned))


def test_graft_existing_garden_initializes_repo_and_sets_remote() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        env = _env_with_ivy_home()
        assert runner.invoke(app, ["seed", "--garden-id", "work"], env=env).exit_code == 0

        root = Path.cwd()
        remote_bare = root / "work-remote.git"
        Repo.init(remote_bare, bare=True)

        result = runner.invoke(
            app,
            ["graft", "--garden-id", "work", "--url", str(remote_bare.resolve())],
            env=env,
        )
        assert result.exit_code == 0

        garden_repo_path = root / ".ivy-home" / "gardens" / "work"
        repo = Repo(garden_repo_path)
        assert _normalize_remote_url(repo.remotes.origin.url) == _normalize_remote_url(str(remote_bare.resolve()))
        assert (garden_repo_path / "ivy.yaml").exists()


def test_graft_new_garden_clones_repo_and_ensures_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        env = _env_with_ivy_home()
        root = Path.cwd()

        source_repo_path = root / "source-repo"
        source_repo_path.mkdir(parents=True, exist_ok=True)
        source_repo = Repo.init(source_repo_path)
        _configure_repo_identity(source_repo)
        (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
        source_repo.index.add(["README.md"])
        source_repo.index.commit("init")

        remote_bare = root / "fresh-remote.git"
        Repo.init(remote_bare, bare=True)
        source_repo.create_remote("origin", str(remote_bare.resolve()))
        source_repo.git.push("--set-upstream", "origin", source_repo.active_branch.name)

        result = runner.invoke(
            app,
            ["graft", "--garden-id", "fresh", "--url", str(remote_bare.resolve())],
            env=env,
        )
        assert result.exit_code == 0

        garden_path = root / ".ivy-home" / "gardens" / "fresh"
        repo = Repo(garden_path)
        assert _normalize_remote_url(repo.remotes.origin.url) == _normalize_remote_url(str(remote_bare.resolve()))
        assert (garden_path / "README.md").exists()
        assert (garden_path / "ivy.yaml").exists()
