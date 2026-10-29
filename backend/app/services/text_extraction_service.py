"""AIC-Verify — Hybrid Text Extraction and OCR Service.

Phase 4, Batch 2:
Extracts textual content from antivirus-clean evidence documents using:
- pypdf for fast native vector text extraction.
- pypdfium2 for page-by-page PDF rasterization to PIL images.
- RapidOCR (PP-OCRv6 ONNX CPU engine) for deep learning OCR.
- Pillow for validated image processing.

Key Architectural Guarantees:
1. Page-by-page independent routing: Each PDF page is evaluated independently
   as NATIVE_TEXT or OCR; no majority-page assumption is made.
2. Provenance integrity: Bounding boxes and confidence scores are preserved
   strictly from OCR output; native text does NOT fabricate bounding boxes
   or calibrated confidence scores.
3. Pre-render dimension calculation: PDF page dimensions and pixel budgets are
   computed before calling PDFium rendering, rejecting oversized pages before
   allocating raster image buffers.
4. Deadline & timeout enforcement: Execution deadlines are enforced across
   document pages, unblocking callers when timeouts expire.
5. Sparse native text preservation: Embedded vector text on scanned pages is not
   discarded when OCR also detects content; non-duplicate text is preserved.
6. Resource safety: Bounded page counts (<=200), bounded rendering dimensions,
   bounded memory via sequential page processing, and async thread-pool offloading.
7. Engine lifecycle: Lazy initialization and singleton reuse of the ONNX OCR models.
"""

from __future__ import annotations

import asyncio
import io
import logging
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings

logger = logging.getLogger("aic_flow.text_extraction")


class PageExtractionMethod(str, Enum):
    """Method used to extract text from a specific page."""

    NATIVE_TEXT = "NATIVE_TEXT"
    OCR = "OCR"


class BoundingBox(BaseModel):
    """Bounding box for OCR-detected text.

    Supports both rectangular (x, y, width, height) and 4-point polygon vertices
    (top-left, top-right, bottom-right, bottom-left) in pixel coordinates.
    """

    x: float = Field(..., description="Top-left horizontal coordinate (pixels)")
    y: float = Field(..., description="Top-left vertical coordinate (pixels)")
    width: float = Field(..., description="Bounding box width (pixels)")
    height: float = Field(..., description="Bounding box height (pixels)")
    vertices: list[list[float]] = Field(
        default_factory=list,
        description="4-point polygon coordinates [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]",
    )


class ExtractedTextLine(BaseModel):
    """Individual line of extracted text with provenance."""

    line_number: int = Field(..., description="1-indexed line number on page")
    text: str = Field(..., description="Extracted line text")
    confidence: float | None = Field(
        default=None,
        description="Raw line recognition score from OCR engine (None for native text)",
    )
    bounding_box: BoundingBox | None = Field(
        default=None,
        description="OCR bounding box (None for native vector text)",
    )
    start_char_offset: int | None = Field(
        default=None,
        description="Character offset from start of page text",
    )
    end_char_offset: int | None = Field(
        default=None,
        description="Character offset to end of line in page text",
    )


class PageExtractionResult(BaseModel):
    """Extraction output for an individual page."""

    page_number: int = Field(..., description="1-indexed page number")
    method: PageExtractionMethod = Field(
        ...,
        description="Extraction method applied to this page",
    )
    text: str = Field(..., description="Full text extracted for this page")
    lines: list[ExtractedTextLine] = Field(
        default_factory=list,
        description="Extracted lines with provenance",
    )
    width: float | None = Field(
        default=None,
        description="Page or image width (pixels or points)",
    )
    height: float | None = Field(
        default=None,
        description="Page or image height (pixels or points)",
    )
    dpi: int | None = Field(
        default=None,
        description="Rendering DPI used if page was processed via OCR",
    )
    char_count: int = Field(default=0, description="Character count on page")
    line_count: int = Field(default=0, description="Number of lines on page")
    average_confidence: float | None = Field(
        default=None,
        description="Average raw OCR confidence score across lines on this page",
    )
    processing_time_ms: float = Field(
        default=0.0,
        description="Extraction time for this page in milliseconds",
    )


