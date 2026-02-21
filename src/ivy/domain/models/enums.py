from __future__ import annotations

from enum import Enum


class CommandName(str, Enum):
    ADD = "add"
    INIT = "init"
    INIT_BED = "init-bed"
    PLAN = "plan"
    SYNC = "sync"
    STATUS = "status"
    PULL = "pull"
    PUSH = "push"


class Direction(str, Enum):
    ONE_WAY = "one_way"
    TWO_WAY = "two_way"


class ConflictPolicy(str, Enum):
    PROMPT = "prompt"
    ABORT = "abort"
    SOURCE_WINS = "source_wins"
    BED_WINS = "bed_wins"
    MERGE = "merge"


class BedTargetMode(str, Enum):
    COPY = "copy"
    SYMLINK = "symlink"
    HARDLINK = "hardlink"


class PlanActionType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DRIFTED = "DRIFTED"
    BOTH_CHANGED = "BOTH_CHANGED"
    COPY = "COPY"
    RENDER = "RENDER"
    BACKUP = "BACKUP"
    DELETE = "DELETE"
    PROMOTE_BED_TO_SOURCE = "PROMOTE_BED_TO_SOURCE"
    SKIP = "SKIP"
    CONFLICT = "CONFLICT"


class SyncDirection(str, Enum):
    SOURCE_TO_BED = "source_to_bed"
    BED_TO_SOURCE = "bed_to_source"
