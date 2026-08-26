from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    user_id: str = Field(pattern=r"^\d{6}$", description="6-digit user login ID (YY####)")
    password: str = Field(min_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login_id: str
    employee_id: str | None
    email: EmailStr
    contact_email: str | None = None
    name: str
    department_id: int | None
    org_level_id: int | None = None
    org_level_code: str | None = None
    org_level_name: str | None = None
    designation: str | None
    must_change_password: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageResponse(BaseModel):
    message: str


class RegeneratedCredentials(BaseModel):
    """One-time view of a freshly generated password. Never persisted."""

    login_id: str
    name: str
    generated_password: str