class DocumentExtractionResult(BaseModel):
    """Standardized document-level extraction container."""

    mime_type: str = Field(..., description="Detected MIME type of document")
    page_count: int = Field(..., description="Total pages processed")
    pages: list[PageExtractionResult] = Field(
        default_factory=list,
        description="Page-by-page extraction results",
    )
    full_text: str = Field(
        ...,
        description="Concatenated document text across all pages",
    )
    total_char_count: int = Field(
        default=0,
        description="Total character count across document",
    )
    native_pages_count: int = Field(
        default=0,
        description="Count of pages extracted using native vector text",
    )
    ocr_pages_count: int = Field(
        default=0,
        description="Count of pages extracted using deep learning OCR",
    )
    extraction_engine: str = Field(
        default="RapidOCR/ONNXRuntime + pypdf",
        description="Primary extraction engine and backend",
    )
    engine_version: str = Field(
        default="rapidocr 3.10.0 / onnxruntime 1.31.1",
        description="Engine and inference runtime version",
    )
    model_names: dict[str, str] = Field(
        default_factory=lambda: {
            "detection": "PP-OCRv6_det_small",
            "classification": "ch_ppocr_mobile_v2.0_cls_mobile",
            "recognition": "PP-OCRv6_rec_small",
        },
        description="Exact deep learning model names",
    )
    total_processing_time_ms: float = Field(
        default=0.0,
        description="Total document processing latency in milliseconds",
    )
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic details, rendering info, and environmental metadata",
    )


class TextExtractionError(Exception):
    """Base exception for text extraction failures."""


class ExtractionPageLimitError(TextExtractionError):
    """Document exceeds the allowed maximum page count."""


class UnsupportedMimeTypeError(TextExtractionError):
    """MIME type is not supported for text extraction."""


class CorruptDocumentError(TextExtractionError):
    """Document content is corrupt, truncated, or unreadable."""


class ImageDimensionExceededError(TextExtractionError):
    """Image dimensions exceed configured safety limits."""


class ExtractionTimeoutError(TextExtractionError):
    """Document text extraction exceeded the configured deadline."""


