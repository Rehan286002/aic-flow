
---
name: backend-engineering
description: Defines AIC-Flow backend architecture, FastAPI development, SQLAlchemy database access, Alembic migrations, API contracts, authentication, role-based security, source connectors, business services and background processing. Use when implementing or reviewing backend functionality.
---

# AIC-Flow Backend Engineering

## 1. Backend Objective

Build a modular, secure and maintainable backend for the AIC-Flow approval-workflow platform. Preserve document validation as a supporting evidence subsystem.

The backend must support a complete application lifecycle:

Application
-> Checklist
-> Document Upload
-> Document Processing
-> Extraction
-> Source Reconciliation
-> Regulatory Validation
-> Findings
-> Human Review
-> Rectification
-> Re-validation
-> Lead Recommendation
-> Audit Proof

All important operations must use persistent database records.

Do not build a collection of independent mock APIs.

## 2. Mandatory Technology Stack

Use:

- Python 3.13
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL 18
- psycopg
- Redis 7.2.x
- Celery
- pytest
- HTTPX

Use compatible stable package versions and pin them in the project dependency lockfile.

Do not replace the prescribed backend architecture without an explicit technical reason.

## 3. Architecture: Modular Monolith

Use one FastAPI application with logically separated API routers, services, models and integrations.

Responsibilities:

### API Layer
- Receive HTTP requests.
- Authenticate users.
- Check access permissions.
- Validate request data.
- Call application services.
- Return structured responses.

### Service Layer
- Implement actual business rules.
- Coordinate database operations.
- Manage transactions.
- Call supporting modules.
- Avoid HTTP-specific responsibilities.

### Database Layer
- Manage SQLAlchemy sessions.
- Define persistence models.
- Manage transactions.
- Support scoped queries and Row-Level Security.

### Connector Layer
- Implement synthetic institution and issuer adapters.
- Return structured source responses.
- Record source environment and provenance.

### Worker Layer
- Execute background document processing.
- Process OCR jobs.
- Execute source synchronisation jobs where appropriate.
- Handle retry and failure states.

### Assistant Layer
- Retrieve approved handbook content.
- Produce cited responses.
- Enforce role and case access scope.

Do not introduce microservices unnecessarily.

## 4. Code Organisation

Keep responsibilities within the established repository:

backend/
    app/
        main.py
        api/
            routes/
            dependencies.py
        core/
            config.py
            security.py
            exceptions.py
        db/
            session.py
            base.py
        models/
        schemas/
        services/
        connectors/
        workers/
        assistant/
    tests/
    alembic/

Additional internal files and module-specific directories may be introduced when justified.

Do not put the entire application in main.py.

Do not create circular imports.

## 5. API Design

Use versioned API paths:

/api/v1/

Organise endpoints by domain:

- auth
- users
- institutions
- applications
- checklists
- documents
- extraction
- verification
- validation
- findings
- reviews
- rectification
- replay
- recommendations
- notifications
- reports
- assistant
- admin

Follow REST conventions.

Use:
- GET for retrieval.
- POST for creation or operations.
- PATCH for permitted partial modifications.
- PUT only where full replacement is appropriate.
- DELETE only where deletion is explicitly permitted.

Use appropriate HTTP response codes.

Validate requests with Pydantic.

Keep API request and response schemas separate from SQLAlchemy database models.

Do not expose internal database objects directly to frontend clients.

Provide consistent error responses and meaningful validation messages.

Keep automatically generated OpenAPI documentation enabled during development.

## 6. Database Engineering

PostgreSQL 18 is the primary persistent database.

Use SQLAlchemy 2 for database interactions.

Use Alembic for controlled database migrations.

The supplied schema references are:

- schema/reference/AICTE_Regulatory_Platform_Schema_v4.sql
- schema/reference/AICTE_Regulatory_Platform_Schema_v3_to_v4.sql

Important rules:

- V4 is the fresh-install schema reference.
- V3-to-v4 is an upgrade migration only.
- Never apply the v3-to-v4 migration to an empty database.
- Preserve supplied reference files unchanged.
- Analyse existing tables before creating replacements.
- Implement only the necessary MVP subset.
- Preserve required primary keys, foreign keys and relationships.
- Use appropriate indexes and uniqueness constraints.
- Avoid duplicate representations of the same information.

Do not automatically convert all 80 tables into ORM models.

Begin with the entities necessary for the first complete workflow.

Before producing migrations:

