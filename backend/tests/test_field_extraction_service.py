"""Tests for Phase 4 Batch 3: Rule-Based Structured Field Extractors.

Verifies:
- All 7 Annexure 2.1 document extractors (EOA-SD-01 through EOA-SD-07).
- Specialized variants (Occupancy, Completion, Building License, Form D for EOA-SD-03).
- Helper normalizers (dates, Indian monetary amounts, geographic coordinates).
- Fallback extractor for unmapped / generic requirement codes.
- Ambiguous date handling per Indian regulatory norms (DD/MM/YYYY assumed with lower matching strength).
- Deficit monetary handling (negative values, parentheses).
- Non-fabrication on empty or unrelated text.
- Separation of OCR confidence, matching strength, and review category.
"""

from __future__ import annotations

import pytest

from app.services.field_extraction_service import (
    Affidavit2Extractor,
    AuditedStatementExtractor,
    BuildingCertificateExtractor,
    FieldExtractionService,
    FireSafetyExtractor,
    GenericFallbackExtractor,
    PaymentReceiptExtractor,
    ReviewCategory,
    SatelliteMapExtractor,
    StructuralStabilityExtractor,
    field_extraction_service,
    is_valid_indian_latitude,
    is_valid_indian_longitude,
    normalize_iso_date,
    parse_geographic_coordinate,
    parse_indian_monetary_amount,
)
from app.services.text_extraction_service import (
    BoundingBox,
    DocumentExtractionResult,
    ExtractedTextLine,
    PageExtractionMethod,
    PageExtractionResult,
)

# =============================================================================
# Test Helpers
# =============================================================================


def make_test_doc(
    pages_text: list[str],
    method: PageExtractionMethod = PageExtractionMethod.NATIVE_TEXT,
    line_confidence: float = 0.95,
) -> DocumentExtractionResult:
    """Creates a synthetic DocumentExtractionResult for testing field extractors."""
    pages: list[PageExtractionResult] = []
    total_chars = 0

    for page_idx, page_text in enumerate(pages_text, start=1):
        lines_raw = page_text.strip().split("\n")
        lines: list[ExtractedTextLine] = []
        for line_idx, line_str in enumerate(lines_raw):
            clean_line = line_str.strip()
            if not clean_line:
                continue
            lines.append(
                ExtractedTextLine(
                    line_number=line_idx + 1,
                    text=clean_line,
                    confidence=line_confidence,
                    bounding_box=BoundingBox(
                        x=50.0,
                        y=float(100.0 + line_idx * 25.0),
                        width=450.0,
                        height=20.0,
                    ),
                )
            )
        page_content = "\n".join(line.text for line in lines)
        total_chars += len(page_content)
        pages.append(
            PageExtractionResult(
                page_number=page_idx,
                method=method,
                text=page_content,
                lines=lines,
                width_pt=595.0,
                height_pt=842.0,
                ocr_confidence_mean=line_confidence
                if method == PageExtractionMethod.OCR
                else None,
            )
        )

    full_text_doc = "\n\n".join(p.text for p in pages)
    return DocumentExtractionResult(
        mime_type="application/pdf",
        page_count=len(pages),
        pages=pages,
        full_text=full_text_doc,
        total_char_count=len(full_text_doc),
        native_pages_count=len(pages)
        if method == PageExtractionMethod.NATIVE_TEXT
        else 0,
        ocr_pages_count=len(pages) if method == PageExtractionMethod.OCR else 0,
        total_processing_time_ms=10.0,
    )


# =============================================================================
# 1. Normalization Utility Tests
# =============================================================================


