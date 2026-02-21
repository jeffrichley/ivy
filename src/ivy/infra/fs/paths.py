from __future__ import annotations

import os
from pathlib import Path


def ivy_home() -> Path:
    raw = os.getenv("IVY_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".ivy").resolve()


def garden_root(garden_id: str) -> Path:
    return ivy_home() / "gardens" / garden_id


def garden_config_path(garden_id: str) -> Path:
    return garden_root(garden_id) / "ivy.yaml"


def state_file_path() -> Path:
    return ivy_home() / "state" / "state.json"


def find_bed_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / ".ivy" / "bed.yaml"
        if candidate.exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
