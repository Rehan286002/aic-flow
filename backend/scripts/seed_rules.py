"""AIC-Verify — Regulatory Rules & Versions Seeding Script.

Idempotently seeds the master catalog of 7 validation rules for AICTE APH 2024-2027
Annexure 2.1 requirements (EOA-SD-01 through EOA-SD-07), creates Version 1 for each
rule, and links each rule to its corresponding ChecklistItem.
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.checklist_item import ChecklistItem
from app.models.checklist_item_rule import ChecklistItemRule
from app.models.enums import ApplicationFamily
from app.models.validation_rule import ValidationRule
from app.models.validation_rule_version import ValidationRuleVersion

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RULES_DATA = [
    {
        "rule_code": "RULE_EOA_01_AFFIDAVIT",
        "rule_name": "Annexure 2.1 Item 1: Affidavit 2 Compliance",
        "rule_category": "LEGAL_AFFIDAVIT",
        "description": (
            "Validates notarized affidavit affirming compliance with AICTE norms, governance, "
            "fee structure, and faculty requirements on ₹100 e-stamp paper with authorized deponent."
        ),
        "checklist_item_code": "EOA-SD-01",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item i",
        "condition_json": {
            "required_stamp_duty_inr": 100.0,
            "self_financing_deponent_titles": ["CHAIRMAN", "SECRETARY"],
            "government_deponent_titles": [
                "PRINCIPAL",
                "DIRECTOR",
                "AUTHORISED PERSON",
                "AUTHORISED SIGNATORY",
                "AUTHORIZED OFFICER",
            ],
            "require_notary_registration": True,
            "require_oath_affirmation": True,
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_AICTE_PORTAL"],
            "item_code": "EOA-SD-01",
        },
    },
    {
        "rule_code": "RULE_EOA_02_PAYMENT",
        "rule_name": "Annexure 2.1 Item 2: AICTE Web-Portal Payment Receipt",
        "rule_category": "FINANCIAL_FEE",
        "description": (
            "Validates AICTE web-portal payment receipt copy if applicable, or verifies legal fee "
            "exemption against AICTE master institutional portal."
        ),
        "checklist_item_code": "EOA-SD-02",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item ii",
        "condition_json": {
            "valid_payment_statuses": ["SUCCESS", "PAID"],
            "allow_exemption": True,
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_AICTE_PORTAL"],
            "item_code": "EOA-SD-02",
        },
    },
    {
        "rule_code": "RULE_EOA_03_BUILDING",
        "rule_name": "Annexure 2.1 Item 3: Valid Building / Occupancy Document",
        "rule_category": "INFRASTRUCTURE_LAND",
        "description": (
            "Validates that uploaded building document is an approved statutory certificate type "
            "(Occupancy, Completion, Building License, or Form D) issued by a competent authority."
        ),
        "checklist_item_code": "EOA-SD-03",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item iii",
        "condition_json": {
            "allowed_certificate_types": [
                "OCCUPANCY_CERTIFICATE",
                "COMPLETION_CERTIFICATE",
                "BUILDING_LICENSE",
                "FORM_D",
            ],
            "require_competent_authority": True,
            "cross_check_municipal_record": True,
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_MUNICIPAL_BLDG"],
            "item_code": "EOA-SD-03",
        },
    },
    {
        "rule_code": "RULE_EOA_04_STRUCTURAL",
        "rule_name": "Annexure 2.1 Item 4: Valid Structural Stability Certificate (>30 Years)",
        "rule_category": "SAFETY_STRUCTURAL",
        "description": (
            "Evaluates strict >30-year building age trigger based on Completion Certificate issue date "
            "and verifies 5-year validity of structural stability certificate from a structural engineer."
        ),
        "checklist_item_code": "EOA-SD-04",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item iv",
        "condition_json": {
            "age_threshold_years": 30,
            "statutory_validity_years": 5,
            "assessment_reference_date": "2026-07-01",
            "require_soundness_affirmation": True,
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_MUNICIPAL_BLDG"],
            "item_code": "EOA-SD-04",
        },
    },
    {
        "rule_code": "RULE_EOA_05_FIRE_NOC",
        "rule_name": "Annexure 2.1 Item 5: Valid Fire Safety Certificate",
        "rule_category": "SAFETY_FIRE",
        "description": (
            "Validates that the fire safety certificate/NOC is unexpired and confirmed active "
            "against state fire and emergency services directorate records."
        ),
        "checklist_item_code": "EOA-SD-05",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item v",
        "condition_json": {
            "require_unexpired": True,
            "cross_check_fire_services": True,
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_FIRE_SERVICES"],
            "item_code": "EOA-SD-05",
        },
    },
    {
        "rule_code": "RULE_EOA_06_GEO_COORDS",
        "rule_name": "Annexure 2.1 Item 6: Satellite Map and Entrance Coordinates",
        "rule_category": "GEOSPATIAL_LOCATION",
        "description": (
            "Validates entrance GPS coordinates on satellite map using Indian landmass plausibility "
            "checks and advisory geospatial proximity to registered campus location."
        ),
        "checklist_item_code": "EOA-SD-06",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item vi",
        "condition_json": {
            "coarse_bounds": {
                "min_latitude": 6.0,
                "max_latitude": 38.0,
                "min_longitude": 68.0,
                "max_longitude": 98.0,
            },
            "distance_bands_km": {
                "entrance_tolerance": 1.0,
                "advisory_distance": 5.0,
            },
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_BHUVAN_GEOMAP"],
            "item_code": "EOA-SD-06",
        },
    },
    {
        "rule_code": "RULE_EOA_07_AUDITED_STMT",
        "rule_name": "Annexure 2.1 Item 7: Previous-Year Audited Statement of Accounts",
        "rule_category": "FINANCIAL_AUDIT",
        "description": (
            "Validates previous-year audited balance sheet and statements of accounts of the Trust/Society, "
            "cross-checking CA UDIN against synthetic ICAI records and verifying internal arithmetic."
        ),
        "checklist_item_code": "EOA-SD-07",
        "regulatory_reference": "AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item vii",
        "condition_json": {
            "required_term": "PREVIOUS_YEAR",
            "cross_check_udin": True,
            "figure_matching_tolerance_pct": 1.0,
            "arithmetic_reconciliation_tolerance_pct": 2.0,
        },
        "evaluation_config": {
            "dependent_sources": ["SRC_ICAI_UDIN", "SRC_AICTE_PORTAL"],
            "item_code": "EOA-SD-07",
        },
    },
]


def seed_rules() -> dict[str, int]:
    """Seed validation rules, version 1, and checklist item associations.

    Returns summary counts.
    """
    db = SessionLocal()
    counts = {
        "rules_inserted": 0,
        "rules_updated": 0,
        "versions_inserted": 0,
        "versions_updated": 0,
        "links_created": 0,
    }

    try:
        for rdata in RULES_DATA:
            rule = db.scalar(
                select(ValidationRule).where(
                    ValidationRule.rule_code == rdata["rule_code"]
                )
            )
            if not rule:
                rule = ValidationRule(
                    rule_code=rdata["rule_code"],
                    rule_name=rdata["rule_name"],
                    description=rdata["description"],
                    rule_category=rdata["rule_category"],
                    is_active=True,
                )
                db.add(rule)
                db.flush()
                counts["rules_inserted"] += 1
                logger.info("Inserted rule: %s", rule.rule_code)
            else:
                rule.rule_name = rdata["rule_name"]
                rule.description = rdata["description"]
                rule.rule_category = rdata["rule_category"]
                rule.is_active = True
                counts["rules_updated"] += 1

            # Seed Version 1
            rule_version = db.scalar(
                select(ValidationRuleVersion).where(
                    ValidationRuleVersion.validation_rule_id == rule.validation_rule_id,
                    ValidationRuleVersion.version_number == 1,
                )
            )
            if not rule_version:
                rule_version = ValidationRuleVersion(
                    validation_rule_id=rule.validation_rule_id,
                    version_number=1,
                    application_family=ApplicationFamily.EXISTING_INSTITUTION,
                    academic_year_from="2024-25",
                    academic_year_to="2026-27",
                    effective_from=date(2024, 4, 1),
                    effective_to=None,
                    condition_json=rdata["condition_json"],
                    evaluation_config=rdata["evaluation_config"],
                    regulatory_reference=rdata["regulatory_reference"],
                    is_enabled=True,
                )
                db.add(rule_version)
                counts["versions_inserted"] += 1
                logger.info("Inserted rule version 1 for: %s", rule.rule_code)
            else:
                rule_version.condition_json = rdata["condition_json"]
                rule_version.evaluation_config = rdata["evaluation_config"]
                rule_version.regulatory_reference = rdata["regulatory_reference"]
                rule_version.is_enabled = True
                counts["versions_updated"] += 1

            # Link to ChecklistItem
            ci = db.scalar(
                select(ChecklistItem).where(
                    ChecklistItem.item_code == rdata["checklist_item_code"]
                )
            )
            if ci:
                link = db.scalar(
                    select(ChecklistItemRule).where(
                        ChecklistItemRule.checklist_item_id == ci.checklist_item_id,
                        ChecklistItemRule.validation_rule_id == rule.validation_rule_id,
                    )
                )
                if not link:
                    link = ChecklistItemRule(
                        checklist_item_id=ci.checklist_item_id,
                        validation_rule_id=rule.validation_rule_id,
                    )
                    db.add(link)
                    counts["links_created"] += 1
                    logger.info(
                        "Linked %s -> %s",
                        rdata["checklist_item_code"],
                        rule.rule_code,
                    )

        db.commit()
        logger.info("Successfully seeded validation rules: %s", counts)
        return counts
    except Exception as e:
        db.rollback()
        logger.error("Failed to seed validation rules: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_rules()