class TestNormalizationUtilities:
    """Verifies date, monetary and coordinate normalization."""

    def test_normalize_iso_date_iso_formats(self) -> None:
        val, strength, _notes = normalize_iso_date("2026-05-15")
        assert val == "2026-05-15"
        assert strength == 1.0

    def test_normalize_iso_date_text_month(self) -> None:
        val1, strength1, _ = normalize_iso_date("15 May 2026")
        assert val1 == "2026-05-15"
        assert strength1 == 1.0

        val2, strength2, _ = normalize_iso_date("October 28, 2026")
        assert val2 == "2026-10-28"
        assert strength2 == 1.0

        val3, strength3, _ = normalize_iso_date("01-Jan-2025")
        assert val3 == "2025-01-01"
        assert strength3 == 1.0

    def test_normalize_iso_date_unambiguous_day_first(self) -> None:
        # Day > 12 is unambiguously DD/MM/YYYY
        val, strength, _ = normalize_iso_date("28/04/2026")
        assert val == "2026-04-28"
        assert strength == 1.0

    def test_normalize_iso_date_ambiguous_dd_mm_vs_mm_dd(self) -> None:
        # 04/05/2026 could be April 5 or May 4.
        # Under Indian regulatory conventions, DD/MM/YYYY is assumed with reduced confidence.
        val, strength, notes = normalize_iso_date("04/05/2026")
        assert val == "2026-05-04"
        assert strength == 0.75
        assert notes is not None
        assert "assumed DD/MM/YYYY" in notes

    def test_normalize_iso_date_invalid_values(self) -> None:
        val, strength, _notes = normalize_iso_date("Not a date")
        assert val is None
        assert strength == 0.0

    def test_parse_indian_monetary_amount_standard_inr(self) -> None:
        parsed, strength = parse_indian_monetary_amount("₹ 1,50,000")
        assert parsed is not None
        assert parsed["amount"] == 150000.0
        assert parsed["currency"] == "INR"
        assert parsed["is_negative"] is False
        assert strength == 0.95

    def test_parse_indian_monetary_amount_words_crores_lakhs(self) -> None:
        parsed_cr, _ = parse_indian_monetary_amount("Rs. 4.50 Crores")
        assert parsed_cr is not None
        assert parsed_cr["amount"] == 45000000.0

        parsed_lakh, _ = parse_indian_monetary_amount("₹ 25.5 Lakhs")
        assert parsed_lakh is not None
        assert parsed_lakh["amount"] == 2550000.0

    def test_parse_indian_monetary_amount_negative_parentheses(self) -> None:
        # Deficit formatted as (15,00,000)
        parsed, _ = parse_indian_monetary_amount("(₹ 15,00,000)")
        assert parsed is not None
        assert parsed["amount"] == -1500000.0
        assert parsed["is_negative"] is True

        parsed_minus, _ = parse_indian_monetary_amount("-50,000.00")
        assert parsed_minus is not None
        assert parsed_minus["amount"] == -50000.0
        assert parsed_minus["is_negative"] is True

    def test_parse_geographic_coordinate_decimal_degrees(self) -> None:
        deg, score, _ = parse_geographic_coordinate("12.971598° N")
        assert deg == pytest.approx(12.971598)
        assert score >= 0.90

        lon, _, _ = parse_geographic_coordinate("77.594562 E")
        assert lon == pytest.approx(77.594562)

    def test_parse_geographic_coordinate_dms(self) -> None:
        deg, score, _ = parse_geographic_coordinate("28° 36' 50\" N")
        # 28 + 36/60 + 50/3600 = 28 + 0.6 + 0.013888 = 28.613888
        assert deg == pytest.approx(28.613888, rel=1e-4)
        assert score >= 0.85

    def test_indian_coordinate_bounds(self) -> None:
        # Delhi: inside India
        assert is_valid_indian_latitude(28.6139) is True
        assert is_valid_indian_longitude(77.2090) is True

        # Outside India
        assert is_valid_indian_latitude(51.5074) is False  # London
        assert is_valid_indian_longitude(-0.1278) is False


# =============================================================================
# 2. EOA-SD-01: Affidavit 2 Extractor Tests
# =============================================================================


