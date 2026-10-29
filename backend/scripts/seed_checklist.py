"""Seed the baseline category checklist and shared reference catalogue.

The seed is idempotent. It does not create an institution, user, application,
source record, or approval decision. Production publication is deliberately
interactive because the applicable APH amendments must be reviewed first.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.checklist_service import seed_standard_references

PRODUCTION_CONFIRMATION = "PUBLISH-EOA-APH-2024-2027-BASELINE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed AIC-Flow's baseline EoA checklist and standard references.")
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Allow the idempotent baseline checklist seed in production after regulatory review.",
    )
    return parser.parse_args()


def validate_environment(*, app_env: str, confirm_production: bool) -> None:
    environment = app_env.strip().lower()
    if environment in {"local", "development", "test"}:
        return
    if environment != "production" or not confirm_production:
        raise SystemExit(
            f"Refusing to seed checklist data in APP_ENV={environment!r}. "
            "Production requires --confirm-production and the exact confirmation phrase."
        )
    print(
        "WARNING: Review the applicable AICTE Approval Process Handbook and all effective amendments "
        "for the target academic year before publishing this baseline checklist."
    )
    phrase = getpass.getpass("Type the exact confirmation phrase (input hidden): ")
    if phrase != PRODUCTION_CONFIRMATION:
        raise SystemExit("Production confirmation did not match; no data was changed.")


def run_seed() -> None:
    args = parse_args()
    validate_environment(app_env=settings.app_env, confirm_production=args.confirm_production)

    print("AIC-Flow — seeding baseline EoA checklist and standard references")
    print(f"Environment: {settings.app_env}")
    db = SessionLocal()
    try:
        counts = seed_standard_references(db)
        print("Seeding completed successfully:")
        print(f"  Document types created: {counts['document_types']}")
        print(f"  Field definitions created: {counts['field_definitions']}")
        print(f"  Checklist templates created: {counts['checklist_templates']}")
        print(f"  Checklist items created: {counts['checklist_items']}")
        print("No application, account, institution, source record, or decision was created.")
    except (SQLAlchemyError, RuntimeError) as exc:
        db.rollback()
        print(f"ERROR during seeding: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
