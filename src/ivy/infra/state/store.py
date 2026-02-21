from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ivy.infra.fs.paths import state_file_path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_applied(action_entries: list[dict[str, str]]) -> None:
    path = state_file_path()
    data: dict[str, Any]
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"version": 1, "entries": []}

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    index: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        key = (str(item.get("bed_id", "")), str(item.get("artifact_id", "")), str(item.get("target_path", "")))
        index[key] = item

    for entry in action_entries:
        key = (entry["bed_id"], entry["artifact_id"], entry["target_path"])
        index[key] = {
            "bed_id": entry["bed_id"],
            "artifact_id": entry["artifact_id"],
            "target_path": entry["target_path"],
            "last_applied_hash": entry["last_applied_hash"],
            "last_applied_at": entry["last_applied_at"],
        }

    data["entries"] = sorted(index.values(), key=lambda item: (item["bed_id"], item["artifact_id"], item["target_path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_state_index() -> dict[tuple[str, str, str], str]:
    path = state_file_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return {}

    index: dict[tuple[str, str, str], str] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        bed_id = str(item.get("bed_id", ""))
        artifact_id = str(item.get("artifact_id", ""))
        target_path = str(item.get("target_path", ""))
        last_hash = str(item.get("last_applied_hash", ""))
        if bed_id and artifact_id and target_path and last_hash:
            index[(bed_id, artifact_id, target_path)] = last_hash
    return index