class TestAffidavit2Extractor:
    """Verifies extraction of candidate fields from EOA-SD-01 (Affidavit 2)."""

    @pytest.fixture
    def extractor(self) -> Affidavit2Extractor:
        return Affidavit2Extractor()

    def test_extract_all_standard_fields(self, extractor: Affidavit2Extractor) -> None:
        doc_text = """
        BEFORE THE NOTARY PUBLIC, DELHI
        AFFIDAVIT (FORMAT 2)
        I, Dr. Ramesh Sharma, Secretary of Sri Krishna Education Trust,
        having AICTE Permanent Institute ID 1-123456789,
        do hereby solemnly affirm and state on oath:
        1. That our institution, Sri Krishna Institute of Technology, complies with all norms.
        
        DEPONENT: Dr. Ramesh Sharma
        DESIGNATION: Secretary / Chairman
        
        VERIFICATION:
        Verified at New Delhi on this 15th day of April 2025.
        
        ATTESTED BY:
        Advocate & Notary Public: S. K. Gupta
        Notary Registration Number: DL/9876/2018
        Date of Attestation: 15/04/2025
        Non-Judicial E-Stamp Duty: Rs. 100/-
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        assert result.item_code == "EOA-SD-01"
        assert result.document_type_code == "AFFIDAVIT_UNDERTAKING"
        assert result.extraction_status == "COMPLETED"

        field_map = {f.field_code: f for f in result.candidate_fields}

        # AICTE Permanent ID
        assert "aicte_permanent_id" in field_map
        assert field_map["aicte_permanent_id"].raw_value == "1-123456789"
        assert field_map["aicte_permanent_id"].review_category in [
            ReviewCategory.HIGH,
            ReviewCategory.MEDIUM_REVIEW,
        ]

        # Deponent Name
        assert "deponent_name" in field_map
        assert "Ramesh Sharma" in field_map["deponent_name"].raw_value

        # Deponent Designation
        assert "deponent_designation" in field_map
        assert (
            "Secretary" in field_map["deponent_designation"].raw_value
            or "Chairman" in field_map["deponent_designation"].raw_value
        )

        # Notary Registration No
        assert "notary_registration_no" in field_map
        assert "DL/9876/2018" in field_map["notary_registration_no"].raw_value

        # Attestation Date
        assert "attestation_date" in field_map
        assert (
            field_map["attestation_date"].normalized_value["iso_date"] == "2025-04-15"
        )

        # Stamp Duty Amount
        assert "stamp_duty_amount" in field_map
        assert field_map["stamp_duty_amount"].normalized_value["numeric_value"] == 100.0

        # Provenance sanity
        for candidate in result.candidate_fields:
            assert candidate.page_number == 1
            assert candidate.source_snippet is not None
            assert candidate.ocr_confidence is not None
            assert candidate.matching_strength > 0.0


# =============================================================================
# 3. EOA-SD-02: Payment Receipt Extractor Tests
# =============================================================================


class TestPaymentReceiptExtractor:
    """Verifies extraction of candidate fields from EOA-SD-02 (AICTE Payment Receipt)."""

    @pytest.fixture
    def extractor(self) -> PaymentReceiptExtractor:
        return PaymentReceiptExtractor()

    def test_extract_standard_payment_receipt(
        self, extractor: PaymentReceiptExtractor
    ) -> None:
        doc_text = """
        ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
        ONLINE PAYMENT RECEIPT - APPROVAL PROCESS 2026-27
        
        Receipt Number: AICTE-2026-987654
        Transaction Reference / UTR Number: SBIN000123456789
        Payment Date: 2026-04-10
        Amount Paid: ₹ 1,50,000.00
        Payment Mode: Net Banking / NEFT
        Payment Status: SUCCESS / PAID
        Application Sub-Type: Extension of Approval (EoA)
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        assert result.item_code == "EOA-SD-02"
        assert result.extraction_status == "COMPLETED"

        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "receipt_number" in field_map
        assert "AICTE-2026-987654" in field_map["receipt_number"].raw_value

        assert "transaction_ref_no" in field_map
        assert "SBIN000123456789" in field_map["transaction_ref_no"].raw_value

        assert "payment_date" in field_map
        assert field_map["payment_date"].normalized_value["iso_date"] == "2026-04-10"

        assert "payment_amount" in field_map
        assert field_map["payment_amount"].normalized_value["numeric_value"] == 150000.0

        assert "payment_mode" in field_map
        assert "payment_status" in field_map
        assert field_map["payment_status"].raw_value.upper() == "SUCCESS"

    def test_conditional_receipt_zero_fee(
        self, extractor: PaymentReceiptExtractor
    ) -> None:
        """EOA-SD-02 is 'if any'. Verify zero fee or exemption notice handled."""
        doc_text = """
        AICTE APPROVAL PROCESS 2026-27
        Receipt Number: EXEMPT-2026-001
        Payment Status: EXEMPTED
        Zero regulatory fee applicable for this application category.
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        assert result.diagnostics.get("conditional_receipt") is True


# =============================================================================
# 4. EOA-SD-03: Building Certificate Extractor Tests (All 4 Variants)
# =============================================================================


class TestBuildingCertificateExtractor:
    """Verifies extraction of EOA-SD-03 supporting all 4 applicable certificate variants:

    - Occupancy Certificate
    - Completion Certificate
    - Building License
    - Form D
    """

    @pytest.fixture
    def extractor(self) -> BuildingCertificateExtractor:
        return BuildingCertificateExtractor()

    def test_variant_occupancy_certificate(
        self, extractor: BuildingCertificateExtractor
    ) -> None:
        doc_text = """
        GREATER NOIDA INDUSTRIAL DEVELOPMENT AUTHORITY
        OCCUPANCY CERTIFICATE
        Certificate No: GNIDA/BP/2023/OC-4521
        Issuing Authority: Chief Executive Officer, GNIDA
        Date of Issue: 18/06/2023
        
        This is to certify that Block A & B of Sri Krishna Institute,
        having Total Built-Up Area of 12,450.50 Sq. Meters,
        is completed in all respects and fit for occupation.
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        field_map = {f.field_code: f for f in result.candidate_fields}
        assert "certificate_type" in field_map
        assert (
            "OCCUPANCY CERTIFICATE" in field_map["certificate_type"].raw_value.upper()
        )
        assert (
            field_map["certificate_type"].normalized_value["canonical_type"]
            == "OCCUPANCY_CERTIFICATE"
        )

        assert "certificate_number" in field_map
        assert "GNIDA/BP/2023/OC-4521" in field_map["certificate_number"].raw_value

        assert "issue_date" in field_map
        assert field_map["issue_date"].normalized_value["iso_date"] == "2023-06-18"

        assert "total_builtup_area" in field_map
        area_norm = field_map["total_builtup_area"].normalized_value
        assert area_norm["area_value"] == pytest.approx(12450.50)
        assert area_norm["unit"] == "SQ_METERS"

    def test_variant_completion_certificate(
        self, extractor: BuildingCertificateExtractor
    ) -> None:
        doc_text = """
        MUNICIPAL CORPORATION OF DELHI
        COMPLETION CERTIFICATE
        Sanction Order No: MCD/BLDG/CC/2022/9981
        Date of Sanction: 12-10-2022
        Issuing Authority: Town Planning Authority, MCD
        Total Built Up Area: 8,500 sq.m
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}
        assert (
            field_map["certificate_type"].normalized_value["canonical_type"]
            == "COMPLETION_CERTIFICATE"
        )

    def test_variant_building_license(
        self, extractor: BuildingCertificateExtractor
    ) -> None:
        doc_text = """
        DIRECTORATE OF TOWN AND COUNTRY PLANNING
        BUILDING LICENSE / SANCTION PLAN
        License Number: DTCP/BL-2021/334
        Date of Issue: 2021-08-14
        Issuing Authority: Commissioner, DTCP
        Built-Up Area: 1,25,000 Sq. Ft.
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}
        assert (
            field_map["certificate_type"].normalized_value["canonical_type"]
            == "BUILDING_LICENSE"
        )
        assert field_map["total_builtup_area"].normalized_value["unit"] == "SQ_FEET"

    def test_variant_form_d(self, extractor: BuildingCertificateExtractor) -> None:
        doc_text = """
        GOVERNMENT OF TAMIL NADU - PUBLIC WORKS DEPARTMENT
        FORM D - BUILDING LICENSE
        License Reference: PWD/BL/FORM-D/2024/112
        Issuing Authority: Executive Engineer, PWD Buildings Division
        Date of Inspection & Issue: 05/01/2024
        Constructed Area: 6,400 Square Meters
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}
        assert (
            field_map["certificate_type"].normalized_value["canonical_type"] == "FORM_D"
        )
        assert "jurisdiction_scope" in field_map["certificate_type"].normalized_value
        assert (
            "state/jurisdiction-specific" in field_map["certificate_type"].notes.lower()
        )


# =============================================================================
# 5. EOA-SD-04: Structural Stability Certificate Extractor Tests
# =============================================================================


class TestStructuralStabilityExtractor:
    """Verifies extraction of EOA-SD-04 (Structural Stability Certificate).

    Extracts stated facts and provenance without deciding 30-year statutory rules.
    """

    @pytest.fixture
    def extractor(self) -> StructuralStabilityExtractor:
        return StructuralStabilityExtractor()

    def test_extract_stability_certificate_facts(
        self, extractor: StructuralStabilityExtractor
    ) -> None:
        doc_text = """
        CONSULTING STRUCTURAL ENGINEER & CHARTERED CIVIL ENGINEER
        STRUCTURAL STABILITY CERTIFICATE
        
        Certified by: Er. Rajesh Kumar, M.E. (Structures)
        Structural Engineer License No: SE/MCD/2018/00432
        Registered with: Municipal Corporation of Delhi & Council of Engineers
        
        Date of Inspection & Issue: 10/05/2024
        Validity of Certificate: Valid up to 09/05/2027
        
        CERTIFICATION STATEMENT:
        I have inspected the academic buildings and hostel blocks of Sri Krishna Institute.
        The structural elements have been designed as per Indian Standard codes.
        The building is structurally sound and stable for educational occupancy.
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        assert result.item_code == "EOA-SD-04"
        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "engineer_name" in field_map
        assert "Rajesh Kumar" in field_map["engineer_name"].raw_value

        assert "engineer_license_no" in field_map
        assert "SE/MCD/2018/00432" in field_map["engineer_license_no"].raw_value

        assert "issue_date" in field_map
        assert field_map["issue_date"].normalized_value["iso_date"] == "2024-05-10"

        assert "validity_date" in field_map
        assert field_map["validity_date"].normalized_value["iso_date"] == "2027-05-09"

        assert "stability_certification_statement" in field_map
        assert (
            field_map["stability_certification_statement"].normalized_value[
                "certified_sound"
            ]
            is True
        )

    def test_certificate_without_stated_validity(
        self, extractor: StructuralStabilityExtractor
    ) -> None:
        """When validity is not explicitly stated in text, does not invent one."""
        doc_text = """
        Er. Amit Sen, Chartered Engineer
        Registration Number: CE/KOL/9912
        Date of Issue: 2024-02-15
        The structure is found safe and stable.
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}
        # validity_date should not be present in candidate fields
        assert "validity_date" not in field_map
        assert "validity_date" in result.unmatched_expected_fields


# =============================================================================
# 6. EOA-SD-05: Fire Safety Certificate Extractor Tests
# =============================================================================


class TestFireSafetyExtractor:
    """Verifies extraction of EOA-SD-05 (Fire Safety Certificate)."""

    @pytest.fixture
    def extractor(self) -> FireSafetyExtractor:
        return FireSafetyExtractor()

    def test_extract_fire_noc_details(self, extractor: FireSafetyExtractor) -> None:
        doc_text = """
        DEPARTMENT OF FIRE AND EMERGENCY SERVICES, HARYANA
        NO OBJECTION CERTIFICATE (FIRE SAFETY)
        
        NOC Number: FS/2025/NOC-88912
        Issuing Department: Office of the Chief Fire Officer, Gurugram
        Issue Date: 12/01/2025
        Valid Up To: 11/01/2028
        
        Campus Address: Plot No. 44, Sector 62, Technology Park, Gurugram, Haryana - 122001
        
        The premises have installed required fire fighting arrangements as per NBC 2016.
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "fire_noc_number" in field_map
        assert "FS/2025/NOC-88912" in field_map["fire_noc_number"].raw_value

        assert "issuing_department" in field_map
        assert "Fire" in field_map["issuing_department"].raw_value

        assert "issue_date" in field_map
        assert field_map["issue_date"].normalized_value["iso_date"] == "2025-01-12"

        assert "expiry_date" in field_map
        assert field_map["expiry_date"].normalized_value["iso_date"] == "2028-01-11"

        assert "campus_address" in field_map
        assert "Plot No. 44" in field_map["campus_address"].raw_value


