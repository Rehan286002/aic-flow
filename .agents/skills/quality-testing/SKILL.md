
---
name: quality-testing
description: Defines AIC-Flow quality assurance, automated testing, backend and frontend validation, security testing, database integrity, OCR evaluation, regulatory rule tests, historical replay, performance benchmarking and final prototype acceptance. Use when implementing, testing, debugging or reviewing project functionality.
---

# AIC-Flow Quality Testing and Acceptance

## 1. Objective

Ensure that AIC-Flow is a genuinely working, integrated and testable approval-workflow platform.

The objective is not merely to make the application compile or display attractive screens.

Every implemented feature must:
- Perform its advertised operation.
- Persist the correct data.
- Respect user permissions.
- Handle errors safely.
- Maintain database integrity.
- Produce reproducible outputs where required.
- Integrate correctly with dependent modules.

Never report an unimplemented or untested capability as completed.

## 2. Testing Technology

Use:

Backend:
- pytest
- HTTPX
- FastAPI test utilities
- SQLAlchemy testing sessions

Frontend:
- Vitest
- React Testing Library
- Playwright

Database:
- PostgreSQL test database.
- Controlled fixtures.
- Migration verification.

Document processing:
- Synthetic PDF/JPEG/PNG fixtures.
- Known expected extraction results.
- OCR confidence and page-location verification.

Keep compatible versions locked in project dependencies.

## 3. Testing Architecture

Maintain separate test levels.

### Unit tests

Test individual functions and services.

Examples:
- Date normalization.
- SHA-256 calculation.
- Document MIME detection.
- Rule evaluation.
- Name normalization.
- Source status mapping.
- Merkle hash calculation.

These tests should be fast and independent.

### Integration tests

Test multiple modules working together.

Examples:
- API to database.
- Document upload to storage.
- OCR worker to extracted-field persistence.
- Source connector to reconciliation.
- Validation to findings.
- Rectification to new application revision.

### End-to-end tests

Test complete workflows through the actual application interface.

Examples:
- Institution login.
- Application creation.
- Document upload.
- Validation.
- Auditor review.
- Rectification.
- Re-validation.
- Lead recommendation.

### Security tests

Verify access boundaries and negative cases.

A successful response for an authorised user is not sufficient. Unauthorised operations must also be tested.

## 4. Test Data Discipline

Use synthetic/generated data exclusively.

Maintain controlled fixtures in:

fixtures/
    documents/
    source_records/
    seed_data/

Test data must include:
- Known expected values.
- Known document types.
- Known source statuses.
- Known rule outcomes.
- Known historical versions.

Keep expected test results separate from the application implementation wherever practical.

Never rely on random generated values for tests requiring deterministic outcomes.

Make fixtures reproducible.

Do not send real personal, faculty, institutional or certificate information to external testing services.

## 5. Project Quality Gates

Every development phase must have a defined acceptance gate.

### Foundation gate

- Environment dependencies are available.
- Required containers start.
- Database connection works.
- Redis connection works.
- Backend health endpoint responds.
- Frontend starts successfully.

### Authentication gate

- Four roles can be resolved correctly.
- Login succeeds for valid provisioned test accounts.
- Invalid credentials are rejected.
- Disabled accounts cannot authenticate.
- Role-specific navigation works.
- Backend permissions are enforced.

### Application gate

- Synthetic institution exists.
- EoA application can be created.
- Academic year is correct.
- Category and checklist are correct.
- Drafts can be saved.
- Application revision relationships are valid.

### Document gate

- Accepted document formats upload correctly.
- Invalid documents are rejected or quarantined.
- SHA-256 is correct.
- Original files remain unchanged.
- New uploads create new versions.
- Processing status is persisted.

### OCR gate

- Searchable PDF extraction works.
- Scanned PDF OCR works.
- Required structured fields are persisted.
- Page numbers are correct.
- Bounding boxes are available where supported.
- Confidence is recorded.
- Failed or uncertain extraction is reported honestly.

### Validation gate

- All seven specified rule identifiers are supported.
- Conditional applicability works.
- Status meanings are preserved.
- Findings have relevant evidence relationships.
- Repeated validations use explicit inputs.
- Historical rules remain identifiable.

### Auditor gate

- Assigned cases are accessible.
- Unassigned cases are denied.
- Findings can be reviewed.
- Reviewer actions retain their history.
- Relevant evidence can be opened.

### Rectification gate

- Only permitted items can be corrected.
- A new application revision is created.
- Old revisions remain unchanged.
- Replacement documents create new versions.
- Re-validation produces a distinct validation run.

### Lead Auditor gate

- Escalations are accessible within scope.
- Previous reviewer actions are preserved.
- Recommendation rationale is required.
- Proceed, Hold and Inspection Required are supported.
- The workflow does not issue a final statutory decision.

### Replay and audit gate

- Historical validation inputs are pinned.
- An earlier run can be reproduced.
- Source updates do not rewrite historical results.
- ICPL chain hashes can be recomputed.
- Merkle inclusion verification works.
- Tampered events fail the appropriate verification test.

