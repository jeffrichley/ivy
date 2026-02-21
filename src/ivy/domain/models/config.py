from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ivy.domain.models.enums import ConflictPolicy, Direction


class GardenMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _no_blank_id(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class GardenProfiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: str = Field(min_length=1)

    @field_validator("default")
    @classmethod
    def _no_blank_default(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class GardenBed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    path: str = Field(min_length=1)

    @field_validator("id", "path")
    @classmethod
    def _no_blank_values(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class GardenConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    garden: GardenMetadata
    profiles: GardenProfiles
    beds: list[GardenBed] = Field(default_factory=list)
    artifacts: list["GardenArtifact"] = Field(default_factory=list)

    @classmethod
    def default(cls, garden_id: str = "default") -> "GardenConfig":
        return cls(
            garden=GardenMetadata(id=garden_id),
            profiles=GardenProfiles(default="default"),
            beds=[],
            artifacts=[],
        )

    def upsert_bed(self, bed_id: str, path: str) -> None:
        for idx, bed in enumerate(self.beds):
            if bed.id == bed_id:
                self.beds[idx] = GardenBed(id=bed_id, path=path)
                return
        self.beds.append(GardenBed(id=bed_id, path=path))


class BedMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    registered_at: str = Field(min_length=1)
    root: str = Field(min_length=1)

    @field_validator("id", "registered_at", "root")
    @classmethod
    def _no_blank_values(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class BedGardenBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    profile: str = Field(min_length=1)

    @field_validator("id", "profile")
    @classmethod
    def _no_blank_values(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class BedOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: dict[str, str] = Field(default_factory=dict)
    disabled_artifacts: list[str] = Field(default_factory=list)


class BedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    bed: BedMetadata
    garden: BedGardenBinding
    overrides: BedOverrides = Field(default_factory=BedOverrides)

    @classmethod
    def default(
        cls,
        bed_id: str,
        garden_id: str = "default",
        profile: str = "default",
        root: Path | str = ".",
    ) -> "BedConfig":
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return cls(
            bed=BedMetadata(id=bed_id, registered_at=now, root=str(root)),
            garden=BedGardenBinding(id=garden_id, profile=profile),
            overrides=BedOverrides(),
        )


class ArtifactTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    bed_id: str | None = None

    @field_validator("path")
    @classmethod
    def _no_blank_path(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed

    @field_validator("bed_id")
    @classmethod
    def _normalize_bed_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


class GardenArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    direction: Direction = Direction.ONE_WAY
    conflict_policy: ConflictPolicy = ConflictPolicy.PROMPT
    selectors: dict[str, str] = Field(default_factory=dict)
    targets: list[ArtifactTarget] = Field(default_factory=list)

    @field_validator("id", "source")
    @classmethod
    def _no_blank_values(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed


GardenConfig.model_rebuild()
