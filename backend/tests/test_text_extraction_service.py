"""AIC-Verify — Text Extraction & OCR Service Test Suite.

Phase 4, Batch 2:
Comprehensive verification of hybrid native text extraction, pypdfium2 rendering,
RapidOCR PP-OCRv6 inference, and resource limits across all 13 required test areas:
1. Native-text PDF: confirms native extraction without unnecessary OCR.
2. Scanned PDF: confirms PDFium rendering and real OCR.
3. Mixed PDF: independent page-by-page decision (native on page 1, OCR on page 2).
4. JPEG OCR.
5. PNG OCR.
6. Multi-page PDF page numbering and ordering.
7. Blank pages and pages containing very little text.
8. Rotated and lower-resolution synthetic text.
9. Malformed or unreadable input (corrupt PDF/image, unsupported MIME, 0-byte file).
10. PDF page-limit enforcement (exceeding max_pdf_pages raises ExtractionPageLimitError).
11. Bounding-box and confidence metadata provenance.
12. OCR initialization and inference error handling (with mocked engine).
13. Resource limits and safe sequential processing (dimension/pixel limits & async offload).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image, ImageDraw, ImageFont

# Ensure backend root is in sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.text_extraction_service import (
    CorruptDocumentError,
    ExtractionPageLimitError,
    ExtractionTimeoutError,
    ImageDimensionExceededError,
    PageExtractionMethod,
    TextExtractionError,
    TextExtractionService,
    UnsupportedMimeTypeError,
    text_extraction_service,
)

# -----------------------------------------------------------------------------
# Synthetic Document Helpers
# -----------------------------------------------------------------------------


def _get_font(size: int = 28) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads Arial or falls back to default."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def make_native_pdf(text_str: str, pages: int = 1) -> bytes:
    """Generates a searchable PDF with genuine native vector text via pypdf."""
    writer = PdfWriter()
    for i in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        font_dict = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        resources = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {
                        NameObject("/F1"): font_dict,
                    }
                )
            }
        )
        page[NameObject("/Resources")] = resources

        page_text = f"{text_str} - Page {i + 1}" if pages > 1 else text_str
        stream_content = f"BT\n/F1 14 Tf\n72 700 Td\n({page_text}) Tj\nET\n".encode(
            "latin-1"
        )
        stream = DecodedStreamObject()
        stream.set_data(stream_content)
        page[NameObject("/Contents")] = stream

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_scanned_pdf(
    text_str: str, font_size: int = 28, rotate_degrees: int = 0
) -> bytes:
    """Generates a scanned PDF containing a raster image of rendered text."""
    img = Image.new("RGB", (900, 250), color="white")
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    draw.text((40, 80), text_str, font=font, fill="black")

    if rotate_degrees:
        img = img.rotate(rotate_degrees, expand=True)

    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()


def make_mixed_pdf(native_text: str, scanned_text: str) -> bytes:
    """Generates a 2-page mixed PDF: Page 1 native vector text, Page 2 scanned raster image."""
    writer = PdfWriter()

    # Page 1: Native
    page1 = writer.add_blank_page(width=612, height=792)
    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): font_dict,
                }
            )
        }
    )
    page1[NameObject("/Resources")] = resources
    stream_content = f"BT\n/F1 14 Tf\n72 700 Td\n({native_text}) Tj\nET\n".encode(
        "latin-1"
    )
    stream = DecodedStreamObject()
    stream.set_data(stream_content)
    page1[NameObject("/Contents")] = stream

    # Page 2: Scanned image page
    scanned_bytes = make_scanned_pdf(scanned_text)
    reader_scanned = PdfReader(io.BytesIO(scanned_bytes))
    writer.add_page(reader_scanned.pages[0])

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_synthetic_image(
    text_str: str,
    fmt: str = "PNG",
    font_size: int = 32,
    rotate_degrees: int = 0,
) -> bytes:
    """Generates a synthetic PNG or JPEG image with rendered text."""
    img = Image.new("RGB", (850, 220), color="white")
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    draw.text((40, 80), text_str, font=font, fill="black")

    if rotate_degrees:
        img = img.rotate(rotate_degrees, expand=True)

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. Native-Text PDF Extraction Test
# -----------------------------------------------------------------------------


def test_native_text_pdf_extraction_no_ocr() -> None:
    """Confirms native vector text is extracted with 100% fidelity without invoking OCR."""
    ground_truth = "AICTE Approval Process Handbook AY 2026-27 Annexure 2.1"
    pdf_bytes = make_native_pdf(ground_truth, pages=1)

    result = text_extraction_service.extract_from_bytes(pdf_bytes, "application/pdf")

    assert result.page_count == 1
    assert result.native_pages_count == 1
    assert result.ocr_pages_count == 0
    assert result.pages[0].method == PageExtractionMethod.NATIVE_TEXT
    assert ground_truth in result.full_text
    assert result.pages[0].char_count == len(ground_truth)

    # Native text does NOT fabricate OCR confidence or bounding boxes
    line = result.pages[0].lines[0]
    assert line.text == ground_truth
    assert line.confidence is None
    assert line.bounding_box is None
    assert result.pages[0].average_confidence is None


# -----------------------------------------------------------------------------
# 2. Scanned PDF Extraction Test (PDFium + RapidOCR)
# -----------------------------------------------------------------------------


def test_scanned_pdf_rendering_and_ocr() -> None:
    """Confirms scanned PDF is rendered via pypdfium2 and extracted via RapidOCR."""
    ground_truth = "AFFIDAVIT 2 BY INSTITUTION AY 2026-27"
    pdf_bytes = make_scanned_pdf(ground_truth, font_size=32)

    result = text_extraction_service.extract_from_bytes(pdf_bytes, "application/pdf")

    assert result.page_count == 1
    assert result.native_pages_count == 0
    assert result.ocr_pages_count == 1
    assert result.pages[0].method == PageExtractionMethod.OCR
    assert result.pages[0].dpi == text_extraction_service.render_dpi

    # Verify line items and OCR metadata
    assert len(result.pages[0].lines) >= 1
    line = result.pages[0].lines[0]
    assert line.confidence is not None
    assert 0.0 <= line.confidence <= 1.0
    assert line.bounding_box is not None
    assert line.bounding_box.width > 0
    assert line.bounding_box.height > 0
    assert len(line.bounding_box.vertices) == 4

    # Recognition accuracy check
    assert "AFFIDAVIT" in result.full_text
    assert "2026-27" in result.full_text


# -----------------------------------------------------------------------------
# 3. Mixed PDF Extraction Test (Page-by-Page Decision)
# -----------------------------------------------------------------------------


def test_mixed_pdf_independent_page_routing() -> None:
    """Confirms that page-level routing is independent: Page 1 uses native extraction

    and Page 2 uses OCR in the very same document.
    """
    native_text = "Page 1: Native AICTE Application Requirement EOA-SD-01"
    scanned_text = "Page 2: Scanned Occupancy Certificate Form D 2026"
    pdf_bytes = make_mixed_pdf(native_text, scanned_text)

    result = text_extraction_service.extract_from_bytes(pdf_bytes, "application/pdf")

    assert result.page_count == 2
    assert result.native_pages_count == 1
    assert result.ocr_pages_count == 1

    # Page 1 must be NATIVE_TEXT
    assert result.pages[0].page_number == 1
    assert result.pages[0].method == PageExtractionMethod.NATIVE_TEXT
    assert native_text in result.pages[0].text
    assert result.pages[0].lines[0].confidence is None
    assert result.pages[0].lines[0].bounding_box is None

    # Page 2 must be OCR
    assert result.pages[1].page_number == 2
    assert result.pages[1].method == PageExtractionMethod.OCR
    assert result.pages[1].lines[0].confidence is not None
    assert result.pages[1].lines[0].bounding_box is not None
    assert "Occupancy" in result.pages[1].text or "Certificate" in result.pages[1].text


# -----------------------------------------------------------------------------
# 4 & 5. Standalone Image Tests (JPEG and PNG)
# -----------------------------------------------------------------------------


def test_jpeg_image_ocr() -> None:
    """Confirms standalone JPEG image is processed via OCR."""
    ground_truth = "FIRE SAFETY CERTIFICATE VALID NOC 2026"
    img_bytes = make_synthetic_image(ground_truth, fmt="JPEG", font_size=32)

    result = text_extraction_service.extract_from_bytes(img_bytes, "image/jpeg")

    assert result.mime_type == "image/jpeg"
    assert result.page_count == 1
    assert result.ocr_pages_count == 1
    assert result.pages[0].method == PageExtractionMethod.OCR
    assert result.pages[0].lines[0].confidence is not None
    assert "FIRE" in result.full_text
    assert "CERTIFICATE" in result.full_text


def test_png_image_ocr() -> None:
    """Confirms standalone PNG image is processed via OCR."""
    ground_truth = "STRUCTURAL STABILITY CERTIFICATE 5 YEARS"
    img_bytes = make_synthetic_image(ground_truth, fmt="PNG", font_size=32)

    result = text_extraction_service.extract_from_bytes(img_bytes, "image/png")

    assert result.mime_type == "image/png"
    assert result.page_count == 1
    assert result.ocr_pages_count == 1
    assert result.pages[0].method == PageExtractionMethod.OCR
    assert "STRUCTURAL" in result.full_text
    assert "STABILITY" in result.full_text


# -----------------------------------------------------------------------------
# 6. Multi-Page PDF Page Numbering and Ordering
# -----------------------------------------------------------------------------


def test_multipage_pdf_ordering() -> None:
    """Confirms multi-page PDF pages are ordered sequentially 1..N with accurate offsets."""
    pdf_bytes = make_native_pdf("AICTE Document Header", pages=3)

    result = text_extraction_service.extract_from_bytes(pdf_bytes, "application/pdf")

    assert result.page_count == 3
    assert [p.page_number for p in result.pages] == [1, 2, 3]
    for idx, page_res in enumerate(result.pages, start=1):
        assert f"Page {idx}" in page_res.text
        assert page_res.lines[0].line_number == 1
        assert page_res.lines[0].start_char_offset == 0


# -----------------------------------------------------------------------------
# 7. Blank and Sparse Pages
# -----------------------------------------------------------------------------


def test_blank_page_handling() -> None:
    """Confirms a truly blank page is safely handled with zero lines and empty text."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    blank_bytes = buf.getvalue()

    result = text_extraction_service.extract_from_bytes(blank_bytes, "application/pdf")

    assert result.page_count == 1
    assert result.pages[0].char_count == 0
    assert result.pages[0].lines == []
    assert result.full_text == ""


