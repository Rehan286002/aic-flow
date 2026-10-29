"""AIC-Verify — Seed Synthetic Verification Sources and Baseline Institutional Records.

Development-only seeding utility for:
- 6 Synthetic Verification Sources (SRC_AICTE_PORTAL, SRC_REVENUE_LAND,
  SRC_MUNICIPAL_BLDG, SRC_FIRE_SERVICES, SRC_ICAI_UDIN, SRC_BHUVAN_GEOMAP).
- Initial versioned institutional master record snapshots for Apex Institute of Technology
  (SYNTH-AICTE-0001).
- Audit trail in source_sync_runs with SIMULATED provenance.

Strictly prohibited from running in production environments.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.institution import Institution
from app.services.source_connector_service import source_connector_service

ALLOWED_ENVIRONMENTS = {"local", "development", "test"}

DEMO_PERMANENT_ID = "SYNTH-AICTE-0001"
DEFAULT_SOURCE_CODES = [
    "SRC_AICTE_PORTAL",
    "SRC_REVENUE_LAND",
    "SRC_MUNICIPAL_BLDG",
    "SRC_FIRE_SERVICES",
    "SRC_ICAI_UDIN",
    "SRC_BHUVAN_GEOMAP",
]


def seed_sources() -> dict[str, Any]:
    """Execute idempotent seeding of verification sources and institutional snapshots."""
    if settings.app_env not in ALLOWED_ENVIRONMENTS:
        print(f"ERROR: Cannot run seed_sources in '{settings.app_env}' environment.")
        sys.exit(1)

    print("=" * 70)
    print("AIC-Verify — Seeding Synthetic Verification Sources & Snapshots")
    print(f"Environment: {settings.app_env} (Provenance: SIMULATED)")
    print("=" * 70)

    db = SessionLocal()
    try:
        # 1. Seed or update VerificationSource definitions
        print("1. Synchronizing Verification Sources...")
        source_counts = source_connector_service.seed_or_update_verification_sources(db)
        print(
            f"   Sources: {source_counts['inserted']} inserted, "
            f"{source_counts['updated']} updated, "
            f"{source_counts['unchanged']} unchanged."
        )

        # 2. Look up synthetic demo institution
        print("2. Locating synthetic demonstration institution...")
        inst = db.scalar(
            select(Institution).where(
                Institution.aicte_permanent_institution_id == DEMO_PERMANENT_ID
            )
        )
        if not inst:
            print(
                f"   WARNING: Demo institution {DEMO_PERMANENT_ID} not found. Skipping snapshot seeding."
            )
            return {"source_counts": source_counts, "snapshot_counts": {}}

        print(f"   Found: {inst.institution_name} ({inst.institution_id})")

        # 3. Synchronize initial baseline snapshots
        print("3. Synchronizing initial institutional record snapshots...")
        snapshot_counts = {"inserted": 0, "unchanged": 0}

        for source_code in DEFAULT_SOURCE_CODES:
            # Check existing snapshot version count before sync
            prev_snapshots = source_connector_service.get_institution_snapshot_history(
                db, inst.institution_id, source_system=source_code
            )
            count_before = len(prev_snapshots)

            _sync_run, version = source_connector_service.sync_institution_source(
                db=db,
                institution_id=inst.institution_id,
                source_code=source_code,
                sync_kind="FULL",
            )

            # Check snapshot version count after sync
            count_after = len(
                source_connector_service.get_institution_snapshot_history(
                    db, inst.institution_id, source_system=source_code
                )
            )

            if count_after > count_before:
                snapshot_counts["inserted"] += 1
                status_str = f"NEW (v{version.record_version})"
            else:
                snapshot_counts["unchanged"] += 1
                ver_num = version.record_version if version else "N/A"
                status_str = f"UNCHANGED (v{ver_num})"

            print(
                f"   - {source_code:<20} : {status_str} (SHA: {version.source_payload_sha256[:12] if version else 'N/A'})"
            )

        print("=" * 70)
        print("Summary:")
        print(
            f"  - Verification Sources: {source_counts['inserted']} added, {source_counts['unchanged']} retained"
        )
        print(
            f"  - Institutional Snapshots: {snapshot_counts['inserted']} created, {snapshot_counts['unchanged']} retained"
        )
        print("  - Provenance: ALL RECORDS EXPLICITLY TAGGED 'SIMULATED'")
        print("=" * 70)

        return {"source_counts": source_counts, "snapshot_counts": snapshot_counts}

    except SQLAlchemyError as e:
        db.rollback()
        print(f"ERROR during source seeding: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_sources()
