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
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import UserStatus
from app.models.user import User


@pytest.fixture(autouse=True)
def configure_test_security(monkeypatch):
    """Ensure a safe 32-byte JWT secret and local cookie security are configured for tests."""
    test_secret = secrets.token_urlsafe(32)
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr(test_secret))
    monkeypatch.setattr(settings, "cookie_secure", False)
    return test_secret


@pytest.fixture
def client():
    """Provide a TestClient for testing FastAPI endpoints."""
    return TestClient(app)


@pytest.fixture
def test_db():
    """Provide a PostgreSQL database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def active_user(test_db):
    """Create a real active test user in PostgreSQL and clean it up strictly by ID."""
    raw_password = "SecurePassword#2026"
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        full_name="Active Test User",
        email=f"active.{user_id.hex[:8]}@test.aic-verify.internal",
        password_hash=hash_password(raw_password),
        status=UserStatus.ACTIVE,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    try:
        yield user, raw_password
    finally:
        cleanup_db = SessionLocal()
        try:
            target = cleanup_db.get(User, user_id)
            if target:
                cleanup_db.delete(target)
                cleanup_db.commit()
            assert cleanup_db.get(User, user_id) is None
        finally:
            cleanup_db.close()


@pytest.fixture
def invited_user(test_db):
    """Create a real invited test user in PostgreSQL and clean it up strictly by ID."""
    raw_password = "SecurePassword#2026"
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        full_name="Invited Test User",
        email=f"invited.{user_id.hex[:8]}@test.aic-verify.internal",
        password_hash=hash_password(raw_password),
        status=UserStatus.INVITED,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    try:
        yield user, raw_password
    finally:
        cleanup_db = SessionLocal()
        try:
            target = cleanup_db.get(User, user_id)
            if target:
                cleanup_db.delete(target)
                cleanup_db.commit()
            assert cleanup_db.get(User, user_id) is None
        finally:
            cleanup_db.close()


@pytest.fixture
def suspended_user(test_db):
    """Create a real suspended test user in PostgreSQL and clean it up strictly by ID."""
    raw_password = "SecurePassword#2026"
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        full_name="Suspended Test User",
        email=f"suspended.{user_id.hex[:8]}@test.aic-verify.internal",
        password_hash=hash_password(raw_password),
        status=UserStatus.SUSPENDED,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    try:
        yield user, raw_password
    finally:
        cleanup_db = SessionLocal()
        try:
            target = cleanup_db.get(User, user_id)
            if target:
                cleanup_db.delete(target)
                cleanup_db.commit()
            assert cleanup_db.get(User, user_id) is None
        finally:
            cleanup_db.close()


@pytest.fixture
def disabled_user(test_db):
    """Create a real disabled test user in PostgreSQL and clean it up strictly by ID."""
    raw_password = "SecurePassword#2026"
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        full_name="Disabled Test User",
        email=f"disabled.{user_id.hex[:8]}@test.aic-verify.internal",
        password_hash=hash_password(raw_password),
        status=UserStatus.DISABLED,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    try:
        yield user, raw_password
    finally:
        cleanup_db = SessionLocal()
        try:
            target = cleanup_db.get(User, user_id)
            if target:
                cleanup_db.delete(target)
                cleanup_db.commit()
            assert cleanup_db.get(User, user_id) is None
        finally:
            cleanup_db.close()


@pytest.fixture
def user_without_password(test_db):
    """Create a real test user with no password hash in PostgreSQL and clean it up strictly by ID."""
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        full_name="No Password User",
        email=f"nopassword.{user_id.hex[:8]}@test.aic-verify.internal",
        password_hash=None,
        status=UserStatus.ACTIVE,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    try:
        yield user
    finally:
        cleanup_db = SessionLocal()
        try:
            target = cleanup_db.get(User, user_id)
            if target:
                cleanup_db.delete(target)
                cleanup_db.commit()
            assert cleanup_db.get(User, user_id) is None
        finally:
            cleanup_db.close()


# ==============================================================================
# CSRF Tests (Requirement 1, 2, 3, 21)
# ==============================================================================


def test_csrf_token_endpoint_creates_matching_cookie_and_response(client):
    """Verify that GET /csrf generates a matching CSRF cookie and response payload."""
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200

    data = response.json()
    assert "csrf_token" in data
    csrf_token = data["csrf_token"]
    assert len(csrf_token) >= 32

    # Verify cookie was set and matches the response body
    cookie_value = response.cookies.get(settings.csrf_cookie_name)
    assert cookie_value == csrf_token


def test_csrf_multi_tab_preserves_existing_cookie(client):
    """Verify that calling /csrf with an existing valid CSRF cookie returns that token without replacing it."""
    initial_csrf = secrets.token_urlsafe(32)
    client.cookies.set(settings.csrf_cookie_name, initial_csrf)

    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"] == initial_csrf


def test_csrf_missing_header_rejected(client):
    """Verify that state-changing auth endpoints reject requests missing the X-CSRF-Token header."""
    csrf_token = secrets.token_urlsafe(32)
    client.cookies.set(settings.csrf_cookie_name, csrf_token)

    # Missing X-CSRF-Token header
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "any@test.aic-verify.internal", "password": "password"},
    )
    assert response.status_code == 403
    assert "CSRF validation failed: token missing" in response.json()["detail"]


def test_csrf_mismatched_value_rejected(client):
    """Verify that state-changing auth endpoints reject mismatched CSRF values."""
    cookie_token = secrets.token_urlsafe(32)
    header_token = secrets.token_urlsafe(32)
    client.cookies.set(settings.csrf_cookie_name, cookie_token)

    response = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": header_token},
        json={"email": "any@test.aic-verify.internal", "password": "password"},
    )
    assert response.status_code == 403
    assert "CSRF validation failed: token mismatch" in response.json()["detail"]


# ==============================================================================
# Login Tests (Requirements 4, 5, 6, 7, 8, 9, 10, 11, 12, 22)
# ==============================================================================


def test_login_valid_credentials_succeeds(client, active_user, test_db):
    """Verify that valid credentials return HTTP 200, safe profile, and update last_login_at."""
    user, raw_password = active_user

    # Establish CSRF
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )

    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["message"] == "Login successful"
    assert data["user"]["user_id"] == str(user.user_id)
    assert data["user"]["email"] == user.email
    assert data["user"]["status"] == "ACTIVE"
    # Ensure no token or password hash is returned in response body
    assert "access_token" not in data
    assert "password_hash" not in data["user"]

    # Verify HttpOnly access cookie is set
    access_cookie = login_resp.cookies.get(settings.access_cookie_name)
    assert access_cookie is not None

    # Verify last_login_at was updated in PostgreSQL
    test_db.refresh(user)
    assert user.last_login_at is not None


def test_login_invalid_password_fails_with_generic_response(client, active_user):
    """Verify that incorrect password returns generic HTTP 401."""
    user, _ = active_user
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": "WrongPassword123!"},
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["detail"] == "Invalid email or password."
    assert settings.access_cookie_name not in login_resp.cookies


def test_login_nonexistent_email_fails_with_identical_generic_response(client):
    """Verify that non-existent email returns identical generic HTTP 401 to prevent enumeration."""
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "nonexistent@test.aic-verify.internal",
            "password": "AnyPassword123!",
        },
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["detail"] == "Invalid email or password."


def test_login_email_case_and_whitespace_normalization(client, active_user):
    """Verify that email comparison is case-insensitive and ignores surrounding whitespace."""
    user, raw_password = active_user
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    # Submit with mixed case and leading/trailing whitespace
    messy_email = f"   {user.email.upper()}   "
    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": messy_email, "password": raw_password},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == user.email


def test_login_user_without_password_hash_cannot_log_in(client, user_without_password):
    """Verify that accounts without password hashes cannot log in and return generic 401."""
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user_without_password.email, "password": "AnyPassword123!"},
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["detail"] == "Invalid email or password."


def test_login_invited_user_rejected(client, invited_user):
    """Verify that users in INVITED status cannot log in (HTTP 403)."""
    user, raw_password = invited_user
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )
    assert login_resp.status_code == 403
    assert "INVITED" in login_resp.json()["detail"]


def test_login_suspended_user_rejected(client, suspended_user):
    """Verify that users in SUSPENDED status cannot log in (HTTP 403)."""
    user, raw_password = suspended_user
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )
    assert login_resp.status_code == 403
    assert "SUSPENDED" in login_resp.json()["detail"]


def test_login_disabled_user_rejected(client, disabled_user):
    """Verify that users in DISABLED status cannot log in (HTTP 403)."""
    user, raw_password = disabled_user
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )
    assert login_resp.status_code == 403
    assert "DISABLED" in login_resp.json()["detail"]


def test_login_cookie_attributes_and_security(client, active_user, monkeypatch):
    """Verify that the access cookie has correct HttpOnly, SameSite, and Secure flags."""
    user, raw_password = active_user

    # Test local environment: secure=False
    monkeypatch.setattr(settings, "cookie_secure", False)
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )
    assert resp.status_code == 200
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert f"{settings.access_cookie_name}=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()

    # Test production environment: secure=True
    monkeypatch.setattr(settings, "cookie_secure", True)
    resp_prod = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )
    assert resp_prod.status_code == 200
    set_cookie_header_prod = resp_prod.headers.get("set-cookie", "")
    assert "secure" in set_cookie_header_prod.lower()


def test_login_fails_closed_on_missing_jwt_secret(client, active_user, monkeypatch):
    """Verify that login returns HTTP 503 if JWT secret is missing, rather than invalid credentials."""
    user, raw_password = active_user
    csrf_resp = client.get("/api/v1/auth/csrf")
    csrf_token = csrf_resp.json()["csrf_token"]

    monkeypatch.setattr(settings, "jwt_secret_key", None)
    login_resp = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": user.email, "password": raw_password},
    )
    assert login_resp.status_code == 503
    assert "configuration error" in login_resp.json()["detail"]


# ==============================================================================
# /me Current User Tests (Requirements 13, 14, 15, 16)
# ==============================================================================


def test_me_endpoint_succeeds_with_valid_access_cookie(client, active_user):
    """Verify that GET /me returns the user profile when valid access cookie is present."""
    user, _ = active_user
    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()["user"]
    assert data["user_id"] == str(user.user_id)
    assert data["full_name"] == user.full_name
    assert data["email"] == user.email
    assert data["status"] == "ACTIVE"


def test_me_endpoint_rejects_missing_token(client):
    """Verify that GET /me returns HTTP 401 when access cookie is omitted."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "access token missing" in response.json()["detail"]


