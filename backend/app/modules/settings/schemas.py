from pydantic import BaseModel, ConfigDict, Field, model_validator


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group: str
    key: str
    value: dict


class SettingUpsertIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group: str = Field(min_length=1, max_length=60)
    key: str = Field(min_length=1, max_length=120)
    value: dict

    @model_validator(mode="after")
    def validate_known_settings(self):
        KNOWN_SETTINGS = {
            "attendance": {
                "late_threshold_minutes": (int, 0, 480),
                "overtime_threshold_minutes": (int, 0, 480),
            },
            "leave": {
                "casual_annual": (int, 0, 100),
                "sick_annual": (int, 0, 100),
                "earned_annual": (int, 0, 100),
            },
        }
        group_keys = KNOWN_SETTINGS.get(self.group)
        if group_keys and self.key in group_keys:
            expected_type, min_val, max_val = group_keys[self.key]
            inner = self.value.get("value") if isinstance(self.value, dict) else None
            if inner is None or not isinstance(inner, expected_type):
                raise ValueError(
                    f"Setting '{self.key}' in group '{self.group}' expects type {expected_type.__name__}, "
                    f"got {type(inner).__name__ if inner is not None else 'None'}"
                )
            if inner < min_val or inner > max_val:
                raise ValueError(
                    f"Setting '{self.key}' in group '{self.group}' must be between {min_val} and {max_val}, "
                    f"got {inner}"
                )
        return self
