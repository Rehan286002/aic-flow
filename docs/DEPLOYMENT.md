# Deployment guide

## Frontend — Vercel

Create a Vercel project from the AIC-Flow repository with:

- Root directory: `frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL=https://<your-api-host>`

`frontend/vercel.json` supplies the SPA fallback so deep links such as `/workflow` resolve to `index.html`. Use HTTPS for both frontend and backend.

## Backend — persistent Python/container host

Deploy `backend/Dockerfile` on a service that supports persistent API, worker and scheduler processes and outgoing access to managed PostgreSQL, Redis and ClamAV (or an approved scanning alternative). Do not deploy FastAPI as a static Vercel site. Configure the following environment variables in the host secret/configuration panel:

- `APP_ENV=production`
- `DATABASE_URL` — managed PostgreSQL connection string with SSL as required by the provider
- `REDIS_URL` — managed Redis connection string
- `JWT_SECRET_KEY` — cryptographically random secret, at least 32 bytes
- `JWT_ISSUER=aic-flow`
- `JWT_AUDIENCE=aic-flow-api`
- `CORS_ALLOWED_ORIGINS=["https://<your-vercel-domain>"]` (JSON array)
- `ACCESS_COOKIE_NAME=aic_flow_access`
- `CSRF_COOKIE_NAME=aic_flow_csrf`
- `COOKIE_SAMESITE=none`
- `COOKIE_SECURE=true`
- `MALWARE_SCANNER_TYPE=clamav` and `CLAMAV_HOST`/`CLAMAV_PORT` if ClamAV is used
- `STORAGE_ROOT_DIR` mapped to persistent private storage

Set the frontend's `VITE_API_URL` to the exact HTTPS backend origin, without an API path suffix. Rebuild/redeploy the frontend after changing it because Vite variables are build-time values.

## Workflow reminders and escalations

The production Compose file includes separate `workflow-worker` and `workflow-beat` services. Start both with the API and data services:

```bash
docker compose -f compose.prod.yaml up -d workflow-worker workflow-beat
```

The Beat process triggers the reminder cycle every 15 minutes; the worker evaluates enabled policy rows and creates persistent in-app notifications. Dispatch records and unique recipient/event keys make each policy/target reminder idempotent across retries and restarts. Run one Beat instance for a deployment; worker concurrency can be scaled independently.

For a managed container host, deploy two additional processes from the same backend image and environment:
- Worker command: `celery -A app.core.celery_app:celery_app worker --loglevel=INFO --concurrency=2`
- Scheduler command: `celery -A app.core.celery_app:celery_app beat --loglevel=INFO --schedule=/var/lib/aic-flow/beat-schedule`

Persist the Beat schedule directory, keep only one active Beat scheduler, and ensure the worker and scheduler use the same PostgreSQL and Redis configuration as the API.

For local development, run these in separate backend terminals after starting PostgreSQL and Redis:

```bash
uv run celery -A app.core.celery_app:celery_app worker --loglevel=INFO
uv run celery -A app.core.celery_app:celery_app beat --loglevel=INFO
```

Reminders are delivered through the in-app notification centre. The configured policies cover application-stage due dates and post-approval condition due dates.

## Database and documents

Provision managed PostgreSQL and Redis separately. Apply migrations once from a controlled release job: `cd backend && uv run alembic upgrade head`. Confirm there is one Alembic head first. Never run development seed or reset scripts against production.

Document files must be stored on a persistent private disk or a private object-storage adapter. The current storage service uses a filesystem root; an ephemeral container filesystem will lose uploads on restart/redeployment. Do not make the storage directory publicly static.

## Cookie, CSRF and CORS check

The backend uses credentialed cookie authentication and CSRF protection. The frontend must call the backend with credentials (already configured). The backend must allow the exact frontend origin, not `*`, and allow credentials. `SameSite=None` requires `Secure=true` and HTTPS. Validate login, refresh/current-user, CSRF-protected write and logout in the deployed cross-origin setup.

## What is not automatically deployed

This repository configuration does not create hosting accounts, provision paid database/storage resources, issue AICTE/API Setu credentials, or enable an official AICTE integration. Those require owner/provider action and service-specific configuration. Scheduled reminder delivery requires both the dedicated worker and the single Beat scheduler to be running.

## Baseline checklist publication

A fresh database needs the category checklist and shared document/field reference rows before an institution can start an EoA self-disclosure application. After the migration and before enabling institution submissions, review the current AICTE Approval Process Handbook plus every effective corrigendum/amendment for the target academic year. The bundled checklist is a baseline starting point, not an automatic confirmation that every later amendment has been incorporated.

For a reviewed production release, run the idempotent seed explicitly from the backend service shell:

```bash
cd backend
uv run python scripts/seed_checklist.py --confirm-production
```

The command requires typing `PUBLISH-EOA-APH-2024-2027-BASELINE` when prompted. It only seeds shared checklist/reference data; it does not create institutions, accounts, applications, source records, or decisions. Do not run `seed_demo.py`, `seed_sources.py`, or reset scripts in production. Unconfigured application categories remain blocked pending policy review.
