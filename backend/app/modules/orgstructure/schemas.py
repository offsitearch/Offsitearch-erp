from pydantic import BaseModel, ConfigDict, Field


class OrgLevelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=8, pattern=r"^L\d{1,2}$")
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    rank: int = Field(default=0, ge=0, le=99)


class OrgLevelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    rank: int | None = Field(default=None, ge=0, le=99)
    is_active: bool | None = None
