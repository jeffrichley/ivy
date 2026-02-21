from __future__ import annotations

import json
import os
from pathlib import Path

from git import Repo
import yaml
from typer.testing import CliRunner

from ivy.cli.router import app


def _env_with_ivy_home() -> dict[str, str]:
    return {"IVY_HOME": str((Path.cwd() / ".ivy-home").resolve())}


def _configure_repo_identity(repo: Repo) -> None:
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "ivy-test")
        writer.set_value("user", "email", "ivy-test@example.com")


def _prepare_push_fixture(root: Path, env: dict[str, str]) -> tuple[Path, Path, Path]:
    runner = CliRunner()
    assert runner.invoke(app, ["seed"], env=env).exit_code == 0
    garden_root = root / ".ivy-home" / "gardens" / "default"
    cfg = garden_root / "ivy.yaml"
    src = garden_root / "assets" / "publish.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("base\n", encoding="utf-8")

    project = root / "publish-bed"
    project.mkdir(parents=True, exist_ok=True)
    os.chdir(project)
    try:
        runner.invoke(app, ["plant", "--bed-id", "publish-bed"], env=env)
    finally:
        os.chdir(root)

    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    data["artifacts"] = [
        {
            "id": "publish_artifact",
            "source": "assets/publish.md",
            "direction": "one_way",
            "targets": [{"bed_id": "publish-bed", "path": "publish.md"}],
        }
    ]
    cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    os.chdir(project)
    try:
        assert runner.invoke(app, ["sync"], env=env).exit_code == 0
        (project / "publish.md").write_text("bed edit\n", encoding="utf-8")
    finally:
        os.chdir(root)
    return garden_root, project, src


def test_push_without_flags_is_promotion_only_with_publish_payload() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        _, project, src = _prepare_push_fixture(root, env)

        os.chdir(project)
        try:
            result = runner.invoke(app, ["push", "--json"], env=env)
            assert result.exit_code == 0
            payload = json.loads(result.stdout)["payload"]
        finally:
            os.chdir(root)

        assert payload["publish"]["requested_commit"] is False
        assert payload["publish"]["requested_push"] is False
        assert payload["publish"]["committed"] is False
        assert payload["publish"]["pushed"] is False
        assert payload["publish"]["reason"] == "publish not requested"
        assert src.read_text(encoding="utf-8") == "bed edit\n"


def test_push_commit_creates_commit_for_promoted_changes_only() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        garden_root, project, src = _prepare_push_fixture(root, env)

        repo = Repo.init(garden_root)
        _configure_repo_identity(repo)
        repo.git.add(A=True)
        repo.index.commit("baseline")

        os.chdir(project)
        try:
            result = runner.invoke(app, ["push", "--commit", "--json"], env=env)
            assert result.exit_code == 0
            payload = json.loads(result.stdout)["payload"]
        finally:
            os.chdir(root)

        assert payload["publish"]["requested_commit"] is True
        assert payload["publish"]["requested_push"] is False
        assert payload["publish"]["committed"] is True
        assert payload["publish"]["pushed"] is False
        assert payload["publish"]["commit_id"]
        assert src.read_text(encoding="utf-8") == "bed edit\n"


def test_push_push_requires_commit_flag() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        env = _env_with_ivy_home()
        result = runner.invoke(app, ["push", "--push"], env=env)
        assert result.exit_code == 2
        assert "--push requires --commit" in result.stdout


def test_push_commit_and_push_succeeds_with_remote() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        garden_root, project, _ = _prepare_push_fixture(root, env)

        remote = root / "origin.git"
        Repo.init(remote, bare=True)

        repo = Repo.init(garden_root)
        _configure_repo_identity(repo)
        repo.git.add(A=True)
        repo.index.commit("baseline")
        repo.create_remote("origin", str(remote.resolve()))
        repo.git.push("--set-upstream", "origin", repo.active_branch.name)

        os.chdir(project)
        try:
            result = runner.invoke(app, ["push", "--commit", "--push", "--json"], env=env)
            assert result.exit_code == 0
            payload = json.loads(result.stdout)["payload"]
        finally:
            os.chdir(root)

        assert payload["publish"]["committed"] is True
        assert payload["publish"]["pushed"] is True
        assert payload["publish"]["reason"] == "commit and push succeeded"


def test_push_commit_and_push_fails_without_origin_remote() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        garden_root, project, _ = _prepare_push_fixture(root, env)

        repo = Repo.init(garden_root)
        _configure_repo_identity(repo)
        repo.git.add(A=True)
        repo.index.commit("baseline")

        os.chdir(project)
        try:
            result = runner.invoke(app, ["push", "--commit", "--push", "--json"], env=env)
            assert result.exit_code == 1
            payload = json.loads(result.stdout)["payload"]
        finally:
            os.chdir(root)

        assert payload["publish"]["committed"] is True
        assert payload["publish"]["pushed"] is False
        assert "no 'origin' remote" in payload["publish"]["reason"]


def test_push_commit_after_prior_plain_push_commits_managed_changes() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        root = Path.cwd()
        env = _env_with_ivy_home()
        garden_root, project, src = _prepare_push_fixture(root, env)

        repo = Repo.init(garden_root)
        _configure_repo_identity(repo)
        repo.git.add(A=True)
        repo.index.commit("baseline")

        os.chdir(project)
        try:
            first = runner.invoke(app, ["push"], env=env)
            assert first.exit_code == 0
            second = runner.invoke(app, ["push", "--commit", "--json"], env=env)
            assert second.exit_code == 0
            payload = json.loads(second.stdout)["payload"]
        finally:
            os.chdir(root)

        assert payload["publish"]["requested_commit"] is True
        assert payload["publish"]["committed"] is True
        assert payload["publish"]["commit_id"]
        assert src.read_text(encoding="utf-8") == "bed edit\n"
