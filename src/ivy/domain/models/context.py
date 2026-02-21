from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ivy.domain.models.enums import CommandName


class RuntimeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    os: str = Field(min_length=1)
    arch: str = Field(min_length=1)
    hostname: str = Field(min_length=1)
    username: str = Field(min_length=1)
    box_id: str = Field(min_length=1)
    project_root: Path | None = None
    garden_id: str | None = None
    profile: str | None = None

    @field_validator("os", "arch", "hostname", "username", "box_id")
    @classmethod
    def _no_blank_strings(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class ExecutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: CommandName
    runtime: RuntimeContext
    dry_run: bool = False
    explain: bool = False
    filters: list[str] = Field(default_factory=list)

    @field_validator("filters")
    @classmethod
    def _validate_filters(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        return cleaned