1. Identify required entities.
2. Map them to v4 table definitions.
3. Identify foreign-key dependencies.
4. Identify necessary constraints and indexes.
5. Review the resulting migration.
6. Test fresh database installation.
7. Verify upgrade and rollback expectations.

Never modify an already-applied migration silently.

## 7. Data Modelling Principles

Preserve the distinction between:

- Institution master records.
- Application records.
- Immutable application revisions.
- Application requirements.
- Documents.
- Immutable document versions.
- Extracted fields.
- Source record versions.
- Verification attempts.
- Validation runs.
- Validation results.
- Internal findings.
- Evidence references.
- Reviewer actions.
- Rectification responses.
- Audit events.

A submitted application revision must not be overwritten during rectification.

A corrected document must create a new document version.

A validation run must retain its original inputs.

Historical validation must remain reproducible.

## 8. Authentication and Authorisation

Support the PS 26262 role/permission packages:

- INSTITUTION_USER (Institution Representative)
- INTAKE_OFFICER (Intake / Registry Officer)
- SCRUTINY_OFFICER (Scrutiny / Processing Officer)
- REGIONAL_OFFICER (Regional Officer / Coordinator)
- EVC_COORDINATOR and EVC_MEMBER (EVC coordination / assigned participant)
- COMMITTEE_SECRETARIAT (Committee Secretariat / Panel Participant)
- BUREAU_SUPERVISOR (Bureau Supervisor / Senior Officer)
- COMPETENT_AUTHORITY (statutory decision authority)
- REGULATORY_POLICY_PUBLISHER (versioned regulatory policy publication)

Legacy AUDITOR, LEAD_AUDITOR and ADMIN codes remain only for backward compatibility. Map them to the appropriate UI workspace without broadening backend permissions.

Enforce permissions on the backend for every protected endpoint.

Do not trust:
- Browser-provided role values.
- Client-supplied institution IDs without verification.
- Client-supplied reviewer assignments.
- Frontend navigation restrictions as security enforcement.

Verify the authenticated user's active role and permitted scope.

Institution Users may access only their institution's permitted records.

Auditors may access only assigned cases.

Lead Auditors may access cases within their permitted review scope.

Admins may manage system configuration and operational settings but must not automatically gain access to case contents.

Use secure password hashing for provisioned test and operational accounts.

Never store plaintext passwords.

Keep credentials and secret values outside source code.

## 9. PostgreSQL Row-Level Security

The supplied schema uses PostgreSQL Row-Level Security (RLS).

Preserve and test this security model.

Important requirements:

- Use a dedicated restricted application database role.
- Do not use the migration-owner account for normal application requests.
- Never give the application role BYPASSRLS.
- Establish authenticated database user context through trusted backend code.
- Use transaction-local security context.
- Do not allow the browser to set database security context.
- Ensure pooled database connections do not retain user context from previous requests.
- Apply the required grants and policies.
- Test both authorised and unauthorised queries.

The application must enforce permissions even where RLS is also enabled.

Admin must not receive implicit case-content access.

Service-only operations, including protected source replay mappings, must use appropriately restricted service access.

## 10. Document Storage and Upload Security

Never store document binaries directly in ordinary database columns.

Use private storage behind a storage-service abstraction.

The processing sequence is:

Authorisation
-> Upload
-> Quarantine
-> File Validation
-> Malware Scan
-> SHA-256
-> Private Storage
-> Document Version
-> Processing Job

Validate:

- Extension allowlist.
- Actual detected MIME type.
- File signatures / magic bytes.
- File size.
- PDF page count.
- Image dimensions.
- File parsing failures.

Use random storage keys.

Never use original filenames as storage paths.

Never expose public document URLs.

Never overwrite original document bytes.

Keep raw files private and return them only through authorised backend endpoints.

## 11. Background Processing

Use Redis and Celery for expensive asynchronous tasks.

Examples:

- OCR processing.
- PDF page processing.
- Image preprocessing.
- Document integrity observations.
- Source connector operations.
- Report generation where appropriate.

Upload requests should return a job identifier and processing status without waiting for OCR to finish.

Use explicit job states:

- QUEUED
- PROCESSING
- COMPLETED
- PARTIAL
- FAILED
- NEEDS_MANUAL_REVIEW

Make background tasks idempotent.

Retries must not create duplicate documents, findings, audit events or notifications.

Use bounded retry policies.

Record meaningful errors without logging private document contents or secrets.

Do not use FastAPI in-process background tasks for heavy OCR workloads.

## 12. Regulatory Rule Engine

Implement regulatory rules as deterministic, testable services.

Use the seven specified rule identifiers:

