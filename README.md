# AIC-Flow

**AICTE Approval Workflow and Compliance Platform**  
Smart India Hackathon 2026 · Problem Statement 26262

AIC-Flow brings application intake, category-specific routing, scrutiny, clarification and resubmission, EVC and committee coordination where applicable, authorised decisions, post-decision conditions, compliance evidence, notifications and audit history into one connected case lifecycle. Existing document extraction, evidence validation and verification capabilities remain available as a supporting subsystem.

## Architecture

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Pydantic + SQLAlchemy + Alembic
- Database: PostgreSQL
- Supporting services: Redis, ClamAV, private document storage
- OCR/text extraction: `pypdf`, `pypdfium2`, RapidOCR/ONNX Runtime and OpenCV-based document extraction pipeline

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

- Document text and field extraction are assistance signals. Regulatory assessment and statutory outcomes remain with authorised officers.
- Workflow and compliance checks use deterministic rules and persisted case records; no AI model makes an approval or rejection decision.

- Route logic is category-specific and version-pinned. Only configured categories are automatically routed; unsupported categories stop for manual policy confirmation.
- EVC and committee steps remain distinct. Their applicability must come from the approved category route.
- Statutory outcomes are entered only by an authorised Competent Authority user. The system does not make statutory decisions autonomously.
- No official AICTE or third-party live integration should be claimed unless credentials, authority, contracts and end-to-end tests exist.
- Institution and review-team access is enforced by the backend. Platform administrators do not automatically gain confidential case access.
- Extracted fields and document-integrity signals are review evidence, not proof of issuer authenticity.