class TextExtractionService:
    """Service orchestrating hybrid native PDF text extraction and RapidOCR."""

    def __init__(
        self,
        engine: Any | None = None,
        render_dpi: int | None = None,
        min_native_chars_per_page: int | None = None,
        processing_timeout: float | None = None,
    ) -> None:
        self._engine = engine
        self._engine_lock = threading.Lock()
        self.render_dpi = render_dpi or settings.ocr_render_dpi
        self.min_native_chars_per_page = (
            min_native_chars_per_page
            if min_native_chars_per_page is not None
            else settings.ocr_min_native_chars_per_page
        )
        self.processing_timeout = (
            processing_timeout
            if processing_timeout is not None
            else settings.ocr_processing_timeout_seconds
        )

    def _get_engine(self) -> Any:
        """Lazily initializes and reuses the RapidOCR engine instance."""
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    try:
                        from rapidocr import RapidOCR

                        self._engine = RapidOCR()
                    except Exception as exc:
                        raise TextExtractionError(
                            f"Failed to initialize RapidOCR engine: {exc}"
                        ) from exc
        return self._engine

    def extract_from_bytes(
        self,
        content: bytes,
        mime_type: str,
    ) -> DocumentExtractionResult:
        """Synchronously extracts text and OCR metadata from document bytes."""
        normalized_mime = mime_type.lower().strip()
        start_time = time.perf_counter()
        deadline = start_time + self.processing_timeout

        if not content:
            raise CorruptDocumentError("Document content is empty (0 bytes)")

        if normalized_mime == "application/pdf":
            result = self._extract_pdf(content, deadline)
        elif normalized_mime in ("image/png", "image/jpeg", "image/jpg"):
            result = self._extract_image(content, normalized_mime, deadline)
        else:
            raise UnsupportedMimeTypeError(
                f"Unsupported MIME type for text extraction: {mime_type}"
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        result.total_processing_time_ms = round(elapsed_ms, 2)
        return result

    def extract_from_file(
        self,
        file_path: Path | str,
        mime_type: str | None = None,
    ) -> DocumentExtractionResult:
        """Extracts text from a file on disk."""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise CorruptDocumentError(f"File not found: {path}")

        detected_mime = mime_type
        if not detected_mime:
            ext = path.suffix.lower()
            if ext == ".pdf":
                detected_mime = "application/pdf"
            elif ext == ".png":
                detected_mime = "image/png"
            elif ext in (".jpg", ".jpeg"):
                detected_mime = "image/jpeg"
            else:
                raise UnsupportedMimeTypeError(
                    f"Cannot infer supported MIME type from extension: {ext}"
                )

        content = path.read_bytes()
        return self.extract_from_bytes(content, detected_mime)

    async def extract_from_bytes_async(
        self,
        content: bytes,
        mime_type: str,
    ) -> DocumentExtractionResult:
        """Asynchronously extracts text offloaded to a thread pool with deadline enforcement.

        Note: CPU-bound native ONNX inference cannot be preemptively terminated mid-call
        by asyncio cancellation. The deadline is checked deterministically between pages
        and before inference calls, while asyncio.wait_for unblocks the asynchronous caller
        if the overall document timeout expires.
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.extract_from_bytes, content, mime_type),
                timeout=self.processing_timeout,
            )
        except TimeoutError as exc:
            raise ExtractionTimeoutError(
                f"Asynchronous text extraction timed out after {self.processing_timeout:.1f}s"
            ) from exc

    async def extract_from_file_async(
        self,
        file_path: Path | str,
        mime_type: str | None = None,
    ) -> DocumentExtractionResult:
        """Asynchronously extracts text from a file path offloaded to a thread pool."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.extract_from_file, file_path, mime_type),
                timeout=self.processing_timeout,
            )
        except TimeoutError as exc:
            raise ExtractionTimeoutError(
                f"Asynchronous text extraction timed out after {self.processing_timeout:.1f}s"
            ) from exc

    # -------------------------------------------------------------------------
    # PDF Processing (Hybrid Page-by-Page)
    # -------------------------------------------------------------------------

    def _extract_pdf(
        self,
        content: bytes,
        deadline: float,
    ) -> DocumentExtractionResult:
        """Processes a PDF file, evaluating each page independently for native

        vector text vs. OCR while enforcing deadlines.
        """
        # 1. Structural inspection with pypdf
        try:
            reader = PdfReader(io.BytesIO(content))
        except (PdfReadError, ValueError, TypeError, KeyError) as exc:
            raise CorruptDocumentError(f"Malformed PDF structure: {exc}") from exc
        except Exception as exc:
            raise CorruptDocumentError(f"Failed to read PDF document: {exc}") from exc

        if reader.is_encrypted:
            raise CorruptDocumentError(
                "PDF is password-protected or encrypted; extraction rejected"
            )

        num_pages = len(reader.pages)
        if num_pages == 0:
            raise CorruptDocumentError("PDF contains zero pages")

        if num_pages > settings.max_pdf_pages:
            raise ExtractionPageLimitError(
                f"PDF page count ({num_pages}) exceeds allowed limit "
                f"({settings.max_pdf_pages})"
            )

        # 2. Open PDFium document for page rasterization on demand
        try:
            pdfium_doc = pdfium.PdfDocument(content)
        except Exception as exc:
            raise CorruptDocumentError(
                f"pypdfium2 failed to parse PDF document: {exc}"
            ) from exc

        pages_results: list[PageExtractionResult] = []
        native_count = 0
        ocr_count = 0

        try:
            for page_idx in range(num_pages):
                page_start = time.perf_counter()
                page_num = page_idx + 1

                # Check timeout deadline before each page
                if time.perf_counter() > deadline:
                    raise ExtractionTimeoutError(
                        f"Document text extraction exceeded timeout deadline of "
                        f"{self.processing_timeout:.1f}s while processing page {page_num} of {num_pages}"
                    )

                # Extract native text from pypdf
                pypdf_page = reader.pages[page_idx]
                try:
                    native_raw = pypdf_page.extract_text() or ""
                except (PdfReadError, ValueError, TypeError, AttributeError) as exc:
                    logger.debug(
                        "pypdf text extraction skipped on page %d: %s", page_num, exc
                    )
                    native_raw = ""

                clean_native = native_raw.strip()
                page_width: float | None = None
                page_height: float | None = None

                try:
                    mediabox = pypdf_page.mediabox
                    page_width = float(mediabox.width)
                    page_height = float(mediabox.height)
                except (AttributeError, ValueError, TypeError) as exc:
                    logger.debug(
                        "Could not read mediabox dimensions for page %d: %s",
                        page_num,
                        exc,
                    )

                # Page-level decision:
                # If non-whitespace native text meets or exceeds threshold, use NATIVE_TEXT.
                if len(clean_native) >= self.min_native_chars_per_page:
                    page_res = self._process_native_page(
                        page_num=page_num,
                        text=native_raw,
                        width=page_width,
                        height=page_height,
                        elapsed_ms=(time.perf_counter() - page_start) * 1000.0,
                    )
                    native_count += 1
                else:
                    # Low or zero native text: render page image via pypdfium2 and run OCR
                    page_res = self._process_scanned_pdf_page(
                        pdfium_doc=pdfium_doc,
                        page_idx=page_idx,
                        page_num=page_num,
                        fallback_native_text=native_raw,
                        fallback_width=page_width,
                        fallback_height=page_height,
                        start_time=page_start,
                        deadline=deadline,
                    )
                    if page_res.method == PageExtractionMethod.OCR:
                        ocr_count += 1
                    else:
                        native_count += 1

                pages_results.append(page_res)

        finally:
            pdfium_doc.close()

        # Build full text by joining pages with double newline
        full_text = "\n\n".join(p.text for p in pages_results if p.text.strip())
        total_chars = sum(p.char_count for p in pages_results)

        return DocumentExtractionResult(
            mime_type="application/pdf",
            page_count=num_pages,
            pages=pages_results,
            full_text=full_text,
            total_char_count=total_chars,
            native_pages_count=native_count,
            ocr_pages_count=ocr_count,
            diagnostics={
                "pdf_version": getattr(reader, "pdf_header", "unknown"),
                "render_dpi": self.render_dpi,
                "min_native_chars_threshold": self.min_native_chars_per_page,
                "processing_timeout_seconds": self.processing_timeout,
            },
        )

    def _process_native_page(
        self,
        page_num: int,
        text: str,
        width: float | None,
        height: float | None,
        elapsed_ms: float,
    ) -> PageExtractionResult:
        """Builds a PageExtractionResult from native vector text without OCR."""
        lines: list[ExtractedTextLine] = []
        raw_lines = text.splitlines()
        offset = 0

        for line_idx, raw_line in enumerate(raw_lines, start=1):
            line_str = raw_line.strip()
            if not line_str:
                offset += len(raw_line) + 1
                continue

            start_offset = text.find(raw_line, offset)
            if start_offset == -1:
                start_offset = offset
            end_offset = start_offset + len(raw_line)
            offset = end_offset

            lines.append(
                ExtractedTextLine(
                    line_number=line_idx,
                    text=line_str,
                    confidence=None,  # Not an OCR output; confidence is not fabricated
                    bounding_box=None,  # Native text does not fabricate bounding box
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                )
            )

        return PageExtractionResult(
            page_number=page_num,
            method=PageExtractionMethod.NATIVE_TEXT,
            text=text,
            lines=lines,
            width=width,
            height=height,
            dpi=None,
            char_count=len(text),
            line_count=len(lines),
            average_confidence=None,
            processing_time_ms=round(elapsed_ms, 2),
        )

    def _process_scanned_pdf_page(
        self,
        pdfium_doc: pdfium.PdfDocument,
        page_idx: int,
        page_num: int,
        fallback_native_text: str,
        fallback_width: float | None,
        fallback_height: float | None,
        start_time: float,
        deadline: float,
    ) -> PageExtractionResult:
        """Renders an individual PDF page through pypdfium2 and runs RapidOCR.

        Calculates expected rendered pixel dimensions BEFORE rasterization, rejecting
        pages that exceed configured safety boundaries without allocating image memory.
        """
        scale = self.render_dpi / 72.0
        pdf_page = pdfium_doc[page_idx]

        try:
            # 1. Pre-render dimension calculation: inspect page size before rasterization
            width_pts, height_pts = pdf_page.get_size()
            expected_width = round(width_pts * scale)
            expected_height = round(height_pts * scale)
            expected_pixels = expected_width * expected_height

            if (
                expected_width > settings.max_image_dimension
                or expected_height > settings.max_image_dimension
            ):
                raise ImageDimensionExceededError(
                    f"Calculated rendered dimensions ({expected_width}x{expected_height}) for PDF page {page_num} "
                    f"exceed maximum allowed limit ({settings.max_image_dimension})"
                )

            if expected_pixels > settings.max_image_pixels:
                raise ImageDimensionExceededError(
                    f"Calculated rendered total pixels ({expected_pixels}) for PDF page {page_num} "
                    f"exceeds limit ({settings.max_image_pixels})"
                )

            # Check deadline before invoking heavy rendering / OCR
            if time.perf_counter() > deadline:
                raise ExtractionTimeoutError(
                    f"Document text extraction exceeded timeout deadline of "
                    f"{self.processing_timeout:.1f}s before rendering page {page_num}"
                )

            # 2. Render page to PIL image
            pil_image = pdf_page.render(scale=scale).to_pil()
            img_width, img_height = pil_image.size

            # 3. Execute OCR inference
            ocr_output = self._run_ocr_inference(pil_image)

            # 4. Parse OCR output
            lines, page_text, avg_conf = self._parse_ocr_output(ocr_output)

            # 5. Sparse native text preservation:
            # If native text exists on this page, ensure it is not discarded.
            clean_native = fallback_native_text.strip()
            if clean_native:
                if not lines:
                    # OCR detected nothing, retain native text
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    return self._process_native_page(
                        page_num=page_num,
                        text=fallback_native_text,
                        width=fallback_width or float(img_width),
                        height=fallback_height or float(img_height),
                        elapsed_ms=elapsed_ms,
                    )

                # Both OCR and native text exist: check for distinct native lines not in OCR
                lower_ocr_text = page_text.lower()
                distinct_native_lines: list[str] = []
                for raw_n_line in fallback_native_text.splitlines():
                    n_line = raw_n_line.strip()
                    if n_line and n_line.lower() not in lower_ocr_text:
                        distinct_native_lines.append(n_line)

                if distinct_native_lines:
                    merged_lines: list[ExtractedTextLine] = []
                    for n_idx, n_text in enumerate(distinct_native_lines, start=1):
                        merged_lines.append(
                            ExtractedTextLine(
                                line_number=n_idx,
                                text=n_text,
                                confidence=None,
                                bounding_box=None,
                            )
                        )
                    for ocr_idx, ocr_line in enumerate(
                        lines, start=len(merged_lines) + 1
                    ):
                        ocr_line.line_number = ocr_idx
                        merged_lines.append(ocr_line)

                    lines = merged_lines
                    page_text = "\n".join(l.text for l in lines)
                    # Recompute character offsets
                    current_off = 0
                    for l in lines:
                        l.start_char_offset = current_off
                        l.end_char_offset = current_off + len(l.text)
                        current_off = l.end_char_offset + 1

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return PageExtractionResult(
                page_number=page_num,
                method=PageExtractionMethod.OCR,
                text=page_text,
                lines=lines,
                width=float(img_width),
                height=float(img_height),
                dpi=self.render_dpi,
                char_count=len(page_text),
                line_count=len(lines),
                average_confidence=avg_conf,
                processing_time_ms=round(elapsed_ms, 2),
            )

        finally:
            pdf_page.close()

    # -------------------------------------------------------------------------
    # Image Processing (JPEG / PNG)
    # -------------------------------------------------------------------------

    def _extract_image(
        self,
        content: bytes,
        mime_type: str,
        deadline: float,
    ) -> DocumentExtractionResult:
        """Processes a single standalone image file (JPEG or PNG)."""
        start_time = time.perf_counter()

        if time.perf_counter() > deadline:
            raise ExtractionTimeoutError(
                f"Image text extraction exceeded timeout deadline of {self.processing_timeout:.1f}s"
            )

        try:
            pil_image = Image.open(io.BytesIO(content))
            pil_image.load()
        except (UnidentifiedImageError, ValueError, OSError) as exc:
            raise CorruptDocumentError(f"Malformed or unreadable image: {exc}") from exc

        # Dimension and pixel bounds
        img_width, img_height = pil_image.size
        if (
            img_width > settings.max_image_dimension
            or img_height > settings.max_image_dimension
        ):
            raise ImageDimensionExceededError(
                f"Image dimensions ({img_width}x{img_height}) exceed maximum "
                f"allowed limit ({settings.max_image_dimension})"
            )

        if img_width * img_height > settings.max_image_pixels:
            raise ImageDimensionExceededError(
                f"Image total pixels ({img_width * img_height}) exceeds maximum "
                f"allowed limit ({settings.max_image_pixels})"
            )

        # Convert to RGB if needed (e.g. RGBA or Grayscale)
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")

        if time.perf_counter() > deadline:
            raise ExtractionTimeoutError(
                f"Image text extraction exceeded timeout deadline of {self.processing_timeout:.1f}s "
                f"before OCR inference"
            )

        ocr_output = self._run_ocr_inference(pil_image)
        lines, page_text, avg_conf = self._parse_ocr_output(ocr_output)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        page_res = PageExtractionResult(
            page_number=1,
            method=PageExtractionMethod.OCR,
            text=page_text,
            lines=lines,
            width=float(img_width),
            height=float(img_height),
            dpi=None,
            char_count=len(page_text),
            line_count=len(lines),
            average_confidence=avg_conf,
            processing_time_ms=round(elapsed_ms, 2),
        )

        return DocumentExtractionResult(
            mime_type=mime_type,
            page_count=1,
            pages=[page_res],
            full_text=page_text,
            total_char_count=len(page_text),
            native_pages_count=0,
            ocr_pages_count=1,
            diagnostics={
                "original_image_mode": pil_image.mode,
                "image_width": img_width,
                "image_height": img_height,
                "processing_timeout_seconds": self.processing_timeout,
            },
        )

    # -------------------------------------------------------------------------
    # OCR Execution & Parsing Helpers
    # -------------------------------------------------------------------------

    def _run_ocr_inference(self, img: Image.Image) -> Any:
        """Executes RapidOCR inference inside thread lock."""
        engine = self._get_engine()
        with self._engine_lock:
            try:
                return engine(img)
            except Exception as exc:
                raise TextExtractionError(
                    f"OCR inference execution failed: {exc}"
                ) from exc

    def _parse_ocr_output(
        self,
        ocr_output: Any,
    ) -> tuple[list[ExtractedTextLine], str, float | None]:
        """Parses RapidOCROutput structure into ExtractedTextLine items.

        Preserves:
        - Exact bounding box polygon vertices and rectangular bounds.
        - Raw OCR line confidence scores without pseudo-calibration.
        """
        lines: list[ExtractedTextLine] = []

        if not ocr_output or not hasattr(ocr_output, "txts") or not ocr_output.txts:
            return lines, "", None

        boxes = getattr(ocr_output, "boxes", None)
        txts = getattr(ocr_output, "txts", [])
        scores = getattr(ocr_output, "scores", [])

        full_lines_text: list[str] = []
        total_conf = 0.0
        conf_count = 0
        current_offset = 0

        for idx, text_item in enumerate(txts):
            line_str = str(text_item).strip() if text_item is not None else ""
            if not line_str:
                continue

            full_lines_text.append(line_str)
            raw_score: float | None = None
            if idx < len(scores) and scores[idx] is not None:
                try:
                    raw_score = round(float(scores[idx]), 4)
                    total_conf += raw_score
                    conf_count += 1
                except (ValueError, TypeError):
                    raw_score = None

            bbox: BoundingBox | None = None
            if boxes is not None and idx < len(boxes):
                box_poly = boxes[idx]
                try:
                    # box_poly is shape (4, 2): [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    pts = [[float(pt[0]), float(pt[1])] for pt in box_poly]
                    min_x = min(p[0] for p in pts)
                    max_x = max(p[0] for p in pts)
                    min_y = min(p[1] for p in pts)
                    max_y = max(p[1] for p in pts)

                    bbox = BoundingBox(
                        x=round(min_x, 2),
                        y=round(min_y, 2),
                        width=round(max_x - min_x, 2),
                        height=round(max_y - min_y, 2),
                        vertices=[[round(p[0], 2), round(p[1], 2)] for p in pts],
                    )
                except (IndexError, TypeError, ValueError) as exc:
                    logger.debug(
                        "Failed to parse bounding box at index %d: %s", idx, exc
                    )
                    bbox = None

            start_offset = current_offset
            end_offset = start_offset + len(line_str)
            current_offset = end_offset + 1  # Accounting for newline

            lines.append(
                ExtractedTextLine(
                    line_number=idx + 1,
                    text=line_str,
                    confidence=raw_score,
                    bounding_box=bbox,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                )
            )

        page_text = "\n".join(full_lines_text)
        avg_confidence = round(total_conf / conf_count, 4) if conf_count > 0 else None

        return lines, page_text, avg_confidence


# Singleton service instance for standard application reuse
text_extraction_service = TextExtractionService()
