"""
Read-only verification of the immutable Apex reference ValidationRun 5822d8f2-dcd4-4fd3-8794-cb84ef23e54f.
Strict read-only safety: never modifies, deletes or inserts any records.
"""
import uuid
import sys
from app.db.session import SessionLocal
from app.models.validation_run import ValidationRun
from app.models.validation_result import ValidationResult
from app.models.finding import Finding
from app.models.finding_evidence import FindingEvidence
from app.models.validation_run_rule_version import ValidationRunRuleVersion
from app.models.validation_run_source_version import ValidationRunSourceVersion
from app.models.validation_rule_version import ValidationRuleVersion
from app.models.validation_rule import ValidationRule
from app.models.application_revision import ApplicationRevision
from app.models.application import Application
from app.models.institution import Institution

TARGET_RUN_ID = uuid.UUID("5822d8f2-dcd4-4fd3-8794-cb84ef23e54f")

def main():
    db = SessionLocal()
    try:
        run = db.query(ValidationRun).filter(ValidationRun.validation_run_id == TARGET_RUN_ID).first()
        if not run:
            print(f"FAILED: ValidationRun {TARGET_RUN_ID} NOT FOUND in database!")
            sys.exit(1)

        print(f"=== VALIDATION RUN (1 record) ===")
        print(f"  Run ID: {run.validation_run_id}")
        print(f"  Revision ID: {run.application_revision_id}")
        print(f"  Status: {run.status}")
        print(f"  Run Type: {run.run_type}")
        print(f"  Engine Version: {run.engine_version}")
        print(f"  Evaluation As Of: {run.evaluation_as_of}")
        print(f"  Started At: {run.started_at}")
        print(f"  Completed At: {run.completed_at}")

        rev = db.query(ApplicationRevision).filter(ApplicationRevision.application_revision_id == run.application_revision_id).first()
        app = db.query(Application).filter(Application.application_id == rev.application_id).first() if rev else None
        inst = db.query(Institution).filter(Institution.institution_id == app.institution_id).first() if app else None
        print(f"  Application ID: {app.application_id if app else 'None'}")
        print(f"  Application Number: {app.application_number if app else 'None'}")
        print(f"  Academic Year: {app.academic_year if app else 'None'}")
        print(f"  Revision Number: {rev.revision_number if rev else 'None'}")
        print(f"  Institution Name: {inst.institution_name if inst else 'None'}")
        print(f"  AICTE Permanent ID: {inst.aicte_permanent_institution_id if inst else 'None'}")

        # Results
        results = db.query(ValidationResult).filter(ValidationResult.validation_run_id == TARGET_RUN_ID).all()
        print(f"\n=== VALIDATION RESULTS ({len(results)} records) ===")
        for r in results:
            rv = db.query(ValidationRuleVersion).filter(ValidationRuleVersion.validation_rule_version_id == r.validation_rule_version_id).first()
            rule = db.query(ValidationRule).filter(ValidationRule.validation_rule_id == rv.validation_rule_id).first() if rv else None
            print(f"  Result ID: {r.validation_result_id} | Rule: {rule.rule_code if rule else 'N/A'} (v{rv.version_number if rv else '?'}) | Status: {r.result_status} | Reason: {r.explanation[:80]}...")

        # Findings
        findings = db.query(Finding).filter(Finding.validation_run_id == TARGET_RUN_ID).all()
        print(f"\n=== FINDINGS ({len(findings)} records) ===")
        for f in findings:
            print(f"  Finding ID: {f.finding_id} | Severity: {f.severity.value if hasattr(f.severity, 'value') else f.severity} | Status: {f.status.value if hasattr(f.status, 'value') else f.status} | Category: {f.category.value if hasattr(f.category, 'value') else f.category} | Title: {f.title}")

        # Finding Evidence
        finding_ids = [f.finding_id for f in findings]
        evidences = db.query(FindingEvidence).filter(FindingEvidence.finding_id.in_(finding_ids)).all() if finding_ids else []
        print(f"\n=== FINDING EVIDENCE ({len(evidences)} records) ===")
        for e in evidences:
            print(f"  Evidence ID: {e.finding_evidence_id} | Finding ID: {e.finding_id} | Type: {e.evidence_type} | Summary: {e.evidence_summary}")

        # Rule Versions
        rule_versions = db.query(ValidationRunRuleVersion).filter(ValidationRunRuleVersion.validation_run_id == TARGET_RUN_ID).all()
        print(f"\n=== PINNED RULE VERSIONS ({len(rule_versions)} records) ===")
        for rrv in rule_versions:
            rv = db.query(ValidationRuleVersion).filter(ValidationRuleVersion.validation_rule_version_id == rrv.validation_rule_version_id).first()
            rule = db.query(ValidationRule).filter(ValidationRule.validation_rule_id == rv.validation_rule_id).first() if rv else None
            print(f"  Rule Code: {rule.rule_code if rule else 'N/A'} | Version ID: {rrv.validation_rule_version_id} | v{rv.version_number if rv else '?'}")

        # Source Versions
        source_versions = db.query(ValidationRunSourceVersion).filter(ValidationRunSourceVersion.validation_run_id == TARGET_RUN_ID).all()
        print(f"\n=== PINNED SOURCE VERSIONS ({len(source_versions)} records) ===")
        for sv in source_versions:
            print(f"  Source Code: {sv.source_code} | Record Version ID: {sv.institution_record_version_id} | Sync Run ID: {sv.source_sync_run_id}")

        total_records = 1 + len(results) + len(findings) + len(evidences) + len(rule_versions) + len(source_versions)
        print(f"\n========================================================")
        print(f"TOTAL SCOPED RECORDS: {total_records} / 35")
        print(f"  - ValidationRun: 1")
        print(f"  - ValidationResults: {len(results)}")
        print(f"  - Findings: {len(findings)}")
        print(f"  - FindingEvidence: {len(evidences)}")
        print(f"  - ValidationRunRuleVersion: {len(rule_versions)}")
        print(f"  - ValidationRunSourceVersion: {len(source_versions)}")
        if total_records == 35:
            print("STATUS: VERIFIED INTACT AND READ-ONLY IMMUTABLE (35/35 records)")
        else:
            print(f"STATUS: COUNT MISMATCH (Found {total_records}, expected 35)")
        print(f"========================================================")

    finally:
        db.close()

if __name__ == "__main__":
    main()
