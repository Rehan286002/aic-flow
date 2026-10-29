from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """Request schema for password-based authentication."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Email cannot be empty.")
        clean = v.strip().lower()
        if "@" not in clean or clean.startswith("@") or clean.endswith("@"):
            raise ValueError("Invalid email format.")
        return clean


class UserProfile(BaseModel):
    """Sanitized user profile returned to clients (safe fields only)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    full_name: str
    email: str
    status: str


class RoleContext(BaseModel):
    """Active role assignment context representing granted role and scope."""

    model_config = ConfigDict(from_attributes=True)

    role_code: str
    institution_id: UUID | None = None
    review_team_id: UUID | None = None


class LoginResponse(BaseModel):
    """Response returned upon successful authentication.

    Note: The raw access token is conveyed exclusively via HttpOnly cookie
    and is never exposed in the response body.
    """

    message: str = "Login successful"
    user: UserProfile


class CurrentUserResponse(BaseModel):
    """Response schema containing the authenticated user profile and active role contexts."""

    user: UserProfile
    roles: list[RoleContext] = Field(default_factory=list)


class CSRFResponse(BaseModel):
    """Response schema containing the CSRF token."""

    csrf_token: str


class LogoutResponse(BaseModel):
    """Response schema returned upon logout."""

    message: str = "Logout successful"
