import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


class StorageService:
    def __init__(self, root_dir: Path | str | None = None):
        self.root_dir = Path(root_dir or settings.storage_root_dir).resolve()
        self.quarantine_dir = self.root_dir / "quarantine"
        self.clean_dir = self.root_dir / "clean"
        self.rejected_dir = self.root_dir / "rejected"
        self.extractions_dir = self.root_dir / "extractions"

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.clean_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir.mkdir(parents=True, exist_ok=True)
        self.extractions_dir.mkdir(parents=True, exist_ok=True)

    def _validate_path_containment(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(self.root_dir):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid storage path traversal attempt",
                )
        except (ValueError, RuntimeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage path traversal attempt",
            )

    async def save_to_quarantine(
        self,
        upload_file: UploadFile,
        max_size_bytes: int | None = None,
    ) -> tuple[Path, str, int]:
        """Streams an uploaded file directly to private quarantine storage while calculating

        SHA-256 and enforcing byte length limits.
        """
        max_bytes = max_size_bytes or settings.max_upload_size_bytes
        opaque_filename = f"{uuid.uuid4().hex}.bin"
        quarantine_path = self.quarantine_dir / opaque_filename

        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            with open(quarantine_path, "wb") as f:  # noqa: ASYNC230
                while True:
                    chunk = await upload_file.read(64 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Uploaded file exceeds maximum allowed size ({max_bytes // (1024 * 1024)} MB)",
                        )
                    hasher.update(chunk)
                    f.write(chunk)

            if total_bytes == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty (0 bytes)",
                )

            sha256_hex = hasher.hexdigest().lower()
            return quarantine_path, sha256_hex, total_bytes

        except Exception:
            if quarantine_path.exists():
                try:
                    quarantine_path.unlink()
                except OSError:
                    pass
            raise

    def save_bytes_to_quarantine(
        self,
        data: bytes,
        max_size_bytes: int | None = None,
    ) -> tuple[Path, str, int]:
        """Synchronously writes raw bytes into quarantine (useful in unit tests & fixtures)."""
        max_bytes = max_size_bytes or settings.max_upload_size_bytes
        total_bytes = len(data)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded file exceeds maximum allowed size ({max_bytes // (1024 * 1024)} MB)",
            )
        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)",
            )

        opaque_filename = f"{uuid.uuid4().hex}.bin"
        quarantine_path = self.quarantine_dir / opaque_filename

        hasher = hashlib.sha256(data)
        sha256_hex = hasher.hexdigest().lower()

        quarantine_path.write_bytes(data)
        return quarantine_path, sha256_hex, total_bytes

    def move_to_clean(self, current_path: Path) -> tuple[Path, str]:
        """Atomically moves a scanned clean file into clean storage.

        Returns (new_path, relative_storage_key).
        """
        self._validate_path_containment(current_path)
        dest_path = self.clean_dir / current_path.name
        shutil.move(str(current_path), str(dest_path))
        relative_key = f"clean/{dest_path.name}"
        return dest_path, relative_key

    def move_to_rejected(self, current_path: Path) -> tuple[Path, str]:
        """Atomically moves an infected/rejected file into rejected storage.

        Returns (new_path, relative_storage_key).
        """
        self._validate_path_containment(current_path)
        dest_path = self.rejected_dir / current_path.name
        shutil.move(str(current_path), str(dest_path))
        relative_key = f"rejected/{dest_path.name}"
        return dest_path, relative_key

    def get_relative_key_for_quarantine(self, quarantine_path: Path) -> str:
        self._validate_path_containment(quarantine_path)
        return f"quarantine/{quarantine_path.name}"

    def get_file_path(self, storage_key: str) -> Path:
        """Resolves a storage key relative to root_dir and verifies existence."""
        target_path = (self.root_dir / storage_key).resolve()
        self._validate_path_containment(target_path)
        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored document file could not be found",
            )
        return target_path

    def verify_integrity(self, file_path: Path, expected_sha256: str) -> bool:
        """Re-computes the SHA-256 checksum of a stored file and verifies it matches."""
        self._validate_path_containment(file_path)
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                hasher.update(chunk)
        return hasher.hexdigest().lower() == expected_sha256.lower()

    def delete_file(self, file_path: Path) -> None:
        try:
            self._validate_path_containment(file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception:  # noqa: S110, BLE001
            pass

    def save_extraction_json(
        self,
        extraction_id: uuid.UUID,
        payload: dict[str, Any] | str,
    ) -> tuple[Path, str]:
        """Saves serialized extraction JSON to private storage.

        Returns (dest_path, relative_storage_key).
        """
        filename = f"{extraction_id.hex}.json"
        dest_path = self.extractions_dir / filename
        self._validate_path_containment(dest_path)

        content = (
            payload
            if isinstance(payload, str)
            else json.dumps(payload, indent=2, default=str)
        )
        dest_path.write_text(content, encoding="utf-8")
        relative_key = f"extractions/{filename}"
        return dest_path, relative_key

    def get_extraction_json(self, storage_key: str) -> dict[str, Any]:
        """Loads and parses an extraction JSON file by its relative storage key."""
        target_path = self.get_file_path(storage_key)
        self._validate_path_containment(target_path)
        try:
            content = target_path.read_text(encoding="utf-8")
            return json.loads(content)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read extraction data from storage: {exc}",
            ) from exc

    def delete_extraction_file(self, storage_key: str) -> None:
        """Safely removes an extraction JSON file given its relative storage key."""
        try:
            target_path = (self.root_dir / storage_key).resolve()
            self._validate_path_containment(target_path)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
        except Exception:  # noqa: S110, BLE001
            pass


storage_service = StorageService()