def test_me_endpoint_rejects_expired_or_tampered_token(
    client, active_user, configure_test_security
):
    """Verify that GET /me returns HTTP 401 on expired or tampered token."""
    user, _ = active_user

    # Expired token
    expired_token = jwt.encode(
        {
            "sub": str(user.user_id),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "jti": str(uuid.uuid4()),
            "token_type": "access",
        },
        configure_test_security,
        algorithm="HS256",
    )
    client.cookies.set(settings.access_cookie_name, expired_token)
    expired_resp = client.get("/api/v1/auth/me")
    assert expired_resp.status_code == 401

    # Tampered token
    valid_token = create_access_token(subject=user.user_id)
    tampered_token = valid_token[:-5] + "XXXXX"
    client.cookies.set(settings.access_cookie_name, tampered_token)
    tampered_resp = client.get("/api/v1/auth/me")
    assert tampered_resp.status_code == 401


def test_me_endpoint_rejects_deleted_or_deactivated_user(client, active_user, test_db):
    """Verify that GET /me rejects users who have been deleted or deactivated in PostgreSQL."""
    user, _ = active_user
    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Change user status to SUSPENDED in database
    user.status = UserStatus.SUSPENDED
    test_db.commit()

    suspended_resp = client.get("/api/v1/auth/me")
    assert suspended_resp.status_code == 403
    assert "SUSPENDED" in suspended_resp.json()["detail"]

    # Delete user from database entirely
    test_db.delete(user)
    test_db.commit()

    deleted_resp = client.get("/api/v1/auth/me")
    assert deleted_resp.status_code == 401
    assert "no longer exists" in deleted_resp.json()["detail"]


