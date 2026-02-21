from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ivy.domain.models.enums import PlanActionType


class PlanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: PlanActionType
    bed_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    source_path: Path | None = None
    target_path: Path | None = None
    reason: str = Field(min_length=1)

    @field_validator("bed_id", "artifact_id", "reason")
    @classmethod
    def _no_blank_strings(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PlanAction] = Field(default_factory=list)


class CommandResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exit_code: int = Field(ge=0, le=255)
    message: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def _no_blank_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed
