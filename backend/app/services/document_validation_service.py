import logging
import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from fastapi import HTTPException, status
from PIL import Image, ImageFile
from PIL.Image import DecompressionBombError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Enforce strict Pillow security defaults globally
ImageFile.LOAD_TRUNCATED_IMAGES = False

ALLOWED_EXTENSIONS: Final[set[str]] = {".pdf", ".jpg", ".jpeg", ".png"}

MIME_TYPE_MAPPING: Final[dict[str, str]] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# Dangerous magic byte signatures to explicitly reject
DANGEROUS_SIGNATURES: Final[list[tuple[bytes, str]]] = [
    (b"MZ", "Windows executable (PE/EXE/DLL)"),
    (b"\x7fELF", "Linux ELF executable"),
    (b"PK\x03\x04", "ZIP or office archive"),
    (b"Rar!\x1a\x07", "RAR archive"),
    (b"\x1f\x8b", "GZIP compressed archive"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"),
    (b"#!", "Shell or script header"),
    (b"<?php", "PHP script"),
    (b"<script", "Client script"),
    (b"<!DOCTYPE html", "HTML document"),
    (b"<html", "HTML document"),
]


@dataclass(frozen=True)
class DocumentValidationResult:
    original_filename: str
    file_extension: str
    mime_type: str


class DocumentValidationService:
    def __init__(
        self,
        max_pdf_pages: int | None = None,
        max_image_dim: int | None = None,
        max_image_pixels: int | None = None,
    ) -> None:
        self.max_pdf_pages = max_pdf_pages or settings.max_pdf_pages
        self.max_image_dim = max_image_dim or settings.max_image_dimension
        self.max_image_pixels = max_image_pixels or settings.max_image_pixels
        Image.MAX_IMAGE_PIXELS = self.max_image_pixels

    def sanitize_filename(self, filename: str) -> str:
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty",
            )
        # Reject null bytes immediately (both raw \x00 and URL-encoded %00)
        unquoted = urllib.parse.unquote(filename)
        if "\x00" in filename or "\x00" in unquoted or "%00" in filename.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename contains invalid characters (null byte detected)",
            )
        # Normalize Windows path separators to forward slashes before basename extraction
        cleaned = filename.strip().replace("\\", "/")
        cleaned = os.path.basename(cleaned)
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is invalid",
            )
        if len(cleaned) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename exceeds 255 characters",
            )
        return cleaned

    def _validate_pdf_structure(self, file_path: Path) -> None:
        try:
            with open(file_path, "rb") as f:
                reader = PdfReader(f, strict=True)
                if reader.is_encrypted:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Encrypted or password-protected PDF files are not supported",
                    )
                num_pages = len(reader.pages)
                if num_pages == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="PDF document contains zero pages",
                    )
                if num_pages > self.max_pdf_pages:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"PDF page count ({num_pages}) exceeds maximum allowable limit "
                            f"({self.max_pdf_pages} pages)"
                        ),
                    )
        except HTTPException:
            raise
        except (PdfReadError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "PDF structural validation failed for %s: %s",
                file_path.name,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed or unreadable PDF document structure",
            ) from None

    def _validate_png_structure(self, file_path: Path) -> None:
        file_size = file_path.stat().st_size
        with open(file_path, "rb") as f:
            sig = f.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File header does not match valid PNG specification",
                )
            pos = 8
            found_iend = False
            while pos + 8 <= file_size:
                f.seek(pos)
                length_bytes = f.read(4)
                chunk_type = f.read(4)
                chunk_len = int.from_bytes(length_bytes, byteorder="big")
                # 4 bytes length + 4 bytes type + data length + 4 bytes CRC
                chunk_end = pos + 8 + chunk_len + 4
                if chunk_end > file_size:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Malformed PNG structure: chunk length exceeds file bounds",
                    )
                if chunk_type == b"IEND":
                    found_iend = True
                    if chunk_end != file_size:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="PNG file rejected: contains unexpected trailing data after IEND chunk",
                        )
                    break
                pos = chunk_end
            if not found_iend:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Malformed PNG structure: missing IEND termination chunk",
                )

    def _validate_jpeg_structure(self, file_path: Path) -> None:
        file_size = file_path.stat().st_size
        with open(file_path, "rb") as f:
            header = f.read(3)
            if not header.startswith(b"\xff\xd8"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File header does not match valid JPEG specification",
                )
            # Read last 128 bytes to check EOI marker \xff\xd9
            read_len = min(file_size, 128)
            f.seek(file_size - read_len)
            tail = f.read(read_len)
            # Find the position of \xff\xd9
            eoi_idx = tail.rfind(b"\xff\xd9")
            if eoi_idx == -1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JPEG file appears corrupt or truncated (missing EOI marker)",
                )
            # Check trailing bytes after EOI
            trailing = tail[eoi_idx + 2 :]
            if trailing.strip(b"\x00\r\n\t "):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JPEG file rejected: contains unexpected trailing data after EOI marker",
                )

    def _validate_image_structure(
        self,
        file_path: Path,
        expected_format: str,
    ) -> None:
        # 1. Chunk and trailing payload validation
        if expected_format == "PNG":
            self._validate_png_structure(file_path)
        elif expected_format == "JPEG":
            self._validate_jpeg_structure(file_path)

        # 2. Pillow verify and pixel decoding
        try:
            with Image.open(file_path) as img:
                if img.format != expected_format:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Image format '{img.format}' does not match expected format '{expected_format}'",
                    )
                img.verify()

            # Reopen after verify to load raster and enforce dimension/decompression limits
            with Image.open(file_path) as img:
                width, height = img.size
                if width > self.max_image_dim or height > self.max_image_dim:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Image dimensions ({width}x{height}) exceed maximum allowable limit "
                            f"({self.max_image_dim}x{self.max_image_dim})"
                        ),
                    )
                if width * height > self.max_image_pixels:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Image total pixels ({width * height}) exceed maximum allowable limit "
                            f"({self.max_image_pixels})"
                        ),
                    )
                img.load()
        except HTTPException:
            raise
        except DecompressionBombError:
            logger.warning(
                "Image rejected as potential decompression bomb: %s",
                file_path.name,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image rejected: potential decompression bomb detected",
            ) from None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Image structural validation failed for %s: %s",
                file_path.name,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed or corrupt image file structure",
            ) from None

    def validate_file_format(
        self,
        filename: str,
        file_path: Path,
        declared_mime_type: str | None = None,
    ) -> DocumentValidationResult:
        """Validates file extension, magic numbers, and structure against strict compliance rules."""
        sanitized_name = self.sanitize_filename(filename)
        ext = Path(sanitized_name).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported file format '{ext}'. Allowed evidence document formats are: {allowed_str}"
                ),
            )

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content is empty (0 bytes)",
            )

        # Inspect header bytes
        with open(file_path, "rb") as f:
            header = f.read(512)

        # 1. Reject dangerous signatures
        for sig, description in DANGEROUS_SIGNATURES:
            if header.startswith(sig) or (
                sig in (b"<!DOCTYPE html", b"<html", b"<script")
                and sig.lower() in header.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Uploaded file rejected: detected forbidden file type ({description})",
                )

        # 2. Magic byte and structural verification by extension
        if ext == ".pdf":
            if not header.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File header does not match valid PDF specification (%PDF- missing)",
                )
            # Check for %EOF in trailer (read last 2048 bytes)
            with open(file_path, "rb") as f:
                if file_size > 2048:
                    f.seek(file_size - 2048)
                else:
                    f.seek(0)
                trailer = f.read(2048)
                if b"%EOF" not in trailer:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="PDF file appears truncated or corrupt (%EOF marker missing)",
                    )
            # Deep structural validation using pypdf
            self._validate_pdf_structure(file_path)
            canonical_mime = "application/pdf"

        elif ext in (".jpg", ".jpeg"):
            if not header.startswith(b"\xff\xd8\xff"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File header does not match valid JPEG specification",
                )
            self._validate_image_structure(file_path, expected_format="JPEG")
            canonical_mime = "image/jpeg"

        elif ext == ".png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File header does not match valid PNG specification",
                )
            self._validate_image_structure(file_path, expected_format="PNG")
            canonical_mime = "image/png"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{ext}'",
            )

        return DocumentValidationResult(
            original_filename=sanitized_name,
            file_extension=ext,
            mime_type=canonical_mime,
        )


document_validation_service = DocumentValidationService()