def test_sparse_text_below_threshold_retained_if_ocr_empty() -> None:
    """Confirms that if a page has 5 characters (below default 30 threshold)

    and OCR finds no additional text, the native characters are preserved.
    """
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_dict})}
    )
    # 5 characters only: "(1/10)"
    page[NameObject("/Contents")] = DecodedStreamObject()
    page[NameObject("/Contents")].set_data(b"BT /F1 10 Tf 500 50 Td (1/10) Tj ET")

    buf = io.BytesIO()
    writer.write(buf)

    result = text_extraction_service.extract_from_bytes(
        buf.getvalue(), "application/pdf"
    )
    assert result.page_count == 1
    assert "1/10" in result.full_text


# -----------------------------------------------------------------------------
# 8. Rotated Synthetic Text Recognition
# -----------------------------------------------------------------------------


def test_rotated_text_recognition() -> None:
    """Confirms RapidOCR orientation/direction classifier handles rotated text."""
    ground_truth = "ROTATED AICTE OFFICIAL RECORD 2026"
    img_bytes = make_synthetic_image(
        ground_truth, fmt="PNG", font_size=32, rotate_degrees=90
    )

    result = text_extraction_service.extract_from_bytes(img_bytes, "image/png")

    assert result.page_count == 1
    assert result.ocr_pages_count == 1
    # Even rotated, direction classifier identifies characters
    assert (
        "AICTE" in result.full_text
        or "RECORD" in result.full_text
        or "2026" in result.full_text
    )


