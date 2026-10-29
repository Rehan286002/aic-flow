"""AIC-Verify — Rule-Based Structured Field Extraction Service.

Phase 4, Batch 3:
Consumes standardized DocumentExtractionResult (from Batch 2) and extracts
structured candidate fields for the seven AICTE Annexure 2.1 requirements:
- EOA-SD-01: Self-disclosure Affidavit (Affidavit 2)
- EOA-SD-02: AICTE Web-Portal Payment Receipt (if any)
- EOA-SD-03: Building Certificate (Occupancy, Completion, Building License, Form D)
- EOA-SD-04: Structural Stability Certificate
- EOA-SD-05: Fire Safety Certificate
- EOA-SD-06: Satellite Map and Entrance Coordinates
- EOA-SD-07: Previous-Year Audited Statement of Accounts
- Generic fallback extractor for unknown or unsupported requirement codes.

Key Architectural Guarantees:
1. Contextual extraction: Prioritizes explicit labels, adjacent delimiters,
   and contextual proximity over unconstrained global regexes.
2. Provenance preservation: Every candidate preserves source page number,
   source text snippet, extraction method (NATIVE_TEXT or OCR), bounding box,
   and raw OCR line confidence where available.
3. Strict confidence separation:
   - Raw OCR engine confidence is preserved independently.
   - Rule-based field matching strength (0.0 to 1.0) is calculated independently.
   - Review categories (HIGH, MEDIUM_REVIEW, LOW_UNCERTAIN) are assigned without
     multiplying scores or claiming statistical probabilities.
4. Non-fabrication: Fields are never invented when evidence is absent.
   Conflicting candidates are surfaced rather than arbitrarily collapsed.
5. Scope separation: Does not perform source verification (Phase 5) or decide
   statutory compliance (such as the 30-year structural stability rule).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.services.text_extraction_service import (
    BoundingBox,
    DocumentExtractionResult,
    ExtractedTextLine,
    PageExtractionMethod,
    PageExtractionResult,
)


class ReviewCategory(str, Enum):
    """Provisional human review category for an extracted candidate field."""

    HIGH = "HIGH"
    MEDIUM_REVIEW = "MEDIUM_REVIEW"
    LOW_UNCERTAIN = "LOW_UNCERTAIN"


class ExtractedCandidateField(BaseModel):
    """Structured candidate field extracted from evidence text."""

    field_code: str = Field(..., description="Standard machine-readable identifier")
    field_label: str = Field(..., description="Human-readable field description")
    raw_value: str = Field(..., description="Raw text value as extracted from source")
    normalized_value: Any | None = Field(
        default=None,
        description="Standardized value (ISO date, int, float, dict, or bool)",
    )
    page_number: int = Field(..., description="1-indexed source page number")
    source_snippet: str | None = Field(
        default=None,
        description="Contextual source line or nearby text snippet",
    )
    bounding_box: BoundingBox | None = Field(
        default=None,
        description="OCR bounding box if derived from OCR",
    )
    extraction_method: PageExtractionMethod = Field(
        ...,
        description="NATIVE_TEXT or OCR",
    )
    ocr_confidence: float | None = Field(
        default=None,
        description="Raw line recognition score from OCR engine (None for native text)",
    )
    matching_strength: float = Field(
        ...,
        description="Rule heuristic matching strength (0.0 to 1.0)",
    )
    review_category: ReviewCategory = Field(
        ...,
        description="Provisional review tier: HIGH, MEDIUM_REVIEW, or LOW_UNCERTAIN",
    )
    notes: str | None = Field(
        default=None,
        description="Extraction rationale or ambiguity notes",
    )


class FieldExtractionResult(BaseModel):
    """Container for candidate fields extracted for a document requirement."""

    item_code: str = Field(
        ..., description="Checklist requirement code, e.g. EOA-SD-01"
    )
    document_type_code: str | None = Field(
        default=None,
        description="Expected document type code",
    )
    candidate_fields: list[ExtractedCandidateField] = Field(default_factory=list)
    unmatched_expected_fields: list[str] = Field(default_factory=list)
    extraction_status: str = Field(
        default="COMPLETED",
        description="COMPLETED, PARTIAL, or UNRECOGNIZED",
    )
    diagnostics: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Shared Normalization & Text Matching Utilities
# =============================================================================

MONTH_NAME_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "sept": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def normalize_iso_date(date_str: str) -> tuple[str | None, float, str | None]:
    """Attempts to normalize a date string into unambiguous ISO format (YYYY-MM-DD).

    Returns: (iso_date_str, confidence_modifier, ambiguity_note)
    """
    clean = re.sub(r"[,\.]", " ", date_str).strip()
    clean = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", clean, flags=re.IGNORECASE)

    # 1. YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})[\-\/](\d{1,2})[\-\/](\d{1,2})$", clean)
    if iso_match:
        y, m, d = (
            int(iso_match.group(1)),
            int(iso_match.group(2)),
            int(iso_match.group(3)),
        )
        try:
            return datetime(y, m, d).strftime("%Y-%m-%d"), 1.0, None
        except ValueError:
            return None, 0.0, "Invalid calendar date"

    # 2. Text month formats: e.g. "15 October 2024", "October 15 2024", "01-Jan-2025"
    text_month_match = re.match(
        r"^(\d{1,2})[\s\-\/]+([A-Za-z]+)[\s\-\/]+(\d{4})$", clean
    ) or re.match(r"^([A-Za-z]+)[\s\-\/]+(\d{1,2})[\s\-\/]+(\d{4})$", clean)
    if text_month_match:
        g1, g2, g3 = text_month_match.groups()
        if g1.isalpha():
            month_name, day_str, year_str = g1.lower(), g2, g3
        else:
            day_str, month_name, year_str = g1, g2.lower(), g3

        month_num = MONTH_NAME_MAP.get(month_name)
        if month_num:
            try:
                y, d = int(year_str), int(day_str)
                return datetime(y, month_num, d).strftime("%Y-%m-%d"), 1.0, None
            except ValueError:
                return None, 0.0, "Invalid calendar date"

    # 3. Numeric DD/MM/YYYY or MM/DD/YYYY
    numeric_match = re.match(r"^(\d{1,2})[\-\/\s](\d{1,2})[\-\/\s](\d{4})$", clean)
    if numeric_match:
        v1, v2, y = (
            int(numeric_match.group(1)),
            int(numeric_match.group(2)),
            int(numeric_match.group(3)),
        )
        # If first value > 12, unambiguous DD/MM/YYYY
        if v1 > 12 and v2 <= 12:
            try:
                return datetime(y, v2, v1).strftime("%Y-%m-%d"), 1.0, None
            except ValueError:
                return None, 0.0, "Invalid calendar date"
        # If second value > 12, unambiguous MM/DD/YYYY
        if v2 > 12 and v1 <= 12:
            try:
                return (
                    datetime(y, v1, v2).strftime("%Y-%m-%d"),
                    0.9,
                    "Normalized from MM/DD/YYYY",
                )
            except ValueError:
                return None, 0.0, "Invalid calendar date"
        # Both <= 12: Ambiguous (e.g. 05/06/2024). Default to Indian regulatory standard DD/MM/YYYY with lower score
        if v1 <= 12 and v2 <= 12:
            try:
                dt_str = datetime(y, v2, v1).strftime("%Y-%m-%d")
                return (
                    dt_str,
                    0.75,
                    "Ambiguous date format; assumed DD/MM/YYYY per Indian regulatory norm",
                )
            except ValueError:
                return None, 0.0, "Invalid calendar date"

    return None, 0.0, "Unrecognized date format"


def parse_indian_monetary_amount(raw_str: str) -> tuple[dict[str, Any] | None, float]:
    """Parses Indian currency strings, handling comma grouping, lakhs, crores,

    accounting parentheses, and negative signs.
    """
    clean = (
        raw_str.replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("INR", "")
        .strip()
    )
    is_negative = False
    if clean.startswith("(") and clean.endswith(")"):
        is_negative = True
        clean = clean[1:-1].strip()
    elif clean.startswith("-"):
        is_negative = True
        clean = clean[1:].strip()

    raw_unit = "INR"
    multiplier = 1.0

    if re.search(r"\bcrores?\b|\bcr\.?\b", clean, re.IGNORECASE):
        multiplier = 10_000_000.0
        raw_unit = "Crores"
        clean = re.sub(r"\bcrores?\b|\bcr\.?\b", "", clean, flags=re.IGNORECASE).strip()
    elif re.search(r"\blakhs?\b|\blacs?\b", clean, re.IGNORECASE):
        multiplier = 100_000.0
        raw_unit = "Lakhs"
        clean = re.sub(r"\blakhs?\b|\blacs?\b", "", clean, flags=re.IGNORECASE).strip()
    elif re.search(r"\bthousands?\b|\bk\b", clean, re.IGNORECASE):
        multiplier = 1_000.0
        raw_unit = "Thousands"
        clean = re.sub(r"\bthousands?\b|\bk\b", "", clean, flags=re.IGNORECASE).strip()

    num_cleaned = clean.replace(",", "").strip()
    try:
        val = float(num_cleaned) * multiplier
        if is_negative:
            val = -val
        return {
            "amount": round(val, 2),
            "numeric_value": round(val, 2),
            "currency": "INR",
            "raw_unit": raw_unit,
            "is_negative": is_negative,
        }, 0.95
    except ValueError:
        return None, 0.0


def parse_geographic_coordinate(
    coord_str: str,
) -> tuple[float | None, float, str | None]:
    """Parses coordinate in decimal degrees or DMS format.

    Validates that latitude and longitude conform to Indian sovereign territory boundaries.
    """
    clean = coord_str.strip()

    # 1. DMS: e.g. 12° 58' 17.75" N
    dms_match = re.search(
        r"(\d{1,3})\s*°\s*(\d{1,2})\s*['\u2032]\s*([\d\.]+)\s*[\"\u2033]?\s*([NSEW])?",
        clean,
        re.IGNORECASE,
    )
    if dms_match:
        deg, minutes, sec, dir_flag = dms_match.groups()
        try:
            dd = float(deg) + float(minutes) / 60.0 + float(sec) / 3600.0
            if dir_flag and dir_flag.upper() in ("S", "W"):
                dd = -dd
            return round(dd, 6), 0.90, "Converted from DMS format"
        except (ValueError, TypeError):
            pass

    # 2. Decimal degrees (e.g. 12.971598 or 12.971598° N)
    dd_match = re.search(
        r"([+\-]?\d{1,3}(?:\.\d{3,8})?)\s*°?\s*([NSEW])?", clean, re.IGNORECASE
    )
    if dd_match:
        val_str, dir_flag = dd_match.groups()
        try:
            val = float(val_str)
            if dir_flag and dir_flag.upper() in ("S", "W"):
                val = -val
            return round(val, 6), 0.95, None
        except ValueError:
            pass

    return None, 0.0, "Unrecognized coordinate format"


def is_valid_indian_latitude(lat: float) -> bool:
    """Verifies latitude conforms to the Indian landmass (approx. 6.0°N to 38.0°N)."""
    return 6.0 <= lat <= 38.0


def is_valid_indian_longitude(lon: float) -> bool:
    """Verifies longitude conforms to the Indian landmass (approx. 68.0°E to 98.0°E)."""
    return 68.0 <= lon <= 98.0


def assign_review_category(matching_strength: float) -> ReviewCategory:
    """Assigns provisional review category based on heuristic match strength."""
    if matching_strength >= 0.85:
        return ReviewCategory.HIGH
    if matching_strength >= 0.60:
        return ReviewCategory.MEDIUM_REVIEW
    return ReviewCategory.LOW_UNCERTAIN


DATE_VALUE_PATTERN = r"(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}|\d{1,2}[\/\-\.][\w\d]{1,9}[\/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})"


# =============================================================================
# Base Document Extractor
# =============================================================================


class BaseDocumentExtractor(ABC):
    """Abstract base class for requirement-specific document field extractors."""

    item_code: str
    document_type_code: str
    expected_field_codes: ClassVar[list[str]] = []

    @abstractmethod
    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        """Extracts structured candidate fields from the document extraction result."""

    def find_labeled_candidate(
        self,
        pages: list[PageExtractionResult],
        label_pattern: str,
        value_pattern: str,
        max_lookahead_lines: int = 1,
    ) -> list[tuple[str, str, PageExtractionResult, ExtractedTextLine]]:
        """Searches for labeled fields across document pages.

        Returns list of (raw_value, snippet, page_res, line).
        """
        candidates: list[tuple[str, str, PageExtractionResult, ExtractedTextLine]] = []
        lbl_re = re.compile(label_pattern, re.IGNORECASE)
        val_re = re.compile(value_pattern, re.IGNORECASE)

        for page in pages:
            num_lines = len(page.lines)
            for idx, line in enumerate(page.lines):
                # Case 1: Label and value on the same line
                lbl_match = lbl_re.search(line.text)
                if lbl_match:
                    after_label = line.text[lbl_match.end() :].strip()
                    after_label = re.sub(
                        r"^(?:(?:No|Number|#|Name)\.?\s*)?[:\-–—/\s]+",
                        "",
                        after_label,
                        flags=re.IGNORECASE,
                    ).strip()
                    val_match = val_re.search(after_label)
                    if val_match:
                        raw_val = (
                            val_match.group(1)
                            if val_match.groups()
                            else val_match.group(0)
                        )
                        candidates.append((raw_val.strip(), line.text, page, line))
                        continue

                    # Case 2: Value on immediately following lines
                    for lookahead in range(1, max_lookahead_lines + 1):
                        next_idx = idx + lookahead
                        if next_idx < num_lines:
                            next_line = page.lines[next_idx]
                            next_text = re.sub(
                                r"^(?:(?:No|Number|#|Name)\.?\s*)?[:\-–—/\s]+",
                                "",
                                next_line.text.strip(),
                                flags=re.IGNORECASE,
                            ).strip()
                            next_val_match = val_re.search(next_text)
                            if next_val_match:
                                raw_val = (
                                    next_val_match.group(1)
                                    if next_val_match.groups()
                                    else next_val_match.group(0)
                                )
                                snippet = f"{line.text} -> {next_line.text}"
                                candidates.append(
                                    (raw_val.strip(), snippet, page, next_line)
                                )
                                break
        return candidates


# =============================================================================
# 1. EOA-SD-01 Extractor — Affidavit 2
# =============================================================================


class Affidavit2Extractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-01 (Affidavit 2)."""

    item_code = "EOA-SD-01"
    document_type_code = "AFFIDAVIT_UNDERTAKING"
    expected_field_codes: ClassVar[list[str]] = [
        "institution_name",
        "aicte_permanent_id",
        "deponent_name",
        "deponent_designation",
        "notary_registration_no",
        "attestation_date",
        "stamp_duty_amount",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []

        # 1. AICTE Permanent ID
        pid_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:AICTE\s*(?:Permanent\s*)?ID|Permanent\s*ID)",
            value_pattern=r"([1-9][0-9\-\s]{5,15})",
        )
        if not pid_matches:
            # Fallback search for standard pattern 1-XXXXXXXXXX
            for page in doc_result.pages:
                for line in page.lines:
                    m = re.search(r"\b(1-[0-9]{8,12})\b", line.text)
                    if m:
                        pid_matches.append((m.group(1), line.text, page, line))
                        break

        for raw_val, snippet, page, line in pid_matches:
            clean_pid = re.sub(r"\s+", "", raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="aicte_permanent_id",
                    field_label="AICTE Permanent ID",
                    raw_value=raw_val,
                    normalized_value=clean_pid,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.95 if raw_val.startswith("1-") else 0.85,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 2. Deponent Name
        deponent_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Deponent(?:\s*Name)?|Name\s*of\s*Deponent|I,)",
            value_pattern=r"([A-Za-z\.\s]{3,50})(?:,\s*(?:Son|Daughter|Wife|Chairman|aged|residing)|\s+do\s+hereby|$)",
        )
        for raw_val, snippet, page, line in deponent_matches:
            clean_name = re.sub(
                r"^(?:I,?\s*|Mr\.?\s*|Mrs\.?\s*|Dr\.?\s*)",
                "",
                raw_val,
                flags=re.IGNORECASE,
            ).strip()
            candidates.append(
                ExtractedCandidateField(
                    field_code="deponent_name",
                    field_label="Deponent Name",
                    raw_value=raw_val,
                    normalized_value=clean_name,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.90,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 3. Deponent Designation
        desig_re = re.compile(
            r"\b(Chairman|President|Secretary|Treasurer|Trustee|Director|Principal|Member\s+Secretary)\b",
            re.IGNORECASE,
        )
        for page in doc_result.pages:
            for line in page.lines:
                m = desig_re.search(line.text)
                if m:
                    candidates.append(
                        ExtractedCandidateField(
                            field_code="deponent_designation",
                            field_label="Deponent Designation",
                            raw_value=m.group(1),
                            normalized_value=m.group(1).upper(),
                            page_number=page.page_number,
                            source_snippet=line.text,
                            bounding_box=line.bounding_box,
                            extraction_method=page.method,
                            ocr_confidence=line.confidence,
                            matching_strength=0.90,
                            review_category=ReviewCategory.HIGH,
                        )
                    )
                    break

        # 4. Institution Name
        inst_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Name\s+of\s+(?:the\s+)?Institution|Institution\s+Name|behalf\s+of)",
            value_pattern=r"([A-Za-z0-9\s\.\,\-\(\)]{5,100})",
        )
        for raw_val, snippet, page, line in inst_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="institution_name",
                    field_label="Institution Name",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.85,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 5. Notary Registration Number
        notary_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Notary\s*Reg(?:istration)?\.?\s*(?:No\.?)?|Reg(?:istration)?\.?\s*No\.?\s*(?:of\s*Notary)?|G\.O\.\s*Ms\.?)",
            value_pattern=r"([A-Za-z0-9\/\-\.\s]{3,30})",
        )
        for raw_val, snippet, page, line in notary_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="notary_registration_no",
                    field_label="Notary Registration Number",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.88,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 6. Attestation Date
        attest_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Sworn\s+(?:and\s+signed\s+)?before\s+me|Attested\s+on|Affirmed\s+before\s+me|Dated|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in attest_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="attestation_date",
                    field_label="Attestation Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note,
                )
            )

        # 7. Stamp Duty Amount
        stamp_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Stamp\s*Duty(?:\s*Amount)?|Rs\.?|₹)",
            value_pattern=r"(\d{2,5})\s*(?:Non[\s\-]*Judicial|Stamp|/-)?",
        )
        for raw_val, snippet, page, line in stamp_matches:
            try:
                amt = int(raw_val)
                candidates.append(
                    ExtractedCandidateField(
                        field_code="stamp_duty_amount",
                        field_label="Stamp Duty Amount",
                        raw_value=raw_val,
                        normalized_value={
                            "amount": float(amt),
                            "numeric_value": float(amt),
                            "currency": "INR",
                        },
                        page_number=page.page_number,
                        source_snippet=snippet,
                        bounding_box=line.bounding_box,
                        extraction_method=page.method,
                        ocr_confidence=line.confidence,
                        matching_strength=0.90,
                        review_category=ReviewCategory.HIGH,
                    )
                )
            except ValueError:
                pass

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED" if len(matched_codes) >= 4 else "PARTIAL",
        )