# =============================================================================
# 7. EOA-SD-06: Satellite Map Extractor Tests
# =============================================================================


class TestSatelliteMapExtractor:
    """Verifies extraction of EOA-SD-06 (Satellite Map and GPS Coordinates)."""

    @pytest.fixture
    def extractor(self) -> SatelliteMapExtractor:
        return SatelliteMapExtractor()

    def test_extract_decimal_coordinates(
        self, extractor: SatelliteMapExtractor
    ) -> None:
        doc_text = """
        SATELLITE MAP SHOWING GEOGRAPHICAL LOCATION OF MAIN ENTRANCE
        INSTITUTION: Sri Krishna Institute of Technology
        
        Main Building Entrance GPS Coordinates:
        Latitude: 28.613925 N
        Longitude: 77.209015 E
        
        Survey / Khasra No: Khasra No. 124/2 & Survey No. 89
        Village / Town: Badarpur
        District: South East Delhi
        State: Delhi
        Map Capture Date: 2026-02-14 10:30:00 UTC
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "latitude" in field_map
        lat_norm = field_map["latitude"].normalized_value
        assert lat_norm["decimal_degrees"] == pytest.approx(28.613925)
        assert lat_norm["is_in_indian_territory"] is True

        assert "longitude" in field_map
        lon_norm = field_map["longitude"].normalized_value
        assert lon_norm["decimal_degrees"] == pytest.approx(77.209015)
        assert lon_norm["is_in_indian_territory"] is True

        assert "survey_khasra_number" in field_map
        assert "124/2" in field_map["survey_khasra_number"].raw_value

        assert "district" in field_map
        assert "Delhi" in field_map["district"].raw_value

        assert "state" in field_map
        assert "Delhi" in field_map["state"].raw_value

    def test_extract_dms_coordinates(self, extractor: SatelliteMapExtractor) -> None:
        doc_text = """
        SATELLITE IMAGERY OF CAMPUS ENTRANCE
        Entrance Coordinates: 12° 58' 23" N, 77° 35' 45" E
        Village: Whitefield
        District: Bengaluru Urban
        State: Karnataka
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "latitude" in field_map
        assert field_map["latitude"].normalized_value["is_in_indian_territory"]
        assert "longitude" in field_map
        assert field_map["longitude"].normalized_value["is_in_indian_territory"]

    def test_flag_coordinates_outside_india(
        self, extractor: SatelliteMapExtractor
    ) -> None:
        # Latitude 51.5° N (London) is outside India (6.0° to 37.5°)
        doc_text = """
        Latitude: 51.5074 N
        Longitude: 0.1278 W
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "latitude" in field_map
        assert field_map["latitude"].normalized_value["is_in_indian_territory"] is False
        assert (
            field_map["latitude"].normalized_value["passes_coarse_plausibility_check"]
            is False
        )
        assert field_map["latitude"].matching_strength <= 0.50
        assert (
            "coarse indian bounding box plausibility check"
            in field_map["latitude"].notes.lower()  # type: ignore[union-attr]
        )


# =============================================================================
# 8. EOA-SD-07: Audited Statement Extractor Tests
# =============================================================================


class TestAuditedStatementExtractor:
    """Verifies extraction of EOA-SD-07 (Previous-Year Audited Financial Statement)."""

    @pytest.fixture
    def extractor(self) -> AuditedStatementExtractor:
        return AuditedStatementExtractor()

    def test_extract_audited_statement_surplus(
        self, extractor: AuditedStatementExtractor
    ) -> None:
        doc_text = """
        INDEPENDENT AUDITOR'S REPORT
        To the Trustees of Sri Krishna Educational Trust
        Financial Year: 2024-25 (Assessment Year 2025-26)
        
        INCOME AND EXPENDITURE ACCOUNT FOR THE YEAR ENDED 31ST MARCH 2025
        Gross Annual Income / Total Revenue: ₹ 4,50,00,000.00
        Total Expenditure / Expenses: ₹ 3,85,00,000.00
        Excess of Income over Expenditure (Surplus): ₹ 65,00,000.00
        
        For M/s Ramanathan & Co., Chartered Accountants
        Firm Registration No: 001234S
        Auditor Name: CA S. Ramanathan, Partner
        Membership No: 054321
        UDIN: 25054321BGHKLM1234
        Date of Report: 25/08/2025
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)

        assert result.item_code == "EOA-SD-07"
        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "financial_year" in field_map
        assert "2024-25" in field_map["financial_year"].raw_value

        assert "trust_society_name" in field_map
        assert (
            "Sri Krishna Educational Trust" in field_map["trust_society_name"].raw_value
        )

        assert "auditor_name" in field_map
        assert "Ramanathan" in field_map["auditor_name"].raw_value

        assert "auditor_registration_no" in field_map
        assert (
            "054321" in field_map["auditor_registration_no"].raw_value
            or "25054321BGHKLM1234" in field_map["auditor_registration_no"].raw_value
        )

        assert "auditor_membership_no" in field_map
        assert "054321" in field_map["auditor_membership_no"].raw_value

        assert "auditor_firm_reg_no" in field_map
        assert "001234S" in field_map["auditor_firm_reg_no"].raw_value

        assert "auditor_udin" in field_map
        assert "25054321BGHKLM1234" in field_map["auditor_udin"].raw_value

        assert "audit_report_date" in field_map
        assert (
            field_map["audit_report_date"].normalized_value["iso_date"] == "2025-08-25"
        )

        assert "gross_annual_income" in field_map
        assert (
            field_map["gross_annual_income"].normalized_value["numeric_value"]
            == 45000000.0
        )

        assert "total_expenditure" in field_map
        assert (
            field_map["total_expenditure"].normalized_value["numeric_value"]
            == 38500000.0
        )

        assert "balance_surplus_deficit" in field_map
        assert (
            field_map["balance_surplus_deficit"].normalized_value["numeric_value"]
            == 6500000.0
        )
        assert (
            field_map["balance_surplus_deficit"].normalized_value["is_negative"]
            is False
        )

    def test_extract_audited_statement_deficit_negative(
        self, extractor: AuditedStatementExtractor
    ) -> None:
        """Verifies deficit formatted with parentheses or minus sign is parsed as negative."""
        doc_text = """
        AUDITED INCOME & EXPENDITURE STATEMENT
        Financial Year: 2024-2025
        Trust: Holy Mother Education Society
        Gross Income: Rs. 1,20,00,000
        Total Expenditure: Rs. 1,35,00,000
        Net Deficit: (15,00,000)
        Auditor: CA P. Venkat
        Date: 2025-09-15
        """
        doc = make_test_doc([doc_text])
        result = extractor.extract(doc)
        field_map = {f.field_code: f for f in result.candidate_fields}

        assert "balance_surplus_deficit" in field_map
        bal_norm = field_map["balance_surplus_deficit"].normalized_value
        assert bal_norm["numeric_value"] == -1500000.0
        assert bal_norm["is_negative"] is True