# ==============================================================================
# Logout Tests (Requirement 17)
# ==============================================================================


def test_logout_clears_both_cookies(client):
    """Verify that POST /logout clears both access and CSRF cookies."""
    csrf_token = secrets.token_urlsafe(32)
    client.cookies.set(settings.csrf_cookie_name, csrf_token)
    client.cookies.set(settings.access_cookie_name, "dummy-token")

    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logout successful"

    # Verify cookies were deleted (cleared in response headers)
    set_cookie_header = response.headers.get("set-cookie", "")
    assert (
        f'{settings.access_cookie_name}=""' in set_cookie_header
        or f"{settings.access_cookie_name}=;" in set_cookie_header
    )
    assert (
        f'{settings.csrf_cookie_name}=""' in set_cookie_header
        or f"{settings.csrf_cookie_name}=;" in set_cookie_header
    )


# ==============================================================================
# Compatibility and CORS Tests (Requirements 18, 19, 20)
# ==============================================================================


def test_health_and_root_endpoints_remain_functional(client):
    """Verify that root / and health /health endpoints remain fully operational."""
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "AIC-Verify API is running" in root_resp.json()["message"]

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"


def test_cors_explicitly_permits_configured_origins_with_credentials(client):
    """Verify that CORS permits configured frontend origins with credentials."""
    allowed_origin = "http://localhost:5173"

    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-CSRF-Token",
        },
    )
    assert response.headers.get("access-control-allow-origin") == allowed_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_rejects_unallowed_origins_without_wildcard(client):
    """Verify that unauthorized origins do not receive CORS permission headers."""
    untrusted_origin = "http://malicious-attacker.com"

    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": untrusted_origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") != untrusted_origin
    assert response.headers.get("access-control-allow-origin") != "*"
