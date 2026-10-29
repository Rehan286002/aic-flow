from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import argon2.exceptions
import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError

from app.core.config import settings

# Reusable PasswordHash instance using recommended Argon2id configuration
_password_hash = PasswordHash.recommended()


class SecurityConfigError(RuntimeError):
    """Raised when security configuration is missing or invalid."""


class TokenValidationError(jwt.InvalidTokenError):
    """Raised when an access token fails validation (e.g. incorrect token type)."""


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: The plaintext password string to hash.

    Returns:
        The encoded Argon2id password hash string.

    Raises:
        ValueError: If the password is empty or not a string.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")

    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id encoded hash.

    Args:
        password: The plaintext password to check.
        password_hash: The stored Argon2id hash to verify against.

    Returns:
        True if the password matches the hash, False otherwise.
        Returns False safely on malformed hashes or invalid inputs.
    """
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    if not password or not password_hash:
        return False

    try:
        return _password_hash.verify(password, password_hash)
    except (PwdlibError, argon2.exceptions.Argon2Error, ValueError):
        return False


def _get_validated_secret_key() -> str:
    """Validate and return the JWT secret key, enforcing a 32-byte minimum for HS256."""
    secret_key = settings.jwt_secret_key
    if secret_key is None or not secret_key.get_secret_value():
        raise SecurityConfigError(
            "JWT_SECRET_KEY is not configured. Authentication cannot proceed."
        )

    secret_value = secret_key.get_secret_value()
    if len(secret_value.encode("utf-8")) < 32:
        raise SecurityConfigError("JWT_SECRET_KEY must be at least 32 bytes for HS256.")

    return secret_value


def create_access_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token using the configured HS256 algorithm.

    Authoritative access roles and scopes are intentionally omitted from the
    token payload and are loaded directly from PostgreSQL during authentication.

    Args:
        subject: The unique user identifier (UUID or string subject).
        expires_delta: Optional custom expiration duration. If omitted,
            uses the configured ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        The encoded and signed JWT access token string.

    Raises:
        SecurityConfigError: If JWT_SECRET_KEY is not configured or shorter than 32 bytes.
        ValueError: If subject is empty or expires_delta is non-positive.
    """
    if not subject:
        raise ValueError("Subject cannot be empty.")

    signing_secret = _get_validated_secret_key()

    now = datetime.now(UTC)
    if expires_delta is not None:
        if expires_delta.total_seconds() <= 0:
            raise ValueError("Token expiration delta must be positive.")
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expire,
        "jti": str(uuid4()),
        "token_type": "access",
    }

    return jwt.encode(
        payload,
        signing_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Verifies signature, issuer, audience, expiration, required claims, and
    token_type. Fails closed if the secret is not configured or insufficient.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded token payload dictionary.

    Raises:
        SecurityConfigError: If JWT_SECRET_KEY is not configured or shorter than 32 bytes.
        TokenValidationError: If token_type is not 'access' or format is invalid.
        jwt.PyJWTError: If signature, issuer, audience, or expiry validation fails.
    """
    if not isinstance(token, str) or not token:
        raise TokenValidationError("Token must be a non-empty string.")

    signing_secret = _get_validated_secret_key()

    payload = jwt.decode(
        token,
        signing_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={
            "require": ["sub", "iss", "aud", "iat", "exp", "jti", "token_type"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_iss": True,
            "verify_aud": True,
        },
    )

    if payload.get("token_type") != "access":
        raise TokenValidationError(
            f"Invalid token type: expected 'access', got '{payload.get('token_type')}'"
        )

    return payload
