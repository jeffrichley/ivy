from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ivy.domain.models.enums import BedTargetMode, ConflictPolicy, Direction


class BedTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    path: Path
    mode: BedTargetMode = BedTargetMode.COPY

    @field_validator("id")
    @classmethod
    def _no_blank_id(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class ArtifactSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source: Path
    beds: list[BedTarget] = Field(default_factory=list)
    direction: Direction = Direction.ONE_WAY
    conflict_policy: ConflictPolicy = ConflictPolicy.PROMPT
    selectors: dict[str, str] = Field(default_factory=dict)
    template: bool = False

    @field_validator("id")
    @classmethod
    def _no_blank_id(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed

    @field_validator("selectors")
    @classmethod
    def _validate_selectors(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, raw in value.items():
            normalized_key = key.strip()
            normalized_value = raw.strip()
            if not normalized_key:
                raise ValueError("selector key must not be blank")
            if not normalized_value:
                raise ValueError(f"selector value for '{normalized_key}' must not be blank")
            cleaned[normalized_key] = normalized_value
        return cleaned