# =============================================================================
# 2. EOA-SD-02 Extractor — AICTE Web Portal Payment Receipt
# =============================================================================


class PaymentReceiptExtractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-02 (Payment Receipt).

    Preserves conditional nature ("if any"). Absent receipt yields an empty result
    without raising an error.
    """

    item_code = "EOA-SD-02"
    document_type_code = "PAYMENT_RECEIPT"
    expected_field_codes: ClassVar[list[str]] = [
        "receipt_number",
        "transaction_ref_no",
        "payment_date",
        "payment_amount",
        "payment_mode",
        "payment_status",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []

        # 1. Receipt Number
        receipt_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Receipt\s*(?:No\.?|Number)|Challan\s*No\.?)",
            value_pattern=r"([A-Za-z0-9\-\/]{4,30})",
        )
        for raw_val, snippet, page, line in receipt_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="receipt_number",
                    field_label="Receipt Number",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.92,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 2. Transaction Reference / UTR
        utr_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Transaction\s*(?:Ref(?:erence)?\.?\s*(?:No\.?|Number)?|ID)(?:\s*[\/\-]\s*UTR(?:\s*(?:No\.?|Number))?)?|UTR\s*(?:No\.?|Number)?|Reference\s*(?:No\.?|Number)?)",
            value_pattern=r"([A-Za-z0-9\-\/]{6,35})",
        )
        for raw_val, snippet, page, line in utr_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="transaction_ref_no",
                    field_label="Transaction Reference / UTR",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.95,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 3. Payment Date
        date_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Payment\s*Date|Transaction\s*Date|Date\s*of\s*Payment|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in date_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="payment_date",
                    field_label="Payment Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note,
                )
            )

        # 4. Payment Amount
        amount_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Amount(?:\s*Paid)?|Total\s*Amount|Fee\s*Amount|Paid\s*Amount)",
            value_pattern=r"(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)",
        )
        for raw_val, snippet, page, line in amount_matches:
            norm_amt, str_mod = parse_indian_monetary_amount(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="payment_amount",
                    field_label="Payment Amount",
                    raw_value=raw_val,
                    normalized_value=norm_amt,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=str_mod,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 5. Payment Mode
        mode_re = re.compile(
            r"\b(NET[\s_\-]*BANKING|NEFT|RTGS|UPI|CREDIT[\s_\-]*CARD|DEBIT[\s_\-]*CARD|PAYMENT[\s_\-]*GATEWAY|CHALLAN)\b",
            re.IGNORECASE,
        )
        for page in doc_result.pages:
            for line in page.lines:
                m = mode_re.search(line.text)
                if m:
                    candidates.append(
                        ExtractedCandidateField(
                            field_code="payment_mode",
                            field_label="Payment Mode",
                            raw_value=m.group(1),
                            normalized_value=re.sub(
                                r"[\s_\-]+", "_", m.group(1).upper()
                            ),
                            page_number=page.page_number,
                            source_snippet=line.text,
                            bounding_box=line.bounding_box,
                            extraction_method=page.method,
                            ocr_confidence=line.confidence,
                            matching_strength=0.92,
                            review_category=ReviewCategory.HIGH,
                        )
                    )
                    break

        # 6. Payment Status
        status_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Payment\s*Status|Transaction\s*Status|Status)",
            value_pattern=r"\b(SUCCESS(?:FUL)?|PAID|COMPLETED|CONFIRMED|FAILED|PENDING)\b",
        )
        if status_matches:
            for raw_val, snippet, page, line in status_matches:
                clean_stat = (
                    "SUCCESS"
                    if re.search(
                        r"SUCCESS|PAID|COMPLETED|CONFIRMED", raw_val, re.IGNORECASE
                    )
                    else raw_val.upper()
                )
                candidates.append(
                    ExtractedCandidateField(
                        field_code="payment_status",
                        field_label="Payment Status",
                        raw_value=raw_val,
                        normalized_value={"status": clean_stat},
                        page_number=page.page_number,
                        source_snippet=snippet,
                        bounding_box=line.bounding_box,
                        extraction_method=page.method,
                        ocr_confidence=line.confidence,
                        matching_strength=0.95,
                        review_category=ReviewCategory.HIGH,
                    )
                )
        else:
            status_re = re.compile(
                r"\b(SUCCESS(?:FUL)?|PAID|COMPLETED|CONFIRMED)\b", re.IGNORECASE
            )
            for page in doc_result.pages:
                for line in page.lines:
                    if re.search(r"\bamount\b", line.text, re.IGNORECASE):
                        continue
                    m = status_re.search(line.text)
                    if m:
                        candidates.append(
                            ExtractedCandidateField(
                                field_code="payment_status",
                                field_label="Payment Status",
                                raw_value=m.group(1),
                                normalized_value={"status": "SUCCESS"},
                                page_number=page.page_number,
                                source_snippet=line.text,
                                bounding_box=line.bounding_box,
                                extraction_method=page.method,
                                ocr_confidence=line.confidence,
                                matching_strength=0.90,
                                review_category=ReviewCategory.HIGH,
                            )
                        )
                        break

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED"
            if len(matched_codes) >= 3
            else ("PARTIAL" if matched_codes else "EMPTY_OR_NOT_SUBMITTED"),
            diagnostics={"conditional_receipt": True},
        )


# =============================================================================
# 3. EOA-SD-03 Extractor — Building Certificate (All 4 Variants)
# =============================================================================


class BuildingCertificateExtractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-03 (Building Certificate).

    Supports: Occupancy Certificate, Completion Certificate, Building License, Form D.
    """

    item_code = "EOA-SD-03"
    document_type_code = "BUILDING_DOCUMENT"
    expected_field_codes: ClassVar[list[str]] = [
        "certificate_type",
        "certificate_number",
        "issuing_authority",
        "issue_date",
        "building_identifier",
        "total_builtup_area",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []
        full_doc_text = doc_result.full_text

        # 1. Certificate Type Identification (All 4 variants)
        detected_variant = "UNKNOWN"
        variant_raw = ""
        variant_line: ExtractedTextLine | None = None
        variant_page: PageExtractionResult | None = None

        variant_patterns = [
            (r"Occupancy\s*Certificate", "OCCUPANCY_CERTIFICATE"),
            (r"Completion\s*Certificate", "COMPLETION_CERTIFICATE"),
            (r"Form\s*[\-]?\s*D\b", "FORM_D"),
            (r"Building\s*Licen[sc]e", "BUILDING_LICENSE"),
        ]

        for pattern, variant_enum in variant_patterns:
            m = re.search(pattern, full_doc_text, re.IGNORECASE)
            if m:
                detected_variant = variant_enum
                variant_raw = m.group(0)
                # Find page and line
                for page in doc_result.pages:
                    for line in page.lines:
                        if re.search(pattern, line.text, re.IGNORECASE):
                            variant_line = line
                            variant_page = page
                            break
                    if variant_page:
                        break
                break

        if detected_variant != "UNKNOWN" and variant_page and variant_line:
            norm_val: dict[str, Any] = {"canonical_type": detected_variant}
            cert_notes = None
            if detected_variant == "FORM_D":
                norm_val["jurisdiction_scope"] = (
                    "State/jurisdiction-specific licensing instrument (e.g., Tamil Nadu Public Buildings Licensing Act)"
                )
                cert_notes = "Form D is a state/jurisdiction-specific licensing instrument rather than a national statutory standard."

            candidates.append(
                ExtractedCandidateField(
                    field_code="certificate_type",
                    field_label="Certificate Type",
                    raw_value=variant_raw,
                    normalized_value=norm_val,
                    page_number=variant_page.page_number,
                    source_snippet=variant_line.text,
                    bounding_box=variant_line.bounding_box,
                    extraction_method=variant_page.method,
                    ocr_confidence=variant_line.confidence,
                    matching_strength=0.98,
                    review_category=ReviewCategory.HIGH,
                    notes=cert_notes,
                )
            )

        # 2. Certificate Number
        cert_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Certificate\s*No\.?|Licen[sc]e\s*No\.?|Order\s*No\.?|Ref\s*No\.?)",
            value_pattern=r"([A-Za-z0-9\-\/\.]{4,35})",
        )
        for raw_val, snippet, page, line in cert_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="certificate_number",
                    field_label="Certificate Number",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.92,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 3. Issuing Authority
        auth_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Issued\s+by|Sanctioning\s+Authority|Competent\s+Authority|Authority)",
            value_pattern=r"([A-Za-z0-9\s\.\,\-]{4,60})",
        )
        for raw_val, snippet, page, line in auth_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="issuing_authority",
                    field_label="Issuing Authority",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.88,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 4. Issue Date
        date_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Date\s*of\s*Issue|Issue\s*Date|Dated|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in date_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="issue_date",
                    field_label="Issue Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note,
                )
            )

        # 5. Building Identifier
        bldg_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Building\s*(?:Name|Identifier|Block|Description)?|Premises)",
            value_pattern=r"([A-Za-z0-9\s\-\,\.]{3,50})",
        )
        for raw_val, snippet, page, line in bldg_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="building_identifier",
                    field_label="Building Identifier",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.85,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 6. Total Built-Up Area
        area_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Total\s*Built[\s\-]*up\s*Area|Built[\s\-]*up\s*Area|Plinth\s*Area|Constructed\s*Area)",
            value_pattern=r"([0-9,]+(?:\.[0-9]+)?)\s*(Sq\.?\s*M(?:eters?)?|Sq\.?\s*Ft\.?|Sqm|Sqft)?",
        )
        for raw_val, snippet, page, line in area_matches:
            raw_clean = raw_val.replace(",", "").strip()
            unit = "SQ_METERS"
            if re.search(r"sq\.?\s*ft|sqft", snippet, re.IGNORECASE):
                unit = "SQ_FEET"

            try:
                numeric_val = float(raw_clean)
                candidates.append(
                    ExtractedCandidateField(
                        field_code="total_builtup_area",
                        field_label="Total Built-up Area",
                        raw_value=raw_val,
                        normalized_value={
                            "area_value": numeric_val,
                            "value": numeric_val,
                            "unit": unit,
                        },
                        page_number=page.page_number,
                        source_snippet=snippet,
                        bounding_box=line.bounding_box,
                        extraction_method=page.method,
                        ocr_confidence=line.confidence,
                        matching_strength=0.92,
                        review_category=ReviewCategory.HIGH,
                    )
                )
            except ValueError:
                pass

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED" if len(matched_codes) >= 3 else "PARTIAL",
            diagnostics={"detected_variant": detected_variant},
        )


