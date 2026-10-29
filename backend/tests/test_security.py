import secrets
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure backend root is in sys.path for pytest discovery
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import jwt
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, settings
from app.core.security import (
    SecurityConfigError,
    TokenValidationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def ephemeral_jwt_secret(monkeypatch):
    """Provide a temporary 32-byte secret for JWT tests and ensure cleanup."""
    secret = secrets.token_urlsafe(32)
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr(secret))
    return secret


# ==============================================================================
# Password Hashing and Verification Tests
# ==============================================================================


def test_password_hash_and_verify_success():
    """Verify that a password is correctly hashed and verified."""
    raw_password = "SecureVerificationPassword#2026"
    encoded_hash = hash_password(raw_password)

    assert isinstance(encoded_hash, str)
    assert verify_password(raw_password, encoded_hash) is True


def test_password_verify_incorrect_fails():
    """Verify that an incorrect password fails verification against a valid hash."""
    raw_password = "CorrectPassword123!"
    encoded_hash = hash_password(raw_password)

    assert verify_password("WrongPassword123!", encoded_hash) is False


def test_password_hash_starts_with_argon2id():
    """Verify that generated hashes explicitly use the Argon2id algorithm format."""
    encoded_hash = hash_password("EphemeralTestPassword123!")

    assert encoded_hash.startswith("$argon2id$")


def test_password_verify_malformed_hash_safely_rejected():
    """Verify that malformed or corrupted hashes return False safely without raising exceptions."""
    malformed_hashes = [
        "not-a-valid-hash",
        "$argon2id$v=19$m=65536,t=3,p=4$corrupted_payload",
        "12345",
        "pbkdf2:sha256:invalid",
        "   ",
    ]

    for bad_hash in malformed_hashes:
        assert verify_password("AnyPassword123!", bad_hash) is False

    # Also confirm non-string or None inputs return False safely
    assert verify_password("AnyPassword123!", None) is False  # type: ignore[arg-type]


def test_password_empty_handling():
    """Verify that empty password inputs are rejected appropriately."""
    # Empty password must raise ValueError on hashing
    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password("")

    # None input must raise ValueError on hashing
    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password(None)  # type: ignore[arg-type]

    # Empty string or empty hash on verify must return False safely
    valid_hash = hash_password("ValidPassword123!")
    assert verify_password("", valid_hash) is False
    assert verify_password("ValidPassword123!", "") is False
    assert verify_password("", "") is False


# ==============================================================================
# JWT Creation and Decoding Tests
# ==============================================================================


def test_jwt_valid_creation_and_decoding(ephemeral_jwt_secret):
    """Verify that a valid token can be created, decoded, and validated."""
    subject = "user-synthetic-001"
    token = create_access_token(subject=subject)

    assert isinstance(token, str)
    assert len(token) > 0

    decoded = decode_access_token(token)
    assert decoded["sub"] == subject
    assert decoded["token_type"] == "access"


def test_jwt_required_claims_present(ephemeral_jwt_secret):
    """Verify that all required claims are included in the decoded access token."""
    subject = "user-synthetic-002"
    token = create_access_token(subject=subject)
    decoded = decode_access_token(token)

    expected_claims = {"sub", "iss", "aud", "iat", "exp", "jti", "token_type"}
    for claim in expected_claims:
        assert claim in decoded, (
            f"Required claim '{claim}' is missing from decoded token"
        )

    assert decoded["iss"] == settings.jwt_issuer
    assert decoded["aud"] == settings.jwt_audience
    assert decoded["token_type"] == "access"
    assert decoded["exp"] > decoded["iat"]


def test_jwt_subject_preserved_string_and_uuid(ephemeral_jwt_secret):
    """Verify that subject is accurately preserved when passed as str or UUID."""
    # Test string subject
    str_subject = "inst-user-rehan-01"
    str_token = create_access_token(subject=str_subject)
    assert decode_access_token(str_token)["sub"] == str_subject

    # Test UUID subject
    user_uuid = uuid.uuid4()
    uuid_token = create_access_token(subject=user_uuid)
    assert decode_access_token(uuid_token)["sub"] == str(user_uuid)


def test_jwt_unique_token_identifier(ephemeral_jwt_secret):
    """Verify that separate tokens for the same subject have unique jti claims."""
    subject = "auditor-case-review-01"
    token_a = create_access_token(subject=subject)
    token_b = create_access_token(subject=subject)

    payload_a = decode_access_token(token_a)
    payload_b = decode_access_token(token_b)

    assert payload_a["jti"] != payload_b["jti"]
    assert uuid.UUID(payload_a["jti"])
    assert uuid.UUID(payload_b["jti"])


