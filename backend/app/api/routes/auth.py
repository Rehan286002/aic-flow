import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_role_assignments, get_current_user, verify_csrf
from app.core.config import settings
from app.core.security import SecurityConfigError, create_access_token, verify_password
from app.db.session import get_db
from app.models.enums import UserStatus
from app.models.user import User
from app.schemas.auth import (
    CSRFResponse,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RoleContext,
    UserProfile,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf", response_model=CSRFResponse)
def get_csrf_token(request: Request, response: Response) -> CSRFResponse:
    """Generate or retrieve the CSRF token.

    Supports multi-tab sessions by returning the existing CSRF token if one is
    already present in the request cookie. If missing, a new token is created and
    set as an accessible (non-HttpOnly) cookie for client-side inclusion in the
    X-CSRF-Token header.
    """
    existing_csrf = request.cookies.get(settings.csrf_cookie_name)
    if existing_csrf and len(existing_csrf) >= 16:
        return CSRFResponse(csrf_token=existing_csrf)

    new_csrf = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=new_csrf,
        httponly=False,
        secure=settings.is_cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )
    return CSRFResponse(csrf_token=new_csrf)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(verify_csrf)],
) -> LoginResponse:
    """Authenticate user with email and password, setting an HttpOnly access cookie.

    Validates credentials against Argon2id password hashes, checks active status,
    updates last_login_at timestamp, and issues an access JWT within an HttpOnly cookie.
    The JWT token is never returned in the JSON response body.
    """
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))

    # Generic credential check prevents account enumeration
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is not active (status: {user.status.value}).",
        )

    try:
        access_token = create_access_token(subject=user.user_id)
    except SecurityConfigError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service configuration error.",
        )

    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )

    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    return LoginResponse(
        message="Login successful",
        user=UserProfile.model_validate(user),
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUserResponse:
    """Retrieve the safe profile of the currently authenticated user including active role contexts."""
    active_assignments = get_active_role_assignments(current_user, db)
    role_contexts = [
        RoleContext(
            role_code=a.role_code,
            institution_id=a.institution_id,
            review_team_id=a.review_team_id,
        )
        for a in active_assignments
    ]
    return CurrentUserResponse(
        user=UserProfile.model_validate(current_user),
        roles=role_contexts,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    _: Annotated[str, Depends(verify_csrf)],
) -> LogoutResponse:
    """Clear access and CSRF authentication cookies.

    Note: This clears client authentication cookies. Stateless JWT tokens remain
    cryptographically valid until expiration unless a token revocation list/blocklist
    is implemented in a future phase.
    """
    response.delete_cookie(
        key=settings.access_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.is_cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.is_cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )

    return LogoutResponse(message="Logout successful")
