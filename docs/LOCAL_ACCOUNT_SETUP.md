# Account provisioning

AIC-Flow does not ship shared passwords or public self-registration. Accounts are created by an authorised operator against the intended database.

## First administrator

1. Configure the backend environment and database connection.
2. Apply migrations: `cd backend && uv run alembic upgrade head`.
3. Provision the first administrator from the backend service shell:

```bash
cd backend
uv run python scripts/provision_account.py --email <admin-email> --name "Platform Administrator" --role ADMIN
```

Set a unique password when prompted. Do not put passwords in shell history or environment files.

## Institution record and user

Institution records are not self-registered. Use the exact permanent ID and details from an authorised, current AICTE institution registry record. If the record has not already been loaded through an approved import, provision it from the backend service shell:

```bash
cd backend
uv run python scripts/provision_institution.py --permanent-id <official-permanent-id> --name "<official institution name>" --type "<institution type>" --address "<official address>" --district "<district>" --state "<state>" --postal-code <postal-code> --confirm-production
```

In production, the command additionally requires typing `CREATE-INSTITUTION-FROM-AUTHORISED-REGISTRY`. It never generates an identifier or overwrites/reactivates an existing record. Copy the resulting Institution ID into the authorised representative account command:

```bash
uv run python scripts/provision_account.py --email <user-email> --name "Institution Representative" --role INSTITUTION_USER --institution-id <institution-uuid> --confirm-production
```

The `--confirm-production` flag and `PRODUCTION` confirmation are required for the account command in production. Keep institution creation and account provisioning restricted to authorised operators.

## Operational user

Create or reuse a team and assign the role:

```bash
uv run python scripts/provision_account.py --email <officer-email> --name "Processing Officer" --role SCRUTINY_OFFICER --team-name "Central Processing Team"
```

The command prints the new team UUID. Use `--review-team-id <uuid>` to add further officers to the same team. Available operational roles are `INTAKE_OFFICER`, `SCRUTINY_OFFICER`, `REGIONAL_OFFICER`, `EVC_COORDINATOR`, `EVC_MEMBER`, `COMMITTEE_SECRETARIAT`, `BUREAU_SUPERVISOR`, `COMPETENT_AUTHORITY`, `AUDITOR`, and `LEAD_AUDITOR`.

## Production protection

For `APP_ENV=production`, the utility requires both `--confirm-production` and typing `PRODUCTION`. It refuses to overwrite existing users, reactivate inactive memberships, or reset passwords. Use a secure provider shell, not a public API. The utility does not create institutions or invent institution IDs.

## Checklist prerequisites

Before the first institution application can be created, seed the standard EoA checklist/reference catalogue. In local development run `uv run python scripts/seed_checklist.py` from `backend/`. In production, follow the separately gated process in `docs/DEPLOYMENT.md` only after reviewing the applicable AICTE handbook and effective amendments. Do not run local-account or non-production reference-data seed scripts in production.