## 6. Authentication and Authorisation Tests

Test every PS 26262 permission package and verify its mapped frontend workspace: Institution Representative, Intake / Registry Officer, Scrutiny / Processing Officer, Regional Officer / Coordinator, EVC Coordinator, EVC Assigned Participant, Committee Secretariat, Bureau Supervisor, Competent Authority, Regulatory Policy Publisher and Platform Administrator. Legacy role codes must not expand permissions.

### Institution User

Test:
- Access to own institution.
- Access to own applications.
- Access to permitted documents.
- Access to applicant-visible rectification.
- Denial of another institution's records.
- Denial of internal findings.
- Denial of reviewer-only operations.

### Auditor

Test:
- Access to assigned cases.
- Denial of unassigned cases.
- Permitted evidence viewing.
- Permitted finding actions.
- Access to relevant review history.
- Denial of unrestricted case access.

### Lead Auditor

Test:
- Access to permitted escalated cases.
- Review of previous auditor actions.
- Permitted recommendation operations.
- Restricted access outside assigned scope.

### Admin

Test:
- User management.
- Role configuration.
- Review team management.
- System health and operational logs.
- Rule and connector configuration.
- Denial of application documents, internal findings and case recommendations.

### PostgreSQL RLS

Do not treat frontend hiding as a security test.

Test actual database queries through the restricted application database role.

Verify:
- Correct authenticated database context.
- Institution isolation.
- Auditor assignment isolation.
- Lead review scope.
- Admin case-content denial.
- No accidental user-context leakage across pooled connections.
- Correct service-only table restrictions.

Use negative tests for every sensitive access boundary.

## 7. Document Processing Tests

Maintain representative synthetic samples.

Test:
- Valid searchable PDF.
- Valid scanned PDF.
- English document.
- Tamil document.
- JPEG.
- PNG.
- Empty file.
- Unsupported file extension.
- MIME/signature mismatch.
- Oversized file.
- Malformed PDF.
- Password-protected PDF.
- Excessive page count.
- Corrupted image.
- Low-quality scan.
- Duplicate bytes.
- Resized/compressed image duplicate candidate.

Verify:
- Quarantine behaviour.
- File validation.
- Malware scan outcome.
- SHA-256.
- Version creation.
- Extracted text.
- Bounding boxes.
- OCR confidence.
- Processing status.
- Error handling.

A scanner unavailable or failed must not be treated as a clean result.

## 8. Regulatory Rule Tests

Test the seven specified identifiers:

- EOA-SD-01.
- EOA-SD-02.
- EOA-SD-03.
- EOA-SD-04.
- EOA-SD-05.
- EOA-SD-06.
- EOA-SD-07.

Include:
- Valid evidence.
- Missing evidence.
- Conditional non-applicability.
- Incomplete evidence.
- Ambiguous values.
- Source mismatch.
- Expired evidence where the applicable validity is established.
- Source unavailable.
- Manual review requirements.

Specific structural stability test:

- Completion age 29 years: Not Applicable.
- Completion age 31 years: Required.
- Missing completion date: Unable to Determine.

Specific Fire Safety test:

- Use explicit issuer-specific validity configuration.
- Do not assume a universal certificate expiry period.
- Test expired, valid, unknown and unavailable outcomes separately.

Verify every output against an independently maintained expected test result.

## 9. Source Reconciliation Tests

Test source outcomes:

- VERIFIED.
- MISMATCH.
- EXPIRED.
- PENDING.
- SOURCE_UNAVAILABLE.

Verify:
- Correct environment label.
- Source identifier.
- Source version.
- Response timestamp.
- Correlation ID.
- Response digest.
- Matched fields.
- Mismatched fields.
- Freshness status.

Never convert a timeout or unavailable source into a verified result.

Test stale and current records separately.

Similarity scores must not be treated as identity probabilities.

## 10. Evidence Contradiction Explorer Tests

Verify that actual stored evidence relationships appear in the interface.

For each material finding, confirm that available evidence references correctly link to:
- Application revision.
- Document.
- Document version.
- PDF page.
- Extracted field.
- Source record.
- Validation result.
- Regulatory rule version.
- Finding.

Test:
- Clicking each graph node.
- Opening linked document pages.
- Displaying extracted values.
- Displaying source values.
- Displaying the applicable rule.
- Navigating back to the related finding.

No decorative graph connections or hardcoded relationships are acceptable.

## 11. Rectification and Historical Version Tests

Run this complete scenario:

1. Submit an application revision.
2. Run validation.
3. Generate findings.
4. Request rectification.
5. Log in as Institution User.
6. Submit the permitted response.
7. Upload replacement evidence.
8. Create a new revision.
9. Run validation again.
10. Review both validation runs.

Expected:
- Original application revision remains unchanged.
- Original document remains unchanged.
- New document version exists.
- New application revision exists.
- Review history is preserved.
- Second validation uses the new revision.