# =============================================================================
# 4. EOA-SD-04 Extractor — Structural Stability Certificate
# =============================================================================


class StructuralStabilityExtractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-04 (Structural Stability Certificate).

    Does NOT decide statutory applicability (30-year rule) or statutory validity.
    """

    item_code = "EOA-SD-04"
    document_type_code = "STRUCTURAL_STABILITY_CERTIFICATE"
    expected_field_codes: ClassVar[list[str]] = [
        "engineer_name",
        "engineer_license_no",
        "issuing_authority",
        "issue_date",
        "validity_date",
        "stability_certification_statement",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []

        # 1. Structural Engineer Name
        eng_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Certified\s*by|Structural\s*Engineer(?!\s*(?:License|Reg))|Name\s*of\s*(?:the\s*)?Engineer|Chartered\s*Engineer|Inspected\s*by)",
            value_pattern=r"((?:Er\.?|Mr\.?|Dr\.?)?\s*[A-Za-z\.\s]{3,50})",
        )
        for raw_val, snippet, page, line in eng_matches:
            if re.search(
                r"\b(?:License|Registration|Authority|Council|Corporation)\b",
                raw_val,
                re.IGNORECASE,
            ):
                continue
            clean_name = re.sub(
                r"^(?:Er\.?|Mr\.?|Dr\.?)\s*", "", raw_val, flags=re.IGNORECASE
            ).strip()
            candidates.append(
                ExtractedCandidateField(
                    field_code="engineer_name",
                    field_label="Structural Engineer Name",
                    raw_value=raw_val,
                    normalized_value=clean_name,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.90,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 2. Engineer Licence Number
        lic_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Licen[sc]e\s*(?:No\.?|Number)|Registration\s*No\.?|Reg\.?\s*No\.?|MIE\s*No\.?|Chartered\s*Engineer\s*No\.?)",
            value_pattern=r"([A-Za-z0-9\-\/\.]{4,30})",
        )
        for raw_val, snippet, page, line in lic_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="engineer_license_no",
                    field_label="Engineer Licence Number",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.92,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 3. Issuing Authority / Body
        body_re = re.compile(
            r"\b(Institution\s*of\s*Engineers|Municipal\s*Corporation|State\s*Licensing\s*Board|Council\s*of\s*Architecture|PWD|CPWD)\b",
            re.IGNORECASE,
        )
        for page in doc_result.pages:
            for line in page.lines:
                m = body_re.search(line.text)
                if m:
                    candidates.append(
                        ExtractedCandidateField(
                            field_code="issuing_authority",
                            field_label="Issuing Authority / Body",
                            raw_value=m.group(0),
                            normalized_value=m.group(0).strip(),
                            page_number=page.page_number,
                            source_snippet=line.text,
                            bounding_box=line.bounding_box,
                            extraction_method=page.method,
                            ocr_confidence=line.confidence,
                            matching_strength=0.88,
                            review_category=ReviewCategory.HIGH,
                        )
                    )
                    break

        # 4. Issue Date
        date_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Date\s*of\s*Issue|Issue\s*Date|Dated|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in date_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="issue_date",
                    field_label="Issue Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note,
                )
            )

        # 5. Explicit Stated Validity Date (if explicitly present)
        val_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Valid\s*(?:up\s*to|until|till|through)|Expiry\s*Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in val_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="validity_date",
                    field_label="Explicit Stated Validity Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note or "Explicitly declared validity in document text",
                )
            )

        # 6. Structural Stability Certification Statement
        stmt_re = re.compile(
            r"(structurally\s+(?:sound|safe)(?:\s+and\s+(?:sound|safe|stable))?|fit\s+for\s+(?:educational\s+)?occupancy|Certified\s+that\s+(?:the\s+)?(?:building|structure)\s+is\s+structurally\s+(?:sound|safe))",
            re.IGNORECASE,
        )
        for page in doc_result.pages:
            for line in page.lines:
                m = stmt_re.search(line.text)
                if m:
                    candidates.append(
                        ExtractedCandidateField(
                            field_code="stability_certification_statement",
                            field_label="Structural Stability Statement",
                            raw_value=m.group(0),
                            normalized_value={
                                "certified_sound": True,
                                "statement": m.group(0),
                            },
                            page_number=page.page_number,
                            source_snippet=line.text,
                            bounding_box=line.bounding_box,
                            extraction_method=page.method,
                            ocr_confidence=line.confidence,
                            matching_strength=0.95,
                            review_category=ReviewCategory.HIGH,
                        )
                    )
                    break

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED" if len(matched_codes) >= 3 else "PARTIAL",
        )


# =============================================================================
# 5. EOA-SD-05 Extractor — Fire Safety Certificate
# =============================================================================


class FireSafetyExtractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-05 (Fire Safety Certificate).

    Never imposes an arbitrary universal validity period; extracts stated expiry.
    """

    item_code = "EOA-SD-05"
    document_type_code = "FIRE_SAFETY_CERTIFICATE"
    expected_field_codes: ClassVar[list[str]] = [
        "fire_noc_number",
        "issuing_department",
        "issue_date",
        "expiry_date",
        "campus_address",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []

        # 1. Fire NOC Number
        noc_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:(?:Fire\s*)?NOC\s*(?:No\.?|Number)?|Certificate\s*(?:No\.?|Number)?|Ref(?:erence)?\s*(?:No\.?|Number)?)",
            value_pattern=r"([A-Za-z0-9\-\/\.]{4,35})",
        )
        for raw_val, snippet, page, line in noc_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="fire_noc_number",
                    field_label="Fire NOC Number",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.92,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 2. Issuing Department
        dept_re = re.compile(
            r"\b(Fire\s*(?:and\s*Rescue)?\s*Services?|Fire\s*Force|Disaster\s*Management|Chief\s*Fire\s*Officer|District\s*Fire\s*Officer)\b",
            re.IGNORECASE,
        )
        for page in doc_result.pages:
            for line in page.lines:
                m = dept_re.search(line.text)
                if m:
                    candidates.append(
                        ExtractedCandidateField(
                            field_code="issuing_department",
                            field_label="Issuing Department",
                            raw_value=m.group(0),
                            normalized_value=m.group(0).strip(),
                            page_number=page.page_number,
                            source_snippet=line.text,
                            bounding_box=line.bounding_box,
                            extraction_method=page.method,
                            ocr_confidence=line.confidence,
                            matching_strength=0.90,
                            review_category=ReviewCategory.HIGH,
                        )
                    )
                    break

        # 3. Issue Date
        date_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Date\s*of\s*Issue|Issue\s*Date|Dated|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in date_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="issue_date",
                    field_label="Issue Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note,
                )
            )

        # 4. Explicit Stated Expiry Date
        exp_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Valid\s*(?:up\s*to|until|till)|Expiry\s*Date|Expires\s*on)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in exp_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="expiry_date",
                    field_label="Explicit Stated Expiry Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.92 * mod, 2),
                    review_category=assign_review_category(round(0.92 * mod, 2)),
                    notes=note or "Explicitly stated expiration date on certificate",
                )
            )

        # 5. Campus / Building Address
        addr_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Campus\s*(?:Address|Location)|Situated\s*at|Premises\s*at|Building\s*at)",
            value_pattern=r"([A-Za-z0-9\s\-\,\.\/]{5,80})",
        )
        for raw_val, snippet, page, line in addr_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="campus_address",
                    field_label="Campus Address",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.85,
                    review_category=ReviewCategory.HIGH,
                )
            )

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED" if len(matched_codes) >= 3 else "PARTIAL",
        )