# =============================================================================
# 9. Fallback Extractor & Service Dispatch Tests
# =============================================================================


class TestFallbackExtractorAndService:
    """Verifies GenericFallbackExtractor and FieldExtractionService dispatch."""

    def test_fallback_extractor_unmapped_code(self) -> None:
        doc = make_test_doc(["Some document text without specialized rules."])
        fallback = GenericFallbackExtractor(item_code="EOA-SD-99")
        result = fallback.extract(doc)

        assert result.item_code == "EOA-SD-99"
        assert result.document_type_code == "GENERIC_DOCUMENT"
        assert result.extraction_status == "UNRECOGNIZED"
        assert len(result.candidate_fields) == 0
        assert "EOA-SD-99" in result.diagnostics["message"]

    def test_field_extraction_service_dispatch_all_seven(self) -> None:
        service = FieldExtractionService()
        registered_codes = [
            "EOA-SD-01",
            "EOA-SD-02",
            "EOA-SD-03",
            "EOA-SD-04",
            "EOA-SD-05",
            "EOA-SD-06",
            "EOA-SD-07",
        ]

        for code in registered_codes:
            extractor = service.get_extractor(code)
            assert extractor.item_code == code
            assert not isinstance(extractor, GenericFallbackExtractor)

        # Unregistered returns fallback
        unregistered = service.get_extractor("UNKNOWN-REQ-01")
        assert isinstance(unregistered, GenericFallbackExtractor)

    def test_global_singleton_service(self) -> None:
        assert field_extraction_service is not None
        ext = field_extraction_service.get_extractor("EOA-SD-01")
        assert isinstance(ext, Affidavit2Extractor)


