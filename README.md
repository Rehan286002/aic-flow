# AIC-Flow

**AICTE Approval Workflow and Compliance Platform**  
Smart India Hackathon 2026 · Problem Statement 26262

AIC-Flow brings application intake, category-specific routing, scrutiny, clarification and resubmission, EVC/committee coordination where applicable, authorised decisions, post-decision conditions, compliance evidence, notifications and audit history into one case lifecycle. Existing document extraction and evidence validation capabilities remain available as a supporting subsystem.

## Architecture

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Pydantic + SQLAlchemy + Alembic
- Database: PostgreSQL
- Supporting services: Redis, ClamAV, private document storage
- OCR/text extraction: existing `pypdf`, `pypdfium2`, RapidOCR/ONNX Runtime and OpenCV pipeline

This is a modular monolith. Do not deploy the frontend as a substitute for backend, database, queue or private document storage services.

## Local setup

1. Install Python 3.13, `uv`, Node.js 22, npm and Docker Compose.
2. Copy `.env.example` to `backend/.env`; set a unique local `JWT_SECRET_KEY`.
3. Start dependencies: `docker compose up -d postgres redis clamav`.
4. In `backend/`, run `uv sync`, then `uv run alembic upgrade head`, then `uv run uvicorn app.main:app --reload --port 8000`.
5. In `frontend/`, run `npm ci`, copy `.env.example` to `.env.local`, then `npm run dev`.
6. Open the Vite URL, sign in with an account provisioned by an authorised administrator, and use **Approval Workflow**. No shared default credentials are shipped.

## Verification

- Backend: `cd backend && uv run pytest tests/`
- Frontend: `cd frontend && npm test`
- Lint: `cd frontend && npm run lint`
- Production build: `cd frontend && npm run build`
- Migration graph: `cd backend && uv run alembic heads` (must report one head)

Run the migration against a fresh database and a backed-up existing database before production use. Do not reset data to test a migration.

## Deployment overview

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Vercel hosts the static frontend only. Deploy FastAPI to a persistent Python/container host and provision managed PostgreSQL, Redis and private persistent storage separately. Cross-origin cookie settings and CORS must be configured together.

## Regulatory and security boundaries

- Route logic is category-specific and version-pinned. Only configured categories are automatically routed; unsupported categories stop for manual policy confirmation.
- EVC and committee steps remain distinct. Their applicability must come from the approved category route.
- Statutory outcomes are entered only by an authorised Competent Authority user. The system does not make statutory decisions autonomously.
- No official AICTE or third-party live integration should be claimed unless credentials, authority, contracts and end-to-end tests exist.
- Institution and review-team access is enforced by the backend. Platform administrators do not automatically gain confidential case access.
- Extracted fields and document-integrity signals are review evidence, not proof of issuer authenticity.


## Local PS 26262 demonstration data

A separate synthetic walkthrough is available for local development. It creates
one fictional institution, three clearly named synthetic review-team groups,
role-specific demo accounts, applications distributed across those groups at
different workflow stages, stage-history events, EVC and
proceeding examples, post-decision obligations, notifications, and lease
validity metadata.

The seed is restricted to APP_ENV=local or APP_ENV=development, a loopback
PostgreSQL host, and the local database named aic_flow. It refuses the CI
database and remote hosts. It does not publish regulatory policy, create
official AICTE records, or create statutory decisions. Every seeded route is
tagged SIMULATION_ONLY.

After the local database and migrations are ready:

```powershell
cd backend
uv run python scripts/seed_checklist.py
uv run python scripts/seed_demo_data.py
```

The three review-team groups let Regional and Bureau users compare workload
without pretending that the names are official AICTE Regions. Operational demo
accounts receive delegated membership in all three synthetic groups; actual
production team membership remains assignment-scoped.

The seed prompts for one local demo password, shared by newly created demo
accounts. Existing demo accounts are never reset or reactivated. Alternatively,
set AIC_FLOW_DEMO_PASSWORD in your local shell before running the seed. Use a
unique password and never reuse a production credential.

The script prints the account emails and synthetic review-team groups, and
reports how many cases, obligations, document-validity records and synthetic
deadline/escalation alerts were created.
Sign in with a different role account to inspect each workspace and follow a
synthetic application through institution submission, processing, EVC,
proceedings, authority review, and compliance tracking.

The seed creates example overdue and upcoming notification records for stage
ageing, EVC, undertakings and document expiry so the notification centre and
supervisory queue are populated immediately. These are one-time local
demonstration events. They do not mean a recurring deadline scheduler, provider
delivery, email or SMS integration is running. Production reminder/escalation
processing still requires an authorised, monitored worker and published policy
versions.

**Document validity demonstration boundary:** pre-seeded lease examples are
metadata-only records with non-downloadable placeholder storage keys. They
exercise expiry, renewal and officer-verification screens. Uploadable
application evidence uses the existing private document pipeline, malware
scanning, versioning and extraction process. The baseline EoA checklist does
not expose a separate standalone lease upload slot, so the demo does not
pretend that a placeholder is an uploaded or verified lease.
