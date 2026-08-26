from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class HolidayCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    date: date_type
    is_recurring: bool = False
    applicable_to: str = Field(default="all", max_length=40)


class HolidayUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    date: date_type | None = None
    is_recurring: bool | None = None
    applicable_to: str | None = Field(default=None, max_length=40)


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date_type
    is_recurring: bool
    applicable_to: str = "all"