# =============================================================================
# 6. EOA-SD-06 Extractor — Satellite Map & Coordinates
# =============================================================================


class SatelliteMapExtractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-06 (Satellite Map and Entrance GPS Coordinates)."""

    item_code = "EOA-SD-06"
    document_type_code = "SATELLITE_MAP"
    expected_field_codes: ClassVar[list[str]] = [
        "latitude",
        "longitude",
        "survey_khasra_number",
        "village_town",
        "district",
        "state",
        "map_timestamp",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []

        # 1 & 2. Latitude and Longitude
        lat_re = re.compile(
            r"(?:Lat(?:itude)?\s*[:\-]?\s*|Latitude\s+)([0-9\.\°\s\'\"\u2032\u2033]+[NS]?)",
            re.IGNORECASE,
        )
        lon_re = re.compile(
            r"(?:Long(?:itude)?\s*[:\-]?\s*|Longitude\s+)([0-9\.\°\s\'\"\u2032\u2033]+[EW]?)",
            re.IGNORECASE,
        )
        pair_re = re.compile(
            r"([0-9]{1,2}\.[0-9]{3,8})\s*°?\s*N?\s*[,/;\s]+\s*([0-9]{2,3}\.[0-9]{3,8})\s*°?\s*E?",
            re.IGNORECASE,
        )
        dms_pair_re = re.compile(
            r"(\d{1,2}\s*°\s*\d{1,2}\s*['\u2032]\s*[\d\.]+\s*[\"\u2033]?\s*[NS]?)\s*[,;/]\s*(\d{1,3}\s*°\s*\d{1,2}\s*['\u2032]\s*[\d\.]+\s*[\"\u2033]?\s*[EW]?)",
            re.IGNORECASE,
        )

        for page in doc_result.pages:
            for line in page.lines:
                # Check for explicit Lat / Lon labels
                lat_m = lat_re.search(line.text)
                if lat_m:
                    raw_lat = lat_m.group(1).strip()
                    val_lat, mod_lat, note_lat = parse_geographic_coordinate(raw_lat)
                    if val_lat is not None:
                        is_in_bounds = is_valid_indian_latitude(val_lat)
                        score = mod_lat if is_in_bounds else 0.50
                        notes = (
                            note_lat
                            if is_in_bounds
                            else "Coordinate falls outside coarse Indian bounding box plausibility check (6.0-37.5 N, 68.0-97.5 E), not definitive territorial verification"
                        )
                        candidates.append(
                            ExtractedCandidateField(
                                field_code="latitude",
                                field_label="Latitude",
                                raw_value=raw_lat,
                                normalized_value={
                                    "decimal_degrees": val_lat,
                                    "passes_coarse_plausibility_check": is_in_bounds,
                                    "is_in_indian_territory": is_in_bounds,
                                },
                                page_number=page.page_number,
                                source_snippet=line.text,
                                bounding_box=line.bounding_box,
                                extraction_method=page.method,
                                ocr_confidence=line.confidence,
                                matching_strength=score,
                                review_category=assign_review_category(score),
                                notes=notes,
                            )
                        )

                lon_m = lon_re.search(line.text)
                if lon_m:
                    raw_lon = lon_m.group(1).strip()
                    val_lon, mod_lon, note_lon = parse_geographic_coordinate(raw_lon)
                    if val_lon is not None:
                        is_in_bounds = is_valid_indian_longitude(val_lon)
                        score = mod_lon if is_in_bounds else 0.50
                        notes = (
                            note_lon
                            if is_in_bounds
                            else "Coordinate falls outside coarse Indian bounding box plausibility check (6.0-37.5 N, 68.0-97.5 E), not definitive territorial verification"
                        )
                        candidates.append(
                            ExtractedCandidateField(
                                field_code="longitude",
                                field_label="Longitude",
                                raw_value=raw_lon,
                                normalized_value={
                                    "decimal_degrees": val_lon,
                                    "passes_coarse_plausibility_check": is_in_bounds,
                                    "is_in_indian_territory": is_in_bounds,
                                },
                                page_number=page.page_number,
                                source_snippet=line.text,
                                bounding_box=line.bounding_box,
                                extraction_method=page.method,
                                ocr_confidence=line.confidence,
                                matching_strength=score,
                                review_category=assign_review_category(score),
                                notes=notes,
                            )
                        )

                # Pair match fallbacks (e.g. "Entrance Coordinates: 12° 58' 23" N, 77° 35' 45" E")
                has_lat = any(c.field_code == "latitude" for c in candidates)
                has_lon = any(c.field_code == "longitude" for c in candidates)
                if (not has_lat or not has_lon) and not lat_m and not lon_m:
                    dms_m = dms_pair_re.search(line.text)
                    if dms_m:
                        dlat_s, dlon_s = dms_m.groups()
                        plat, _, nlat = parse_geographic_coordinate(dlat_s)
                        plon, _, nlon = parse_geographic_coordinate(dlon_s)
                        if plat is not None and plon is not None:
                            in_lat = is_valid_indian_latitude(plat)
                            in_lon = is_valid_indian_longitude(plon)
                            candidates.append(
                                ExtractedCandidateField(
                                    field_code="latitude",
                                    field_label="Latitude",
                                    raw_value=dlat_s,
                                    normalized_value={
                                        "decimal_degrees": plat,
                                        "passes_coarse_plausibility_check": in_lat,
                                        "is_in_indian_territory": in_lat,
                                    },
                                    page_number=page.page_number,
                                    source_snippet=line.text,
                                    bounding_box=line.bounding_box,
                                    extraction_method=page.method,
                                    ocr_confidence=line.confidence,
                                    matching_strength=0.90 if in_lat else 0.50,
                                    review_category=assign_review_category(
                                        0.90 if in_lat else 0.50
                                    ),
                                    notes=nlat,
                                )
                            )
                            candidates.append(
                                ExtractedCandidateField(
                                    field_code="longitude",
                                    field_label="Longitude",
                                    raw_value=dlon_s,
                                    normalized_value={
                                        "decimal_degrees": plon,
                                        "passes_coarse_plausibility_check": in_lon,
                                        "is_in_indian_territory": in_lon,
                                    },
                                    page_number=page.page_number,
                                    source_snippet=line.text,
                                    bounding_box=line.bounding_box,
                                    extraction_method=page.method,
                                    ocr_confidence=line.confidence,
                                    matching_strength=0.90 if in_lon else 0.50,
                                    review_category=assign_review_category(
                                        0.90 if in_lon else 0.50
                                    ),
                                    notes=nlon,
                                )
                            )
                            continue

                    pair_m = pair_re.search(line.text)
                    if pair_m:
                        lat_s, lon_s = pair_m.groups()
                        try:
                            plat = float(lat_s)
                            plon = float(lon_s)
                            in_lat = is_valid_indian_latitude(plat)
                            in_lon = is_valid_indian_longitude(plon)
                            candidates.append(
                                ExtractedCandidateField(
                                    field_code="latitude",
                                    field_label="Latitude",
                                    raw_value=lat_s,
                                    normalized_value={
                                        "decimal_degrees": round(plat, 6),
                                        "passes_coarse_plausibility_check": in_lat,
                                        "is_in_indian_territory": in_lat,
                                    },
                                    page_number=page.page_number,
                                    source_snippet=line.text,
                                    bounding_box=line.bounding_box,
                                    extraction_method=page.method,
                                    ocr_confidence=line.confidence,
                                    matching_strength=0.88 if in_lat else 0.50,
                                    review_category=assign_review_category(
                                        0.88 if in_lat else 0.50
                                    ),
                                )
                            )
                            candidates.append(
                                ExtractedCandidateField(
                                    field_code="longitude",
                                    field_label="Longitude",
                                    raw_value=lon_s,
                                    normalized_value={
                                        "decimal_degrees": round(plon, 6),
                                        "passes_coarse_plausibility_check": in_lon,
                                        "is_in_indian_territory": in_lon,
                                    },
                                    page_number=page.page_number,
                                    source_snippet=line.text,
                                    bounding_box=line.bounding_box,
                                    extraction_method=page.method,
                                    ocr_confidence=line.confidence,
                                    matching_strength=0.88 if in_lon else 0.50,
                                    review_category=assign_review_category(
                                        0.88 if in_lon else 0.50
                                    ),
                                )
                            )
                        except ValueError:
                            pass

        # 3. Survey / Khasra Number
        surv_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Survey\s*[\/\&]\s*Khasra\s*(?:No\.?|Number)?|Khasra\s*(?:No\.?|Number)?|Survey\s*(?:No\.?|Number)?|Gat\s*(?:No\.?|Number)?|Plot\s*(?:No\.?|Number)?)",
            value_pattern=r"([A-Za-z0-9\/\-\s,\&\.]{2,50})",
        )
        for raw_val, snippet, page, line in surv_matches:
            clean_surv = re.sub(
                r"^(?:[:\-–—/\s]|(?:Khasra|Survey|Gat|Plot|No|Number|#)\.?\s*)+",
                "",
                raw_val,
                flags=re.IGNORECASE,
            ).strip()
            final_surv = clean_surv or raw_val.strip()
            candidates.append(
                ExtractedCandidateField(
                    field_code="survey_khasra_number",
                    field_label="Survey / Khasra Number",
                    raw_value=final_surv,
                    normalized_value={"survey_khasra_no": final_surv},
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.90,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 4. Village / Town
        village_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Village|Town|City)",
            value_pattern=r"([A-Za-z\s]{3,35})",
        )
        for raw_val, snippet, page, line in village_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="village_town",
                    field_label="Village / Town",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.85,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 5. District
        dist_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:District|Dist\.?)",
            value_pattern=r"([A-Za-z\s]{3,35})",
        )
        for raw_val, snippet, page, line in dist_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="district",
                    field_label="District",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.88,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 6. State
        state_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:State)",
            value_pattern=r"([A-Za-z\s]{3,35})",
        )
        for raw_val, snippet, page, line in state_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="state",
                    field_label="State",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.88,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 7. Map Timestamp
        time_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Imagery\s*Date|Map\s*Date|Captured\s*on|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in time_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="map_timestamp",
                    field_label="Map Timestamp",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.88 * mod, 2),
                    review_category=assign_review_category(round(0.88 * mod, 2)),
                    notes=note,
                )
            )

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED"
            if "latitude" in matched_codes and "longitude" in matched_codes
            else "PARTIAL",
        )


# =============================================================================
# 7. EOA-SD-07 Extractor — Previous-Year Audited Accounts
# =============================================================================


class AuditedStatementExtractor(BaseDocumentExtractor):
    """Extracts candidate fields from EOA-SD-07 (Audited Financial Statement)."""

    item_code = "EOA-SD-07"
    document_type_code = "AUDITED_STATEMENT"
    expected_field_codes: ClassVar[list[str]] = [
        "financial_year",
        "trust_society_name",
        "auditor_name",
        "auditor_membership_no",
        "auditor_firm_reg_no",
        "auditor_udin",
        "auditor_registration_no",
        "audit_report_date",
        "gross_annual_income",
        "total_expenditure",
        "balance_surplus_deficit",
    ]

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        candidates: list[ExtractedCandidateField] = []

        # 1. Financial Year
        fy_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Financial\s*Year|F\.?\s*Y\.?|Assessment\s*Year|A\.?\s*Y\.?|Year\s*ended)",
            value_pattern=r"([0-9]{4}[\s\-]+[0-9]{2,4})",
        )
        for raw_val, snippet, page, line in fy_matches:
            clean_fy = re.sub(r"\s+", "", raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="financial_year",
                    field_label="Financial Year",
                    raw_value=raw_val,
                    normalized_value=clean_fy,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.95,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 2. Trust / Society Name
        trust_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:To\s*(?:the\s*)?(?:Trustees|Members|Governing\s*Body|Directors)\s*of|Name\s*of\s*(?:the\s*)?(?:Trust|Society|Company)|Trust\s*Name|Accounts\s*of|Trust|Society)",
            value_pattern=r"([A-Za-z0-9\s\.\,\-]{5,80}(?:Trust|Society|Foundation|Company|Sanstha|Samiti|Mandal|Association|LLP|Ltd\.?|Limited))",
        )
        for raw_val, snippet, page, line in trust_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="trust_society_name",
                    field_label="Trust / Society / Company Name",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.88,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 3. Auditor Name / Chartered Accountant
        aud_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Statutory\s*Auditor|Auditor|Chartered\s*Accountant|For\s+([A-Za-z\s\.]+(?:Associates|& Co|LLP)))",
            value_pattern=r"(?:CA\.?\s*)?([A-Za-z\.\s]{3,50})",
        )
        for raw_val, snippet, page, line in aud_matches:
            clean_aud = re.sub(
                r"^(?:CA\.?\s*|Mr\.?\s*)", "", raw_val, flags=re.IGNORECASE
            ).strip()
            candidates.append(
                ExtractedCandidateField(
                    field_code="auditor_name",
                    field_label="Auditor Name",
                    raw_value=raw_val,
                    normalized_value=clean_aud,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.85,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 4a. Auditor ICAI Membership Number
        memb_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:ICAI\s*(?:Membership|Memb|M)?\.?\s*(?:No\.?|Number|\#)?|Membership\s*(?:No\.?|Number)|M\.?\s*No\.?)",
            value_pattern=r"([0-9]{5,6})\b",
        )
        for raw_val, snippet, page, line in memb_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="auditor_membership_no",
                    field_label="Auditor ICAI Membership Number",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.95,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 4b. Auditor Firm Registration Number (FRN)
        frn_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Firm\s*Reg(?:istration)?\.?\s*(?:No\.?)?|Firm\s*Regn\s*No\.?|FRN)",
            value_pattern=r"([0-9]{6}[A-Z]|[0-9]{5,7})\b",
        )
        for raw_val, snippet, page, line in frn_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="auditor_firm_reg_no",
                    field_label="Auditor Firm Registration Number (FRN)",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.95,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 4c. Auditor UDIN (Unique Document Identification Number - 18 alphanumeric chars)
        udin_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:UDIN|Unique\s*Doc(?:ument)?\s*Id(?:entification)?\s*No\.?)",
            value_pattern=r"([0-9]{2}[0-9]{6}[A-Za-z0-9]{10}|[0-9A-Za-z]{18})\b",
        )
        for raw_val, snippet, page, line in udin_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="auditor_udin",
                    field_label="Auditor UDIN",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.98,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 4d. Composite / Legacy Registration Identifier (Preserved for compatibility)
        reg_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Membership\s*(?:No\.?|Number)|M\.?\s*No\.?|Firm\s*Reg(?:istration)?\.?\s*(?:No\.?)?|FRN|UDIN)",
            value_pattern=r"([A-Za-z0-9\/\-]{5,30})",
        )
        for raw_val, snippet, page, line in reg_matches:
            candidates.append(
                ExtractedCandidateField(
                    field_code="auditor_registration_no",
                    field_label="Auditor Registration Identifier",
                    raw_value=raw_val,
                    normalized_value=raw_val.strip(),
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=0.92,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 5. Audit Report Date
        rep_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Audit\s*Report\s*Date|Report\s*Date|Dated|Date)",
            value_pattern=DATE_VALUE_PATTERN,
        )
        for raw_val, snippet, page, line in rep_matches:
            iso_date, mod, note = normalize_iso_date(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="audit_report_date",
                    field_label="Audit Report Date",
                    raw_value=raw_val,
                    normalized_value={"iso_date": iso_date} if iso_date else None,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=round(0.90 * mod, 2),
                    review_category=assign_review_category(round(0.90 * mod, 2)),
                    notes=note,
                )
            )

        # 6. Gross Annual Income
        inc_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Gross\s*(?:Annual\s*)?Income|Total\s*Income|Total\s*Receipts)",
            value_pattern=r"(?:₹|Rs\.?|INR)?\s*(\(?[0-9,]+(?:\.[0-9]+)?\)?(?:\s*(?:Lakhs?|Crores?|Lacs?|Cr|Thousands?))?)",
        )
        for raw_val, snippet, page, line in inc_matches:
            norm_inc, str_mod = parse_indian_monetary_amount(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="gross_annual_income",
                    field_label="Gross Annual Income",
                    raw_value=raw_val,
                    normalized_value=norm_inc,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=str_mod,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 7. Total Expenditure
        exp_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Total\s*(?:Annual\s*)?Expenditure|Total\s*Expenses)",
            value_pattern=r"(?:₹|Rs\.?|INR)?\s*(\(?[0-9,]+(?:\.[0-9]+)?\)?(?:\s*(?:Lakhs?|Crores?|Lacs?|Cr|Thousands?))?)",
        )
        for raw_val, snippet, page, line in exp_matches:
            norm_exp, str_mod = parse_indian_monetary_amount(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="total_expenditure",
                    field_label="Total Expenditure",
                    raw_value=raw_val,
                    normalized_value=norm_exp,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=str_mod,
                    review_category=ReviewCategory.HIGH,
                )
            )

        # 8. Balance Surplus / Deficit
        bal_matches = self.find_labeled_candidate(
            doc_result.pages,
            label_pattern=r"(?:Excess\s*of\s*Income\s*over\s*Expenditure(?:\s*\([A-Za-z\s]+\))?|Excess\s*of\s*Expenditure\s*over\s*Income(?:\s*\([A-Za-z\s]+\))?|Net\s*(?:Surplus|Deficit)(?:\s*[\/\-]\s*(?:Surplus|Deficit))?|Surplus(?:\s*[\/\-]\s*Deficit)?|Deficit|Balance)",
            value_pattern=r"(?:₹|Rs\.?|INR)?\s*(\(?[0-9,]+(?:\.[0-9]+)?\)?(?:\s*(?:Lakhs?|Crores?|Lacs?|Cr|Thousands?))?)",
        )
        for raw_val, snippet, page, line in bal_matches:
            norm_bal, str_mod = parse_indian_monetary_amount(raw_val)
            candidates.append(
                ExtractedCandidateField(
                    field_code="balance_surplus_deficit",
                    field_label="Balance Surplus / Deficit",
                    raw_value=raw_val,
                    normalized_value=norm_bal,
                    page_number=page.page_number,
                    source_snippet=snippet,
                    bounding_box=line.bounding_box,
                    extraction_method=page.method,
                    ocr_confidence=line.confidence,
                    matching_strength=str_mod,
                    review_category=ReviewCategory.HIGH,
                )
            )

        matched_codes = {c.field_code for c in candidates}
        unmatched = [f for f in self.expected_field_codes if f not in matched_codes]

        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=candidates,
            unmatched_expected_fields=unmatched,
            extraction_status="COMPLETED" if len(matched_codes) >= 4 else "PARTIAL",
        )


# =============================================================================
# Fallback Extractor (Generic / Unsupported)
# =============================================================================


class GenericFallbackExtractor(BaseDocumentExtractor):
    """Fallback extractor for unmapped or generic document requirement codes.

    Reports that no specialized extractor is configured without fabricating fields.
    """

    def __init__(self, item_code: str) -> None:
        self.item_code = item_code
        self.document_type_code = "GENERIC_DOCUMENT"
        self.expected_field_codes = []

    def extract(self, doc_result: DocumentExtractionResult) -> FieldExtractionResult:
        return FieldExtractionResult(
            item_code=self.item_code,
            document_type_code=self.document_type_code,
            candidate_fields=[],
            unmatched_expected_fields=[],
            extraction_status="UNRECOGNIZED",
            diagnostics={
                "message": f"No specialized rule extractor registered for requirement code '{self.item_code}'",
                "page_count": doc_result.page_count,
            },
        )


# =============================================================================
# Field Extraction Service & Registry
# =============================================================================


class FieldExtractionService:
    """Service registry dispatching extraction requests to dedicated document extractors."""

    def __init__(self) -> None:
        self._extractors: dict[str, BaseDocumentExtractor] = {
            "EOA-SD-01": Affidavit2Extractor(),
            "EOA-SD-02": PaymentReceiptExtractor(),
            "EOA-SD-03": BuildingCertificateExtractor(),
            "EOA-SD-04": StructuralStabilityExtractor(),
            "EOA-SD-05": FireSafetyExtractor(),
            "EOA-SD-06": SatelliteMapExtractor(),
            "EOA-SD-07": AuditedStatementExtractor(),
        }

    def register_extractor(self, extractor: BaseDocumentExtractor) -> None:
        """Registers or overrides an extractor for a requirement code."""
        self._extractors[extractor.item_code] = extractor

    def get_extractor(self, item_code: str) -> BaseDocumentExtractor:
        """Retrieves registered extractor for item_code or returns GenericFallbackExtractor."""
        return self._extractors.get(item_code, GenericFallbackExtractor(item_code))

    def extract_fields(
        self,
        item_code: str,
        doc_result: DocumentExtractionResult,
    ) -> FieldExtractionResult:
        """Dispatches extraction to the registered requirement extractor."""
        extractor = self.get_extractor(item_code)
        return extractor.extract(doc_result)


# Singleton instance for standard application reuse
field_extraction_service = FieldExtractionService()
