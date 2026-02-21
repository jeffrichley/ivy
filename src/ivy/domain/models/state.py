from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ivy.domain.models.enums import SyncDirection


class StateEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    bed_path: str = Field(min_length=1)
    last_applied_hash: str = Field(min_length=1)
    last_applied_at: datetime
    last_direction: SyncDirection

    @field_validator("artifact_id", "bed_path", "last_applied_hash")
    @classmethod
    def _no_blank_strings(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed
