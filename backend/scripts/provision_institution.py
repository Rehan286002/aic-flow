"""Provision an institution from an authorised institution registry record.

This operator-only utility does not discover, verify, or invent AICTE identifiers.
The operator must supply the institution's official permanent ID and registry data.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.institution import Institution

PRODUCTION_CONFIRMATION = "CREATE-INSTITUTION-FROM-AUTHORISED-REGISTRY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an institution record from an authorised AICTE registry entry.")
    parser.add_argument("--permanent-id", required=True, help="Official AICTE Permanent Institution ID")
    parser.add_argument("--name", required=True, help="Official institution name")
    parser.add_argument("--type", dest="institution_type", help="Institution type as recorded by the authorised source")
    parser.add_argument("--address", help="Official institutional address")
    parser.add_argument("--district", help="Official district")
    parser.add_argument("--state", help="Official state")
    parser.add_argument("--postal-code", help="Official postal code")
    parser.add_argument("--confirm-production", action="store_true", help="Allow record creation in production")
    return parser.parse_args()


def validate_environment(*, app_env: str, confirm_production: bool) -> None:
    environment = app_env.strip().lower()
    if environment in {"local", "development", "test"}:
        return
    if environment != "production" or not confirm_production:
        raise SystemExit("Refusing institution provisioning outside local/test or without --confirm-production.")
    print("Only use data copied from an authorised, current institution registry record.")
    phrase = getpass.getpass("Type the exact confirmation phrase (input hidden): ")
    if phrase != PRODUCTION_CONFIRMATION:
        raise SystemExit("Production confirmation did not match; no institution was created.")


def main() -> int:
    args = parse_args()
    validate_environment(app_env=settings.app_env, confirm_production=args.confirm_production)
    permanent_id = args.permanent_id.strip()
    name = args.name.strip()
    if not permanent_id or len(permanent_id) > 80 or not name or len(name) > 300:
        print("ERROR: Permanent ID and official institution name are required and must fit their registry fields.")
        return 2

    db = SessionLocal()
    try:
        existing = db.scalar(select(Institution).where(Institution.aicte_permanent_institution_id == permanent_id))
        if existing:
            print("ERROR: This Permanent Institution ID already exists. Existing records are never overwritten or reactivated.")
            return 3
        institution = Institution(
            aicte_permanent_institution_id=permanent_id,
            institution_name=name,
            institution_type=args.institution_type.strip() if args.institution_type else None,
            address_line=args.address.strip() if args.address else None,
            district=args.district.strip() if args.district else None,
            state=args.state.strip() if args.state else None,
            postal_code=args.postal_code.strip() if args.postal_code else None,
            is_active=True,
        )
        db.add(institution)
        db.commit()
        db.refresh(institution)
        print("Institution record created from operator-supplied registry data.")
        print(f"Institution ID: {institution.institution_id}")
        print(f"Permanent Institution ID: {institution.aicte_permanent_institution_id}")
        print("Next: provision its authorised INSTITUTION_USER account with provision_account.py.")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERROR: Institution creation failed; transaction rolled back: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