- EOA-SD-01
- EOA-SD-02
- EOA-SD-03
- EOA-SD-04
- EOA-SD-05
- EOA-SD-06
- EOA-SD-07

Preserve applicability and result distinctions.

Possible requirement states include:

- PENDING
- UPLOADED
- SATISFIED
- DEFICIENT
- NOT_APPLICABLE
- UNABLE_TO_DETERMINE
- UNDER_REVIEW

Keep findings separate from requirement statuses.

Every material finding must have:
- Finding category.
- Severity.
- Explanation.
- Rule reference.
- Evidence references.
- Review status.
- Human-review requirement.

Do not automatically convert uncertain data into a mismatch.

Do not invent regulatory validity periods.

Do not hardcode business rules inside API route handlers.

Keep rule evaluation independently testable.

## 13. Source Connector Hub

Implement a provider-independent connector interface.

Initial connectors must use local synthetic fixtures.

Support:

- VERIFIED
- MISMATCH
- EXPIRED
- PENDING
- SOURCE_UNAVAILABLE

Record:

- Source code.
- Environment.
- Method.
- Request correlation ID.
- Request and response timestamps.
- Adapter version.
- Compared fields.
- Response digest.
- Simulated/sandbox indicator.

Do not claim live source verification without an authorised operational integration.

Do not scrape restricted portals or bypass access controls.

Never treat a failed or unavailable source as verified.

## 14. Temporal Compliance Replay

Each validation run must preserve:

- Application revision.
- Evaluation-as-of timestamp.
- Exact rule versions.
- Exact source record versions.
- Validation outputs.
- Relevant processing references.

Replay must load the pinned historical inputs.

It must not silently query the latest source state.

Implement a deterministic test:

1. Validate against source snapshot A.
2. Update the current source record to B.
3. Replay the original validation.
4. Confirm that the original result still uses A.
5. Create a new validation run.
6. Confirm that the new run uses B.

## 15. Audit and ICPL

Maintain append-oriented application activity and review history.

Record:

- Actor.
- Role.
- Action.
- Resource.
- Timestamp.
- Previous and resulting state.
- Safe metadata.

Never log:
- Passwords.
- Tokens.
- Connector secrets.
- Private document contents.
- Unnecessary personal data.

ICPL must follow the specified hash-chain and Merkle proof design.

Use canonical event representations and deterministic cryptographic hashing.

Keep the batch root available as a separately trusted reference for integrity verification.

Do not describe an ordinary database hash field as a complete independent blockchain network.

## 16. Reports, Alerts and AIC Assist

Reports:

- Produce structured JSON.
- Support PDF generation.
- Include validation results and evidence references.
- Record generation timestamps.
- Respect role permissions.

Notifications:

- Use an outbox or equivalent durable delivery approach.
- Support in-app delivery first.
- Track event and delivery timestamps.
- Use idempotency to prevent duplicates.
- Retry transient delivery failures safely.

AIC Assist Lite:

- Use PostgreSQL full-text search.
- Search approved regulatory knowledge chunks.
- Return section and page citations.
- Enforce user and case permissions before retrieving information.
- Provide a retrieval-only fallback.
- Keep optional model inference separate.
- Never execute workflow actions or make statutory decisions.

## 17. Error Handling and Observability

Use centralised error handling.

Distinguish:

- Invalid input.
- Authentication failure.
- Permission denial.
- Missing resources.
- Business-rule failures.
- Processing failures.
- Database errors.
- External connector failures.

Record correlation IDs where appropriate.

Use structured logs.

Avoid leaking database internals, document contents or credentials in error responses.

## 18. Testing Requirements

Use pytest and HTTPX.

Test:

- API request validation.
- Database constraints.
- Service logic.
- Role permissions.
- Institution isolation.
- Auditor assignments.
- Admin separation.
- File upload validation.
- Processing failures.
- Rule conditions.
- Source status handling.
- Immutable revisions.
- Historical replay.
- Audit integrity.

Include positive and negative tests.

Do not claim an API or module is complete merely because the server starts.

## 19. Development Discipline

For each backend module:

1. Read the relevant prototype specification.
2. Map the required schema entities.
3. Define API contracts.
4. Implement service logic.
5. Implement API routes.
6. Implement permissions.
7. Add tests.
8. Integrate with the frontend.
9. Test the entire workflow.

Do not implement the entire backend in one uncontrolled generation.

Explain architectural changes before making them.

Prefer simple, well-tested implementations over unnecessary abstractions.

Never introduce a new database, message broker or framework without a justified requirement.
