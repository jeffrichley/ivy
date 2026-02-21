from __future__ import annotations

from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from ivy.domain.models.plan import CommandResult


class GitPythonGateway:
    """Git gateway implemented with GitPython."""

    def is_repo(self, repo_path: str) -> bool:
        try:
            Repo(repo_path)
            return True
        except (InvalidGitRepositoryError, NoSuchPathError):
            return False

    def status_clean(self, repo_path: str) -> bool:
        repo = Repo(repo_path)
        return not repo.is_dirty(untracked_files=True)

    def pull_ff_only(self, repo_path: str) -> CommandResult:
        repo = Repo(repo_path)
        try:
            repo.git.pull("--ff-only")
            return CommandResult(exit_code=0, message="git pull --ff-only succeeded")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, message=f"git pull --ff-only failed: {exc}")

    def push(self, repo_path: str) -> CommandResult:
        repo = Repo(repo_path)
        try:
            repo.git.push()
            return CommandResult(exit_code=0, message="git push succeeded")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, message=f"git push failed: {exc}")

    def has_remote(self, repo_path: str, remote_name: str = "origin") -> bool:
        repo = Repo(repo_path)
        return any(remote.name == remote_name for remote in repo.remotes)

    def has_staged_changes(self, repo_path: str) -> bool:
        repo = Repo(repo_path)
        try:
            return bool(repo.git.diff("--cached", "--name-only").strip())
        except Exception:  # noqa: BLE001
            return False

    def commit_paths(self, repo_path: str, paths: list[str], message: str) -> CommandResult:
        repo = Repo(repo_path)
        try:
            normalized: list[str] = []
            root = Path(repo.working_tree_dir or repo_path).resolve()
            for raw in paths:
                path = Path(raw).resolve()
                normalized.append(str(path.relative_to(root)))
            if normalized:
                repo.index.add(normalized)
            staged = repo.git.diff("--cached", "--name-only").strip()
            if not staged:
                return CommandResult(exit_code=0, message="no changes to commit", payload={"committed": False})
            commit = repo.index.commit(message)
            return CommandResult(
                exit_code=0,
                message=f"git commit succeeded: {commit.hexsha[:12]}",
                payload={"committed": True, "commit_id": commit.hexsha},
            )
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, message=f"git commit failed: {exc}")

    def init_repo(self, repo_path: str) -> CommandResult:
        try:
            Repo.init(repo_path)
            return CommandResult(exit_code=0, message=f"git init succeeded: {repo_path}")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, message=f"git init failed: {exc}")

    def clone_repo(self, url: str, repo_path: str) -> CommandResult:
        try:
            Repo.clone_from(url, repo_path)
            return CommandResult(exit_code=0, message=f"git clone succeeded: {url} -> {repo_path}")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, message=f"git clone failed: {exc}")

    def set_remote(self, repo_path: str, remote_name: str, url: str) -> CommandResult:
        try:
            repo = Repo(repo_path)
            existing = {remote.name: remote for remote in repo.remotes}
            if remote_name in existing:
                repo.git.remote("set-url", remote_name, url)
            else:
                repo.create_remote(remote_name, url)
            return CommandResult(exit_code=0, message=f"remote '{remote_name}' set to {url}")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, message=f"set remote failed: {exc}")