def test_jwt_expired_token_rejected(ephemeral_jwt_secret):
    """Verify that an expired token is rejected with ExpiredSignatureError."""
    # Forge a token whose exp is in the past
    past_time = datetime.now(UTC) - timedelta(minutes=10)
    issued_time = past_time - timedelta(minutes=30)
    expired_payload = {
        "sub": "user-expired-01",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_time,
        "exp": past_time,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }
    expired_token = jwt.encode(
        expired_payload,
        ephemeral_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_jwt_tampered_token_rejected(ephemeral_jwt_secret):
    """Verify that modifying the payload or signature causes token rejection."""
    token = create_access_token(subject="user-tamper-test")
    header, payload, signature = token.split(".")

    # Tamper with the signature bytes
    tampered_sig = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered_token = f"{header}.{payload}.{tampered_sig}"

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(tampered_token)


def test_jwt_wrong_signing_secret_rejected(ephemeral_jwt_secret):
    """Verify that a token signed with an unknown secret is rejected."""
    wrong_secret = secrets.token_urlsafe(32)
    foreign_payload = {
        "sub": "user-foreign-key",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }
    foreign_token = jwt.encode(
        foreign_payload,
        wrong_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(foreign_token)


def test_jwt_wrong_issuer_or_audience_rejected(ephemeral_jwt_secret):
    """Verify that tokens with unexpected issuer or audience are rejected."""
    valid_base = {
        "sub": "user-claim-test",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }

    # Wrong issuer
    bad_iss_payload = {
        **valid_base,
        "iss": "untrusted-issuer",
        "aud": settings.jwt_audience,
    }
    bad_iss_token = jwt.encode(
        bad_iss_payload,
        ephemeral_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidIssuerError):
        decode_access_token(bad_iss_token)

    # Wrong audience
    bad_aud_payload = {
        **valid_base,
        "iss": settings.jwt_issuer,
        "aud": "foreign-client-app",
    }
    bad_aud_token = jwt.encode(
        bad_aud_payload,
        ephemeral_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidAudienceError):
        decode_access_token(bad_aud_token)


def test_jwt_incorrect_token_type_rejected(ephemeral_jwt_secret):
    """Verify that tokens with token_type other than 'access' are rejected."""
    refresh_payload = {
        "sub": "user-refresh-test",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
        "token_type": "refresh",
    }
    refresh_token = jwt.encode(
        refresh_payload,
        ephemeral_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenValidationError, match="expected 'access'"):
        decode_access_token(refresh_token)


def test_jwt_missing_secret_fails_closed(monkeypatch):
    """Verify that both token creation and decoding fail closed when secret is not configured."""
    # Test None secret
    monkeypatch.setattr(settings, "jwt_secret_key", None)

    with pytest.raises(SecurityConfigError, match="JWT_SECRET_KEY is not configured"):
        create_access_token(subject="user-fail-closed")

    with pytest.raises(SecurityConfigError, match="JWT_SECRET_KEY is not configured"):
        decode_access_token(token="dummy.jwt.token")

    # Test empty string secret
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr(""))

    with pytest.raises(SecurityConfigError, match="JWT_SECRET_KEY is not configured"):
        create_access_token(subject="user-fail-closed")

    with pytest.raises(SecurityConfigError, match="JWT_SECRET_KEY is not configured"):
        decode_access_token(token="dummy.jwt.token")


def test_jwt_custom_expires_delta(ephemeral_jwt_secret):
    """Verify that custom expires_delta overrides the default expiration duration."""
    custom_delta = timedelta(minutes=45)
    token = create_access_token(subject="user-delta-test", expires_delta=custom_delta)
    decoded = decode_access_token(token)

    expected_duration = decoded["exp"] - decoded["iat"]
    assert expected_duration == 45 * 60


def test_jwt_invalid_expires_delta_rejected(ephemeral_jwt_secret):
    """Verify that non-positive expires_delta raises ValueError."""
    with pytest.raises(ValueError, match="Token expiration delta must be positive"):
        create_access_token(subject="user-1", expires_delta=timedelta(seconds=0))

    with pytest.raises(ValueError, match="Token expiration delta must be positive"):
        create_access_token(subject="user-1", expires_delta=timedelta(minutes=-5))


def test_jwt_empty_subject_rejected(ephemeral_jwt_secret):
    """Verify that empty or null subject raises ValueError."""
    with pytest.raises(ValueError, match="Subject cannot be empty"):
        create_access_token(subject="")


def test_settings_expiry_validation():
    """Verify that Settings rejects a non-positive access_token_expire_minutes."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=0,
        )

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=-15,
        )


def test_jwt_insufficient_secret_length_rejected(monkeypatch):
    """Verify that HS256 secret keys shorter than 32 bytes fail closed."""
    short_secret = "short-key-16-byt"  # 16 bytes
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr(short_secret))

    with pytest.raises(SecurityConfigError, match="at least 32 bytes"):
        create_access_token(subject="user-short-secret")

    with pytest.raises(SecurityConfigError, match="at least 32 bytes"):
        decode_access_token(token="dummy.jwt.token")