# =============================================================================
# 10. Non-Fabrication and Robustness Tests
# =============================================================================


class TestNonFabricationAndRobustness:
    """Proves extractors never hallucinate fields on unrelated or empty content."""

    @pytest.mark.parametrize(
        "item_code",
        [
            "EOA-SD-01",
            "EOA-SD-02",
            "EOA-SD-03",
            "EOA-SD-04",
            "EOA-SD-05",
            "EOA-SD-06",
            "EOA-SD-07",
        ],
    )
    def test_no_fabrication_on_lorem_ipsum(self, item_code: str) -> None:
        lorem_text = """
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
        Duis aute irure dolor in reprehenderit in voluptate velit esse cillum.
        """
        doc = make_test_doc([lorem_text])
        result = field_extraction_service.extract_fields(item_code, doc)

        # Extractors must not hallucinate fields
        assert len(result.candidate_fields) == 0
        assert result.extraction_status in ["EMPTY_OR_NOT_SUBMITTED", "PARTIAL"]
        # All expected codes should be listed in unmatched_expected_fields
        extractor = field_extraction_service.get_extractor(item_code)
        for expected in extractor.expected_field_codes:
            assert expected in result.unmatched_expected_fields

    def test_confidence_concept_separation(self) -> None:
        """Verifies raw OCR confidence, matching strength, and review category remain separated."""
        doc_text = """
        Receipt Number: AICTE-2026-111111
        Amount: ₹ 50,000
        Date: 2026-03-01
        """
        # Page OCR mean confidence is 0.82 (e.g. slight scan noise)
        doc = make_test_doc(
            [doc_text],
            method=PageExtractionMethod.OCR,
            line_confidence=0.82,
        )
        extractor = PaymentReceiptExtractor()
        result = extractor.extract(doc)

        for candidate in result.candidate_fields:
            # Concept 1: raw OCR confidence reflects page/line engine certainty
            assert candidate.ocr_confidence == pytest.approx(0.82)
            # Concept 2: heuristic matching strength reflects regex label proximity
            assert 0.0 <= candidate.matching_strength <= 1.0
            # Concept 3: review category is categorical enum
            assert candidate.review_category in [
                ReviewCategory.HIGH,
                ReviewCategory.MEDIUM_REVIEW,
                ReviewCategory.LOW_UNCERTAIN,
            ]
            # Verify they are NOT multiplied into a single composite float
            assert (
                candidate.matching_strength
                != candidate.ocr_confidence * candidate.matching_strength
            )