# -----------------------------------------------------------------------------
# 9. Malformed or Unreadable Input
# -----------------------------------------------------------------------------


def test_corrupt_pdf_bytes_rejected() -> None:
    """Confirms corrupt or truncated PDF raises CorruptDocumentError."""
    with pytest.raises(CorruptDocumentError, match="Failed to read PDF|Malformed PDF"):
        text_extraction_service.extract_from_bytes(
            b"%PDF-1.4 corrupt garbage here...", "application/pdf"
        )


def test_corrupt_image_bytes_rejected() -> None:
    """Confirms corrupt or truncated image raises CorruptDocumentError."""
    with pytest.raises(CorruptDocumentError, match="Malformed or unreadable image"):
        text_extraction_service.extract_from_bytes(
            b"\x89PNG\r\n\x1a\ncorrupt bytes", "image/png"
        )


def test_empty_content_rejected() -> None:
    """Confirms empty 0-byte document raises CorruptDocumentError."""
    with pytest.raises(CorruptDocumentError, match="empty \\(0 bytes\\)"):
        text_extraction_service.extract_from_bytes(b"", "application/pdf")


def test_unsupported_mime_type_rejected() -> None:
    """Confirms unsupported MIME type raises UnsupportedMimeTypeError."""
    with pytest.raises(UnsupportedMimeTypeError, match="Unsupported MIME type"):
        text_extraction_service.extract_from_bytes(b"some text", "text/plain")


