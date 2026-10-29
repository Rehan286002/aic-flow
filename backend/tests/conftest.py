import sys
from collections.abc import Generator
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, engine, get_db
from app.main import app
from app.services.storage_service import storage_service


@pytest.fixture(autouse=True)
def isolated_db_and_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[None]:
    """Guarantees complete database transaction and filesystem isolation for every test.

    1. Establishes a dedicated database connection and starts an outer transaction.
    2. Reconfigures SessionLocal in-place with join_transaction_mode="create_savepoint",
       intercepting all direct SessionLocal() calls and get_db() calls across the app
       and test suite.
    3. Any db.commit() issued by endpoints or services only releases the inner savepoint.
    4. Redirects storage_service and settings.storage_root_dir to a clean tmp_path directory.
    5. On teardown, rolls back the outer transaction and restores all engine bindings,
       leaving the persistent demonstration database and storage 100% untouched.
    """
    # --- 1. Filesystem Storage Isolation ---
    orig_storage_root = storage_service.root_dir
    orig_quarantine = storage_service.quarantine_dir
    orig_clean = storage_service.clean_dir
    orig_rejected = storage_service.rejected_dir
    orig_extractions = storage_service.extractions_dir
    orig_settings_root = settings.storage_root_dir

    temp_storage_dir = tmp_path / "test_storage"
    storage_service.root_dir = temp_storage_dir
    storage_service.quarantine_dir = temp_storage_dir / "quarantine"
    storage_service.clean_dir = temp_storage_dir / "clean"
    storage_service.rejected_dir = temp_storage_dir / "rejected"
    storage_service.extractions_dir = temp_storage_dir / "extractions"
    storage_service._ensure_directories()
    monkeypatch.setattr(settings, "storage_root_dir", str(temp_storage_dir))

    # --- 2. Database Connection & Savepoint Isolation ---
    connection = engine.connect()
    transaction = connection.begin()

    # Reconfigure the global SessionLocal singleton in-place
    SessionLocal.configure(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    # Override FastAPI dependency get_db so all route handlers use the savepoint session
    def override_get_db() -> Generator[Session]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield
    finally:
        # --- 3. Teardown & Rollback ---
        app.dependency_overrides.clear()

        # Restore SessionLocal singleton back to global engine
        SessionLocal.configure(
            bind=engine,
            join_transaction_mode=None,
        )

        # Restore StorageService and settings
        storage_service.root_dir = orig_storage_root
        storage_service.quarantine_dir = orig_quarantine
        storage_service.clean_dir = orig_clean
        storage_service.rejected_dir = orig_rejected
        storage_service.extractions_dir = orig_extractions
        monkeypatch.setattr(settings, "storage_root_dir", orig_settings_root)

        # Roll back all database operations executed during the test
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def db() -> Generator[Session]:
    """Provides an isolated database session for a test function."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    """Provides a TestClient wired to the isolated application instance."""
    return TestClient(app)