## 12. Temporal Compliance Replay Tests

Run a deterministic replay test.

1. Seed synthetic source snapshot A.
2. Run validation.
3. Record its application revision, source version and rule versions.
4. Update the current synthetic source record to B.
5. Replay the original validation.
6. Compare its result with the original run.
7. Execute a fresh validation.
8. Compare the new result.

Expected:
- Historical replay uses A.
- New validation uses B.
- Historical rules remain pinned.
- Earlier validation results are not silently rewritten.

## 13. ICPL and Merkle Tests

Test:
- Event canonicalisation.
- Event ordering.
- Previous-event hash relationship.
- Event hash computation.
- Leaf hash construction.
- Internal Merkle node construction.
- Inclusion proof creation.
- Inclusion proof verification.

Negative tests:
- Alter event content.
- Alter previous hash.
- Change event order.
- Alter a sibling hash.
- Use an incorrect batch root.

Expected:
The appropriate integrity checks must fail when the event or proof is modified.

Do not claim an independently distributed blockchain network exists unless one is actually implemented.

## 14. API Tests

Use HTTPX and FastAPI testing facilities.

Test:
- Successful requests.
- Invalid input.
- Missing fields.
- Invalid identifiers.
- Duplicate operations.
- Authentication failures.
- Permission failures.
- Not-found responses.
- Database transaction failures.
- Worker errors.
- Connector timeouts.

Verify correct response codes and structured error formats.

Do not leak database internals, private document contents, passwords or connector credentials.

## 15. Frontend Tests

Use Vitest and React Testing Library for components and interactions.

Use Playwright for browser-based workflows.

Test:
- Login.
- Role-specific navigation.
- Form validation.
- Application creation.
- Checklist display.
- Document upload.
- Processing status updates.
- PDF preview.
- Finding details.
- Evidence graph interactions.
- Reviewer actions.
- Rectification.
- Report downloads.
- Error and empty states.
- Responsive layout.

Check that every visible interactive button has a meaningful action.

Test loading, success, empty, error and permission-denied states.

## 16. Performance Testing

Measure rather than assume.

Record:
- Hardware configuration.
- RAM availability.
- CPU configuration.
- File type.
- File size.
- PDF page count.
- OCR engine/version.
- Worker concurrency.
- Processing time.
- P50 response time.
- P95 response time.

Relevant specification targets include:

- Application/checklist API: P95 approximately 150–200 ms.
- Upload acknowledgement: P95 approximately 300 ms, excluding transfer.
- Small-file SHA-256: under 100 ms target on declared hardware.
- Issuer adapter demo timeout: approximately 3–5 seconds.
- Dashboard refresh: approximately 10–20 seconds or suitable push updates.
- Retrieval-only AIC Assist: P95 under 3 seconds target on the local corpus.

Treat these as engineering targets, not proven performance claims.

Do not claim them achieved without actual measurements.

On the 16 GB RAM development machine, use bounded OCR concurrency and avoid unnecessary simultaneous model execution.

## 17. Regression Testing

Whenever an existing feature changes:

- Run its relevant unit tests.
- Run dependent service tests.
- Run related API tests.
- Check frontend integration.
- Run security tests when permissions or data access are affected.

Do not break an already working workflow while implementing another module.

Use reproducible test cases to investigate regressions.

## 18. Test Reporting

Maintain a clear record of:

- Test identifier.
- Feature.
- Test environment.
- Input fixture.
- Expected result.
- Actual result.
- Pass/fail.
- Failure explanation.
- Date/time.
- Relevant implementation version.

Distinguish:

- Not implemented.
- Implemented but not tested.
- Tested and passed.
- Tested and failed.
- Blocked by an unavailable dependency.

Do not report blocked or skipped tests as passed.

## 19. Final Prototype Acceptance

The prototype must demonstrate one complete synthetic application workflow.

The final acceptance review should establish:

1. Application creation and checklist.
2. Secure multi-document upload.
3. OCR and structured extraction.
4. Seven evidence rules.
5. Synthetic source reconciliation.
6. Evidence-linked findings.
7. Evidence Contradiction Explorer.
8. Auditor review.
9. Rectification and new revision.
10. Re-validation.
11. Lead recommendation.
12. Temporal replay.
13. ICPL/Merkle proof.
14. Role isolation.
15. Report export.
16. AIC Assist Lite with citations.

Every displayed result must originate from the actual running implementation or be explicitly labelled as a fixture/conceptual element.

The final statutory approval boundary must remain clear.

## 20. Development Discipline

Before declaring any module complete:

1. Identify its acceptance criteria.
2. Implement its functionality.
3. Write relevant tests.
4. Execute the tests.
5. Investigate and resolve failures.
6. Verify dependent modules.
7. Record actual implementation status.

Never hide test failures to make a milestone appear complete.

Do not replace genuine functionality with frontend mock data.

Do not silently skip difficult acceptance requirements.

Prioritise a reliable end-to-end workflow over a large quantity of incomplete features.