# -----------------------------------------------------------------------------
# 10. PDF Page Limit Enforcement
# -----------------------------------------------------------------------------


def test_pdf_page_limit_enforcement() -> None:
    """Confirms that a PDF with > 200 pages raises ExtractionPageLimitError."""
    writer = PdfWriter()
    for _ in range(201):
        writer.add_blank_page(width=50, height=50)
    buf = io.BytesIO()
    writer.write(buf)
    excessive_pdf = buf.getvalue()

    with pytest.raises(ExtractionPageLimitError, match="exceeds allowed limit"):
        text_extraction_service.extract_from_bytes(excessive_pdf, "application/pdf")


# -----------------------------------------------------------------------------
# 11. Bounding-Box and Confidence Provenance
# -----------------------------------------------------------------------------


def test_bounding_box_and_confidence_provenance() -> None:
    """Validates structural integrity of BoundingBox and raw OCR confidence metadata."""
    ground_truth = "AICTE PORTAL PAYMENT RECEIPT UTR 998877"
    img_bytes = make_synthetic_image(ground_truth, fmt="PNG", font_size=32)

    result = text_extraction_service.extract_from_bytes(img_bytes, "image/png")

    page = result.pages[0]
    assert page.average_confidence is not None
    assert 0.0 <= page.average_confidence <= 1.0

    for line in page.lines:
        assert line.confidence is not None
        assert 0.0 <= line.confidence <= 1.0
        assert line.bounding_box is not None
        assert line.bounding_box.width > 0
        assert line.bounding_box.height > 0
        assert len(line.bounding_box.vertices) == 4
        # Verify bounding box geometry coherence: width == max_x - min_x
        xs = [pt[0] for pt in line.bounding_box.vertices]
        ys = [pt[1] for pt in line.bounding_box.vertices]
        assert round(max(xs) - min(xs), 2) == round(line.bounding_box.width, 2)
        assert round(max(ys) - min(ys), 2) == round(line.bounding_box.height, 2)


# -----------------------------------------------------------------------------
# 12. OCR Initialization and Inference Error Handling (Mocked)
# -----------------------------------------------------------------------------


def test_ocr_inference_failure_handled_cleanly() -> None:
    """Confirms that an unexpected OCR engine runtime exception is caught

    and re-raised as TextExtractionError with clear diagnostic information.
    """
    mock_engine = MagicMock(
        side_effect=RuntimeError("Simulated ONNX Runtime segmentation fault")
    )
    service = TextExtractionService(engine=mock_engine)

    img_bytes = make_synthetic_image("Any Text", fmt="PNG")

    with pytest.raises(
        TextExtractionError, match="OCR inference execution failed: Simulated ONNX"
    ):
        service.extract_from_bytes(img_bytes, "image/png")


# -----------------------------------------------------------------------------
# 13. Resource Limits & Safe Async Processing
# -----------------------------------------------------------------------------


def test_image_dimension_limits_enforced() -> None:
    """Confirms an image exceeding maximum allowed dimensions raises ImageDimensionExceededError."""
    # Create image with header declaring 12000 width (> settings.max_image_dimension 10000)
    large_img = Image.new("RGB", (10001, 10), color="white")
    buf = io.BytesIO()
    large_img.save(buf, format="PNG")

    with pytest.raises(
        ImageDimensionExceededError, match="exceed maximum allowed limit"
    ):
        text_extraction_service.extract_from_bytes(buf.getvalue(), "image/png")


@pytest.mark.asyncio
async def test_async_extraction_offloaded_to_thread() -> None:
    """Confirms async extraction method runs offloaded in thread pool without blocking event loop."""
    ground_truth = "ASYNC EXTRACTION TEST FOR AICTE PIPELINE"
    pdf_bytes = make_native_pdf(ground_truth, pages=1)

    result = await text_extraction_service.extract_from_bytes_async(
        pdf_bytes, "application/pdf"
    )

    assert result.page_count == 1
    assert result.native_pages_count == 1
    assert ground_truth in result.full_text
    assert result.total_processing_time_ms > 0


# -----------------------------------------------------------------------------
# Batch 2 Final Acceptance Regression Tests
# -----------------------------------------------------------------------------


