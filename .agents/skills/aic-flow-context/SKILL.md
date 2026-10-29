---
name: aic-flow-context
description: Engineering context for AIC-Flow SIH 2026 PS 26262 approval workflow, compliance monitoring, and alert management.
---

# AIC-Flow Engineering Context

## Product identity
AIC-Flow is the AICTE Approval, Inspection and Compliance Workflow Platform for SIH 2026 PS 26262. Its lifecycle covers application intake, category-specific route resolution, scrutiny and clarification, resubmission, EVC and distinct committee proceedings where applicable, competent-authority decisions, conditions, compliance obligations, validity tracking, persistent alerts and audit history.

## Existing system to reuse
The earlier AIC-Verify application provides the existing authentication, institution/team scoping, document upload, OCR/text extraction, evidence records, deterministic validation, source adapters and audit capabilities. Keep those as a separate evidence-intelligence subsystem. Never reinterpret its old validation records as PS 26262 approval workflow cases.

## Rules before implementation
1. Read `AGENTS.md` and `.agents/rules/project-scope.md`.
2. Inspect the existing models, API schemas, services, frontend routes and tests before adding new code.
3. Reuse existing capabilities and patterns; do not introduce new dependencies or microservices without a concrete need.
4. Keep application categories and effective regulatory routes distinct. Unknown or unverified categories must stop for policy confirmation, not use a default route.
5. Keep Scrutiny, EVC and committee proceedings separate. Scheduling is not committee constitution.
6. Only an authorised Competent Authority may record statutory approval/rejection.
7. Store workflow events, decisions, obligations and notifications in PostgreSQL, and enforce institution/team/individual assignment scope in the backend.
8. Do not claim live AICTE or third-party integrations unless approved credentials and end-to-end tests establish them.
9. Preserve historical document and application revisions. Use Alembic for schema changes; never reset or overwrite protected legacy data.
10. Run targeted tests and a production frontend build after each material change.

## Hosting
Vercel hosts the frontend only. FastAPI needs a persistent backend host, PostgreSQL, Redis/worker services where used, and private persistent document storage. See `docs/DEPLOYMENT.md`.
