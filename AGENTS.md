# AIC-Flow — Project Instructions

## 1. Project identity

- Product: **AIC-Flow — AICTE Approval Workflow and Compliance Platform**.
- SIH 2026 problem statement: **PS 26262 — Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System**.
- Only repository permitted for source changes: `Rehan286002/aic-flow`. Do not modify, push to, or create changes in any other repository.
- Existing document extraction, evidence validation and verification records are retained as a separate supporting capability. Those records are not approval workflow cases and must not be reinterpreted or rewritten.

## 2. Product lifecycle

Institution application → category-specific route snapshot → intake/scrutiny where applicable → clarification and resubmission revisions → EVC where applicable → distinct committee proceedings where applicable → competent-authority decision → decision conditions → compliance obligations → evidence submission and human verification → reminders/escalations → closure and audit history.

Do not use one universal approval route. Every category must be tied to an approved, effective-dated policy route. Unknown or unverified categories must stop for policy confirmation rather than silently use a default route.

## 3. Regulatory and governance boundaries

- AICTE Approval Process Handbook and applicable amendments are the regulatory source hierarchy. Keep the handbook version and route snapshot with each case.
- Distinguish Scrutiny Committee, EVC, SHC/SAC and other proceedings. Scheduling coordination does not constitute committee appointment or statutory decision.
- The Competent Authority alone records the authorised statutory outcome. No model, workflow rule or administrator may autonomously approve or reject an application.
- Do not claim official AICTE, NSWS, eOffice, DigiLocker or API Setu connectivity unless an approved live integration has actually been configured, authenticated and tested.
- Keep statutory deadlines, academic-year schedules, case-specific undertakings, administrative targets and reminder policies as distinct deadline types.
- Extracted OCR values are candidates for review. A hash proves byte identity, not document authenticity.

## 4. Existing stack (reuse first)

Frontend: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS and existing UI components.

Backend: Python, FastAPI, SQLAlchemy, Alembic, Pydantic.

Data/services: PostgreSQL, Redis, private local file storage, existing document services and existing source adapters.

Document processing actually present in this repository: `pypdf`, `pypdfium2`, RapidOCR with ONNX Runtime and OpenCV. Do not claim PaddleOCR unless the implementation is deliberately changed and verified.

Use the current modular monolith. Do not add microservices, databases, libraries or managed vendors unless an explicit need is demonstrated.

## 5. Reuse and change policy

- Reuse authentication, institution/team scope, document upload, extraction, evidence, validation services, audit structures and shared UI components when they fit.
- Add a separate `WorkflowCase` lifecycle; do not overload the legacy validation-run state machine.
- Keep new workflow events and obligations persisted in PostgreSQL. Keep user-visible counts sourced from APIs, not constants or browser local storage.
- Preserve old application/document/evidence records and their meanings. New PS 26262 applications receive a workflow case.
- Maintain API contracts with typed Pydantic schemas and frontend TypeScript interfaces.

## 6. Role packages and access boundaries

The solution defines these 10 role/permission packages: Institution Representative, Intake/Registry Officer, Scrutiny/Processing Officer, Regional Officer/Coordinator, EVC Coordinator/Assigned Participant, Committee Secretariat/Panel Participant, Bureau Supervisor/Senior Officer, Competent Authority, Platform Administrator, and Regulatory Policy Publisher/Approver. Some operational packages may be represented by separate EVC Coordinator and EVC Member codes.

Enforce least privilege on the backend. Scope institution users to their own institution; scope processing roles to active review-team membership and case assignment. Platform Administrators do not automatically receive confidential case content or statutory decision access. Policy publishers manage policy, not case decisions.

## 7. Database and migration rules

- Use Alembic migrations for every schema change.
- Before deployment, confirm `alembic heads` returns exactly one head and test upgrade against a fresh PostgreSQL database.
- Preserve `schema/reference/AICTE_Regulatory_Platform_Schema_v4.sql` and `schema/reference/AICTE_Regulatory_Platform_Schema_v3_to_v4.sql` unchanged; the latter is an upgrade reference, not a fresh-install script.
- Do not reset or seed over existing data. Do not rewrite legacy validation records to fit the new workflow.
- Do not add production data, credentials, access tokens, user uploads or local database dumps to source control.

## 8. Security and privacy

- Store secrets only in deployment environment variables or a secret manager. Commit `.env.example` files with placeholders only.
- Uploaded evidence stays private and must be served through authenticated, scoped endpoints.
- Preserve immutable source documents and revision history.
- Validate uploads by extension, MIME, file signature, size and malware scan.
- Enforce server-side role and resource checks for every read and write. Hiding UI controls is not authorization.
- Use secure cookies, CSRF protection and explicit credentialed CORS origins in production.

## 9. Test and release standard

- Run focused backend tests, frontend unit tests, lint and a production frontend build.
- Test at minimum: category route gates, role-based transitions, institution/team isolation, resubmission revision preservation, obligation lifecycle, notification persistence, migration upgrade and document upload.
- Never report a feature as complete unless code exists and the relevant check has passed.
- If an integration is unavailable, show an explicit pending/manual path; do not display invented verification success.

## 10. Hosting expectations

- Frontend: Vercel project root `frontend`, build command `npm run build`, output `dist`.
- Backend: persistent Python/container host; FastAPI is not deployed as a static Vercel SPA.
- Database and Redis: managed PostgreSQL and Redis services, or the supplied container composition.
- Document storage: persistent private disk or an explicitly configured private object store; ephemeral container filesystem is not acceptable.
- Cross-origin frontend/backend auth requires HTTPS, `SameSite=None`, secure cookies, explicit `CORS_ALLOWED_ORIGINS`, and tested CSRF behaviour.