def test_prerender_dimension_and_pixel_check_rejects_oversized_pdf_page() -> None:
    """Regression Test 1: Verifies that PDF page dimensions and pixel counts are calculated

    BEFORE rasterization is invoked, rejecting oversized pages without allocating raster image buffers.
    """
    # 4000pt x 4000pt page rendered at 200 DPI yields 11111 x 11111 pixels (> settings.max_image_dimension 10000)
    writer = PdfWriter()
    writer.add_blank_page(width=4000, height=4000)
    buf = io.BytesIO()
    writer.write(buf)
    oversized_pdf = buf.getvalue()

    with pytest.raises(
        ImageDimensionExceededError,
        match="Calculated rendered dimensions \\(11111x11111\\) for PDF page 1 exceed maximum allowed limit",
    ):
        text_extraction_service.extract_from_bytes(oversized_pdf, "application/pdf")


def test_processing_timeout_enforcement_sync_and_async() -> None:
    """Regression Test 2: Verifies that ocr_processing_timeout_seconds is actively enforced

    and raises ExtractionTimeoutError when exceeded.
    """
    # 1. Multi-page document with an ultra-short deadline
    pdf_bytes = make_native_pdf("AICTE Verification Content", pages=5)
    timeout_service = TextExtractionService(processing_timeout=0.00001)

    with pytest.raises(
        ExtractionTimeoutError,
        match="exceeded timeout deadline",
    ):
        timeout_service.extract_from_bytes(pdf_bytes, "application/pdf")

    # 2. Async timeout enforcement

    # Run async timeout test
    async def _run_async_timeout() -> None:
        with pytest.raises(
            ExtractionTimeoutError,
            match="timed out after|exceeded timeout deadline",
        ):
            await timeout_service.extract_from_bytes_async(pdf_bytes, "application/pdf")

    import asyncio

    asyncio.run(_run_async_timeout())


def test_sparse_native_text_preserved_alongside_ocr() -> None:
    """Regression Test 3: Verifies that sparse embedded native text (below threshold)

    is not discarded when OCR also detects content on the same page.
    """
    # 1. Generate raster image with certificate body text
    img = Image.new("RGB", (850, 200), color="white")
    draw = ImageDraw.Draw(img)
    font = _get_font(28)
    draw.text(
        (30, 70), "SCANNED STRUCTURAL STABILITY CERTIFICATE", font=font, fill="black"
    )
    buf_img = io.BytesIO()
    img.save(buf_img, format="PDF", resolution=150.0)

    reader_img = PdfReader(buf_img)
    scanned_page = reader_img.pages[0]

    # 2. Generate native page with sparse header text (19 chars < 30 chars threshold)
    writer_native = PdfWriter()
    native_page = writer_native.add_blank_page(
        width=scanned_page.mediabox.width,
        height=scanned_page.mediabox.height,
    )
    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    native_page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_dict})}
    )
    stream_obj = DecodedStreamObject()
    stream_obj.set_data(b"BT /F1 12 Tf 50 150 Td (AICTE Ref: EOA-12345) Tj ET")
    native_page[NameObject("/Contents")] = stream_obj

    buf_native = io.BytesIO()
    writer_native.write(buf_native)
    reader_native = PdfReader(buf_native)

    # 3. Merge native text onto the scanned page using PdfWriter(clone_from=...)
    writer_scanned = PdfWriter(clone_from=io.BytesIO(buf_img.getvalue()))
    writer_scanned.pages[0].merge_page(reader_native.pages[0])

    out_buf = io.BytesIO()
    writer_scanned.write(out_buf)
    pdf_bytes = out_buf.getvalue()

    # 4. Extract text
    result = text_extraction_service.extract_from_bytes(pdf_bytes, "application/pdf")

    assert result.page_count == 1
    assert result.pages[0].method == PageExtractionMethod.OCR
    # BOTH native text and OCR text must be preserved in result.full_text
    assert "AICTE Ref: EOA-12345" in result.full_text
    assert "SCANNED STRUCTURAL STABILITY" in result.full_text

    # Verify provenance distinction
    lines = result.pages[0].lines
    native_lines = [l for l in lines if "AICTE Ref: EOA-12345" in l.text]
    ocr_lines = [l for l in lines if "SCANNED STRUCTURAL STABILITY" in l.text]

    assert len(native_lines) == 1
    assert native_lines[0].confidence is None
    assert native_lines[0].bounding_box is None

    assert len(ocr_lines) >= 1
    assert ocr_lines[0].confidence is not None
    assert ocr_lines[0].bounding_box is not None
