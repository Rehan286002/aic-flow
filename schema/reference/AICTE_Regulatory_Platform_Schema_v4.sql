-- AICTE Application Validation, Document Authentication & Compliance Platform
-- PostgreSQL 18 recommended; verify the selected current minor release. Fresh-database baseline schema v4 (category-aware; source replay and AIC Assist extension).
-- This is a prototype/reference schema; review with AICTE-authorized domain/legal
-- stakeholders before production deployment. Never store actual API secrets here.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. ENUMS
-- ---------------------------------------------------------------------------
CREATE TYPE user_status AS ENUM ('ACTIVE','INVITED','SUSPENDED','DISABLED');
CREATE TYPE application_family AS ENUM (
  'NEW_INSTITUTION','EXISTING_INSTITUTION','UNIVERSITY','OTHER'
);
CREATE TYPE application_status AS ENUM (
  'DRAFT','SUBMITTED','VALIDATING','RECTIFICATION_REQUESTED','RESUBMITTED',
  'UNDER_AUDITOR_REVIEW','ESCALATED_TO_LEAD','UNDER_LEAD_REVIEW',
  'INSPECTION_REQUIRED','RECOMMENDATION_ISSUED','AWAITING_AUTHORITY_DISPOSITION',
  'ON_HOLD','CLOSED'
);
CREATE TYPE revision_status AS ENUM ('DRAFT','SUBMITTED','SUPERSEDED');
CREATE TYPE requirement_status AS ENUM (
  'PENDING','UPLOADED','SATISFIED','DEFICIENT','NOT_APPLICABLE',
  'UNABLE_TO_DETERMINE','UNDER_REVIEW'
);
CREATE TYPE document_processing_status AS ENUM (
  'QUEUED','PROCESSING','COMPLETED','PARTIAL','FAILED','NEEDS_MANUAL_REVIEW'
);
CREATE TYPE finding_category AS ENUM (
  'MISSING_DOCUMENT','INCOMPLETE_DOCUMENT','EXPIRED_DOCUMENT','FIELD_MISMATCH',
  'DUPLICATE_DOCUMENT','METADATA_ANOMALY','CONTENT_ANOMALY','SIGNATURE_ISSUE',
  'SOURCE_MISMATCH','SOURCE_UNAVAILABLE','LOW_OCR_CONFIDENCE',
  'REGULATORY_GAP','INFRASTRUCTURE_OBSERVATION','OTHER'
);
CREATE TYPE finding_severity AS ENUM ('INFO','LOW','MEDIUM','HIGH','CRITICAL');
CREATE TYPE finding_status AS ENUM (
  'OPEN','ACCEPTED','DISMISSED','CLARIFICATION_REQUESTED','ESCALATED',
  'RESOLVED','SUPERSEDED'
);
CREATE TYPE verification_method AS ENUM ('QR_CODE','OFFICIAL_API','OFFICIAL_PORTAL','DIGILOCKER', 'DIGITAL_SIGNATURE','MANUAL');
CREATE TYPE verification_status AS ENUM (
  'PENDING','VERIFIED','MISMATCH','EXPIRED','SOURCE_UNAVAILABLE',
  'MANUAL_REVIEW_REQUIRED','FAILED','CANCELLED'
);
CREATE TYPE assignment_role AS ENUM ('AUDITOR','LEAD_AUDITOR');
CREATE TYPE team_role AS ENUM ('AUDITOR','LEAD_AUDITOR');
CREATE TYPE finding_review_action AS ENUM (
  'ACCEPT_FLAG','DISMISS_FLAG','REQUEST_CLARIFICATION','ESCALATE_TO_LEAD',
  'OVERRIDE_PRIOR_REVIEW','MARK_RESOLVED','ADD_NOTE'
);
CREATE TYPE rectification_status AS ENUM ('OPEN','PARTIALLY_RESPONDED','RESPONDED','CLOSED','CANCELLED');
CREATE TYPE recommendation_type AS ENUM ('PROCEED','HOLD','INSPECTION_REQUIRED');
CREATE TYPE inspection_status AS ENUM ('RECOMMENDED','ASSIGNED','SCHEDULED','IN_PROGRESS','REPORT_SUBMITTED','CLOSED','CANCELLED');
CREATE TYPE source_type AS ENUM ('ISSUING_AUTHORITY','DIGITAL_REPOSITORY','UNIVERSITY','GOVERNMENT_PORTAL','INTERNAL_REFERENCE');
CREATE TYPE audit_visibility AS ENUM ('INTERNAL_ONLY','INSTITUTION_ACTIVITY');
CREATE TYPE payment_status AS ENUM ('PAID','PENDING','FAILED','REFUNDED','NOT_REQUIRED');

-- ---------------------------------------------------------------------------
-- 2. IDENTITY, ROLES, INSTITUTIONS & REVIEW TEAMS
-- ---------------------------------------------------------------------------
CREATE TABLE institutions (
  institution_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aicte_permanent_institution_id VARCHAR(80) NOT NULL UNIQUE,
  institution_name     VARCHAR(300) NOT NULL,
  institution_type     VARCHAR(100),
  address_line         TEXT,
  district             VARCHAR(120),
  state                VARCHAR(120),
  postal_code          VARCHAR(20),
  is_active            BOOLEAN NOT NULL DEFAULT TRUE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  user_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name        VARCHAR(200) NOT NULL,
  email            VARCHAR(320) NOT NULL,
  password_hash    TEXT, -- Prefer external OIDC/SSO; never store plaintext passwords.
  external_subject VARCHAR(255),
  status           user_status NOT NULL DEFAULT 'INVITED',
  last_login_at    TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));
CREATE UNIQUE INDEX uq_users_external_subject ON users (external_subject) WHERE external_subject IS NOT NULL;

CREATE TABLE roles (
  role_id    SMALLSERIAL PRIMARY KEY,
  role_code  VARCHAR(40) NOT NULL UNIQUE,
  role_name  VARCHAR(100) NOT NULL,
  CONSTRAINT chk_role_code CHECK (role_code IN ('INSTITUTION_USER','AUDITOR','LEAD_AUDITOR','ADMIN'))
);
INSERT INTO roles(role_code, role_name) VALUES
 ('INSTITUTION_USER','Institution User (Applicant)'),
 ('AUDITOR','Auditor (Scrutiny Officer)'),
 ('LEAD_AUDITOR','Lead Auditor (Senior Officer)'),
 ('ADMIN','Admin (IT / System Admin)');

CREATE TABLE review_teams (
  review_team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_name      VARCHAR(160) NOT NULL UNIQUE,
  description    TEXT,
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE institution_memberships (
  institution_membership_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  user_id        UUID NOT NULL REFERENCES users(user_id),
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_by     UUID REFERENCES users(user_id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(institution_id, user_id)
);

CREATE TABLE review_team_members (
  review_team_member_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_team_id UUID NOT NULL REFERENCES review_teams(review_team_id),
  user_id        UUID NOT NULL REFERENCES users(user_id),
  team_role      team_role NOT NULL,
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  joined_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(review_team_id, user_id)
);

-- Role assignments are scoped. Institution users need an institution membership;
-- auditors/leads need a review-team membership; Admin is global.
CREATE TABLE user_role_assignments (
  user_role_assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(user_id),
  role_id        SMALLINT NOT NULL REFERENCES roles(role_id),
  institution_id UUID REFERENCES institutions(institution_id),
  review_team_id UUID REFERENCES review_teams(review_team_id),
  granted_by     UUID REFERENCES users(user_id),
  granted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at     TIMESTAMPTZ,
  CONSTRAINT chk_role_scope_shape CHECK (
    (institution_id IS NOT NULL AND review_team_id IS NULL)
    OR (institution_id IS NULL AND review_team_id IS NOT NULL)
    OR (institution_id IS NULL AND review_team_id IS NULL)
  )
);
CREATE INDEX idx_user_role_assignments_user ON user_role_assignments(user_id, revoked_at);

CREATE OR REPLACE FUNCTION enforce_user_role_scope()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_role_code VARCHAR(40);
BEGIN
  SELECT role_code INTO v_role_code FROM roles WHERE role_id = NEW.role_id;
  IF v_role_code = 'INSTITUTION_USER' THEN
    IF NEW.institution_id IS NULL OR NEW.review_team_id IS NOT NULL OR NOT EXISTS (
      SELECT 1 FROM institution_memberships im
      WHERE im.institution_id = NEW.institution_id AND im.user_id = NEW.user_id AND im.is_active = TRUE
    ) THEN RAISE EXCEPTION 'Institution User role requires an active membership in that institution'; END IF;
  ELSIF v_role_code = 'AUDITOR' THEN
    IF NEW.review_team_id IS NULL OR NEW.institution_id IS NOT NULL OR NOT EXISTS (
      SELECT 1 FROM review_team_members tm WHERE tm.review_team_id = NEW.review_team_id
      AND tm.user_id = NEW.user_id AND tm.team_role = 'AUDITOR' AND tm.is_active = TRUE
    ) THEN RAISE EXCEPTION 'Auditor role requires active Auditor membership in a review team'; END IF;
  ELSIF v_role_code = 'LEAD_AUDITOR' THEN
    IF NEW.review_team_id IS NULL OR NEW.institution_id IS NOT NULL OR NOT EXISTS (
      SELECT 1 FROM review_team_members tm WHERE tm.review_team_id = NEW.review_team_id
      AND tm.user_id = NEW.user_id AND tm.team_role = 'LEAD_AUDITOR' AND tm.is_active = TRUE
    ) THEN RAISE EXCEPTION 'Lead Auditor role requires active Lead Auditor membership in a review team'; END IF;
  ELSIF v_role_code = 'ADMIN' THEN
    IF NEW.institution_id IS NOT NULL OR NEW.review_team_id IS NOT NULL THEN
      RAISE EXCEPTION 'Admin role is global and cannot be institution/team scoped';
    END IF;
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER trg_enforce_user_role_scope
BEFORE INSERT OR UPDATE ON user_role_assignments
FOR EACH ROW EXECUTE FUNCTION enforce_user_role_scope();

-- ---------------------------------------------------------------------------
-- 3. APPLICATIONS, REVISIONS & INSTITUTIONAL MASTER RECORDS
-- ---------------------------------------------------------------------------
CREATE TABLE applications (
  application_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_number   VARCHAR(80) NOT NULL UNIQUE,
  institution_id       UUID NOT NULL REFERENCES institutions(institution_id),
  application_family    application_family NOT NULL,
  academic_year        VARCHAR(9) NOT NULL, -- e.g. 2026-27
  status               application_status NOT NULL DEFAULT 'DRAFT',
  review_team_id       UUID REFERENCES review_teams(review_team_id),
  current_revision_id  UUID,
  created_by           UUID NOT NULL REFERENCES users(user_id),
  submitted_at         TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_applications_institution ON applications(institution_id, created_at DESC);
CREATE INDEX idx_applications_team_status ON applications(review_team_id, status);

CREATE TABLE application_revisions (
  application_revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id) ON DELETE RESTRICT,
  revision_number INTEGER NOT NULL CHECK (revision_number > 0),
  status revision_status NOT NULL DEFAULT 'DRAFT',
  supersedes_revision_id UUID REFERENCES application_revisions(application_revision_id),
  created_by UUID NOT NULL REFERENCES users(user_id),
  submitted_by UUID REFERENCES users(user_id),
  submitted_at TIMESTAMPTZ,
  rectification_request_id UUID, -- FK added after rectification table exists
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(application_id, revision_number),
  UNIQUE(application_revision_id, application_id)
);
ALTER TABLE applications ADD CONSTRAINT fk_application_current_revision
  FOREIGN KEY(current_revision_id) REFERENCES application_revisions(application_revision_id);

CREATE TABLE institution_record_versions (
  institution_record_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  record_version INTEGER NOT NULL CHECK (record_version > 0),
  record_data JSONB NOT NULL,
  source_system VARCHAR(120) NOT NULL,
  source_reference TEXT,
  effective_from TIMESTAMPTZ NOT NULL,
  effective_to TIMESTAMPTZ,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  recorded_by UUID REFERENCES users(user_id),
  UNIQUE(institution_id, record_version)
);

CREATE TABLE application_status_history (
  application_status_history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  from_status application_status,
  to_status application_status NOT NULL,
  changed_by UUID REFERENCES users(user_id),
  change_reason TEXT,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_application_status_history ON application_status_history(application_id, changed_at DESC);

-- Dynamic application fields: stable identity/master data remains in institutions;
-- application-specific declarations are revisioned here.
CREATE TABLE application_field_definitions (
  field_definition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  field_code         VARCHAR(100) NOT NULL UNIQUE,
  field_label        VARCHAR(200) NOT NULL,
  data_type          VARCHAR(30) NOT NULL CHECK (data_type IN ('TEXT','NUMBER','DATE','BOOLEAN','JSON','IDENTIFIER')),
  applies_to         application_family[],
  applicant_editable BOOLEAN NOT NULL DEFAULT TRUE,
  is_active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE application_field_values (
  application_field_value_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  field_definition_id UUID NOT NULL REFERENCES application_field_definitions(field_definition_id),
  value_json         JSONB NOT NULL,
  entered_by         UUID NOT NULL REFERENCES users(user_id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(application_revision_id, field_definition_id)
);

CREATE TABLE institution_programmes (
  institution_programme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  programme_code VARCHAR(80) NOT NULL,
  programme_name VARCHAR(250) NOT NULL,
  approved_intake INTEGER CHECK (approved_intake >= 0),
  approval_reference VARCHAR(120),
  effective_from DATE,
  effective_to DATE,
  source_reference TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(institution_id, programme_code, effective_from)
);

CREATE TABLE institution_approval_records (
  institution_approval_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  previous_eoa_number VARCHAR(120) NOT NULL,
  academic_year VARCHAR(9) NOT NULL,
  approval_status VARCHAR(50) NOT NULL,
  approved_on DATE,
  source_reference TEXT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(institution_id, previous_eoa_number)
);

CREATE TABLE application_previous_approval_links (
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  institution_approval_record_id UUID NOT NULL REFERENCES institution_approval_records(institution_approval_record_id),
  PRIMARY KEY(application_revision_id, institution_approval_record_id)
);

CREATE TABLE application_programmes (
  application_programme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  programme_code VARCHAR(80) NOT NULL,
  programme_name VARCHAR(250) NOT NULL,
  requested_action VARCHAR(30) NOT NULL CHECK (requested_action IN ('CONTINUE','INCREASE_INTAKE','ADD_NEW_COURSE','CLOSE_COURSE')),
  existing_approved_intake INTEGER CHECK (existing_approved_intake >= 0),
  proposed_intake INTEGER CHECK (proposed_intake >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional structured faculty support for count/ratio/qualification checks.
-- Keep access restricted because these records may contain personal data.
CREATE TABLE application_faculty_entries (
  application_faculty_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  faculty_reference VARCHAR(100),
  faculty_name VARCHAR(200) NOT NULL,
  programme_code VARCHAR(80),
  designation VARCHAR(120),
  qualification VARCHAR(200),
  experience_years NUMERIC(5,2) CHECK (experience_years >= 0),
  employment_status VARCHAR(40),
  source_document_version_id UUID, -- FK added after document_versions table exists
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Payment records for TER/application-fee checks are linked to the uploaded receipt where available.
-- ---------------------------------------------------------------------------
-- 4. CONFIGURABLE CHECKLISTS & VERSIONED REGULATORY RULES
-- ---------------------------------------------------------------------------
CREATE TABLE checklist_templates (
  checklist_template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_code       VARCHAR(100) NOT NULL,
  template_name       VARCHAR(200) NOT NULL,
  application_family   application_family NOT NULL,
  academic_year_from  VARCHAR(9) NOT NULL,
  academic_year_to    VARCHAR(9),
  version_number      INTEGER NOT NULL CHECK (version_number > 0),
  regulatory_reference TEXT,
  is_published        BOOLEAN NOT NULL DEFAULT FALSE,
  created_by          UUID REFERENCES users(user_id),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(template_code, version_number)
);

CREATE TABLE checklist_items (
  checklist_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  checklist_template_id UUID NOT NULL REFERENCES checklist_templates(checklist_template_id) ON DELETE RESTRICT,
  item_code          VARCHAR(100) NOT NULL,
  title              VARCHAR(250) NOT NULL,
  description        TEXT,
  expected_document_type_code VARCHAR(80),
  is_mandatory_by_default BOOLEAN NOT NULL DEFAULT TRUE,
  applicability_condition JSONB NOT NULL DEFAULT '{}'::jsonb,
  validation_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  regulatory_clause_reference TEXT,
  display_order     INTEGER NOT NULL DEFAULT 0,
  UNIQUE(checklist_template_id, item_code)
);

CREATE TABLE validation_rules (
  validation_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_code          VARCHAR(100) NOT NULL UNIQUE,
  rule_name          VARCHAR(250) NOT NULL,
  description        TEXT,
  rule_category      VARCHAR(80) NOT NULL,
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE validation_rule_versions (
  validation_rule_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  validation_rule_id UUID NOT NULL REFERENCES validation_rules(validation_rule_id),
  version_number     INTEGER NOT NULL CHECK (version_number > 0),
  application_family   application_family,
  academic_year_from VARCHAR(9),
  academic_year_to   VARCHAR(9),
  effective_from     DATE,
  effective_to       DATE,
  condition_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
  evaluation_config  JSONB NOT NULL DEFAULT '{}'::jsonb,
  regulatory_reference TEXT,
  is_enabled         BOOLEAN NOT NULL DEFAULT TRUE,
  approved_by        UUID REFERENCES users(user_id),
  approved_at        TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(validation_rule_id, version_number)
);

CREATE TABLE checklist_item_rules (
  checklist_item_id UUID NOT NULL REFERENCES checklist_items(checklist_item_id) ON DELETE CASCADE,
  validation_rule_id UUID NOT NULL REFERENCES validation_rules(validation_rule_id),
  PRIMARY KEY(checklist_item_id, validation_rule_id)
);

CREATE TABLE application_requirements (
  application_requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  checklist_item_id UUID NOT NULL REFERENCES checklist_items(checklist_item_id),
  applicability_status VARCHAR(20) NOT NULL CHECK (applicability_status IN ('APPLICABLE','NOT_APPLICABLE','PENDING_DETERMINATION')),
  status requirement_status NOT NULL DEFAULT 'PENDING',
  determination_reason TEXT,
  last_evaluated_at TIMESTAMPTZ,
  UNIQUE(application_revision_id, checklist_item_id)
);

-- ---------------------------------------------------------------------------
-- 5. DOCUMENTS, IMMUTABLE VERSIONS, OCR & EXTRACTED FIELDS
-- ---------------------------------------------------------------------------
CREATE TABLE document_types (
  document_type_id SMALLSERIAL PRIMARY KEY,
  type_code        VARCHAR(80) NOT NULL UNIQUE,
  type_name        VARCHAR(200) NOT NULL,
  description      TEXT,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO document_types(type_code,type_name) VALUES
 ('AFFIDAVIT_UNDERTAKING','Affidavit / Undertaking'),
 ('PAYMENT_RECEIPT','TER / Application Fee Payment Receipt'),
 ('AFFILIATION_LETTER','University Affiliation Letter'),
 ('ACCREDITATION_CERTIFICATE','NAAC / NBA Accreditation Certificate'),
 ('TRUST_REGISTRATION','Society / Trust Registration'),
 ('LAND_DOCUMENT','Land Ownership / Lease Document'),
 ('BUILDING_DOCUMENT','Land / Building / Occupancy Document'),
 ('FIRE_SAFETY_CERTIFICATE','Fire Safety Certificate'),
 ('STRUCTURAL_STABILITY_CERTIFICATE','Structural Stability Certificate'),
 ('FACULTY_LIST','Faculty List'),
 ('INFRASTRUCTURE_PHOTO','Infrastructure Photograph'),
 ('FLOOR_PLAN','Floor Plan'),
 ('LAB_LIST','Laboratory List'),
 ('AUDITED_STATEMENT','Audited Financial Statement'),
 ('OTHER','Other Supporting Document');

CREATE TABLE documents (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  document_type_id SMALLINT REFERENCES document_types(document_type_id),
  document_label VARCHAR(250),
  created_by UUID NOT NULL REFERENCES users(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_versions (
  document_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE RESTRICT,
  version_number INTEGER NOT NULL CHECK (version_number > 0),
  original_filename VARCHAR(500) NOT NULL,
  storage_key TEXT NOT NULL, -- Object-storage key; do not store public file URLs.
  mime_type VARCHAR(150) NOT NULL,
  file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
  sha256_hex CHAR(64) NOT NULL,
  page_count INTEGER CHECK (page_count >= 0),
  uploaded_by UUID NOT NULL REFERENCES users(user_id),
  replaces_document_version_id UUID REFERENCES document_versions(document_version_id),
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(document_id, version_number)
);
CREATE INDEX idx_document_versions_hash ON document_versions(sha256_hex);

CREATE TABLE application_payment_records (
  application_payment_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  payment_type VARCHAR(60) NOT NULL CHECK (payment_type IN ('TER_FEE','APPLICATION_FEE','OTHER')) ,
  payment_status payment_status NOT NULL,
  amount NUMERIC(14,2) CHECK (amount >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'INR',
  transaction_reference VARCHAR(180),
  paid_at TIMESTAMPTZ,
  receipt_document_version_id UUID REFERENCES document_versions(document_version_id),
  verification_reference TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE application_document_links (
  application_document_link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id) ON DELETE RESTRICT,
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  uploaded_for_requirement_id UUID REFERENCES application_requirements(application_requirement_id),
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(application_revision_id, document_version_id)
);
CREATE INDEX idx_application_document_revision ON application_document_links(application_revision_id);

CREATE TABLE document_processing_jobs (
  document_processing_job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  processing_status document_processing_status NOT NULL DEFAULT 'QUEUED',
  pipeline_name VARCHAR(100) NOT NULL,
  pipeline_version VARCHAR(80),
  queued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  error_code VARCHAR(100),
  error_message TEXT
);

CREATE TABLE document_classifications (
  document_classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  predicted_document_type_id SMALLINT REFERENCES document_types(document_type_id),
  predicted_label VARCHAR(120),
  confidence NUMERIC(5,4) CHECK (confidence BETWEEN 0 AND 1),
  model_name VARCHAR(120),
  model_version VARCHAR(80),
  is_human_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
  confirmed_by UUID REFERENCES users(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_extractions (
  document_extraction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  processing_job_id UUID REFERENCES document_processing_jobs(document_processing_job_id),
  extraction_status document_processing_status NOT NULL,
  extraction_engine VARCHAR(120) NOT NULL,
  engine_version VARCHAR(80),
  language_code VARCHAR(20),
  full_text_storage_key TEXT, -- Prefer protected object storage for full OCR text.
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE extracted_fields (
  extracted_field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_extraction_id UUID NOT NULL REFERENCES document_extractions(document_extraction_id) ON DELETE CASCADE,
  field_code VARCHAR(120) NOT NULL,
  field_label VARCHAR(200),
  raw_value TEXT,
  normalized_value JSONB,
  confidence NUMERIC(5,4) CHECK (confidence BETWEEN 0 AND 1),
  page_number INTEGER CHECK (page_number > 0),
  bounding_box JSONB, -- e.g. {"x":0.1,"y":0.2,"width":0.3,"height":0.05}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_extracted_fields_code ON extracted_fields(field_code);

CREATE TABLE extracted_field_reviews (
  extracted_field_review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  extracted_field_id UUID NOT NULL REFERENCES extracted_fields(extracted_field_id),
  reviewed_by UUID NOT NULL REFERENCES users(user_id),
  corrected_value JSONB,
  review_note TEXT,
  accepted_as_extracted BOOLEAN NOT NULL DEFAULT FALSE,
  reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE application_faculty_entries ADD CONSTRAINT fk_faculty_source_doc_version
  FOREIGN KEY(source_document_version_id) REFERENCES document_versions(document_version_id);

-- ---------------------------------------------------------------------------
-- 6. EXTERNAL ISSUER / REPOSITORY VERIFICATION
-- ---------------------------------------------------------------------------
CREATE TABLE verification_sources (
  verification_source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_code VARCHAR(100) NOT NULL UNIQUE,
  source_name VARCHAR(250) NOT NULL,
  source_type source_type NOT NULL,
  supported_document_types SMALLINT[],
  official_domain VARCHAR(255),
  integration_mode VARCHAR(40) NOT NULL CHECK (integration_mode IN ('API','PORTAL','QR_RESOLUTION','DIGITAL_SIGNATURE','MANUAL','MOCK')),
  is_authorized BOOLEAN NOT NULL DEFAULT FALSE,
  is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  credential_secret_reference TEXT, -- Reference to a vault; never put secret values here.
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE verification_attempts (
  verification_attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  verification_source_id UUID REFERENCES verification_sources(verification_source_id),
  method verification_method NOT NULL,
  status verification_status NOT NULL DEFAULT 'PENDING',
  requested_by UUID REFERENCES users(user_id),
  source_reference_number VARCHAR(200),
  request_correlation_id VARCHAR(160),
  response_summary JSONB NOT NULL DEFAULT '{}'::jsonb, -- Redacted, minimum necessary data only.
  compared_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_response_reference TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX idx_verification_doc_status ON verification_attempts(document_version_id, status);

-- ---------------------------------------------------------------------------
-- 7. VALIDATION RUNS, RESULTS, FINDINGS & EVIDENCE LINKS
-- ---------------------------------------------------------------------------
CREATE TABLE validation_runs (
  validation_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id),
  checklist_template_id UUID REFERENCES checklist_templates(checklist_template_id),
  triggered_by UUID REFERENCES users(user_id),
  run_type VARCHAR(40) NOT NULL CHECK (run_type IN ('FULL','DOCUMENT_ONLY','RULE_ONLY','RECHECK')),
  engine_version VARCHAR(80),
  status VARCHAR(30) NOT NULL CHECK (status IN ('QUEUED','RUNNING','COMPLETED','PARTIAL','FAILED')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE validation_run_rule_versions (
  validation_run_id UUID NOT NULL REFERENCES validation_runs(validation_run_id) ON DELETE CASCADE,
  validation_rule_version_id UUID NOT NULL REFERENCES validation_rule_versions(validation_rule_version_id),
  PRIMARY KEY(validation_run_id, validation_rule_version_id)
);

CREATE TABLE validation_results (
  validation_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  validation_run_id UUID NOT NULL REFERENCES validation_runs(validation_run_id) ON DELETE CASCADE,
  application_requirement_id UUID REFERENCES application_requirements(application_requirement_id),
  validation_rule_version_id UUID REFERENCES validation_rule_versions(validation_rule_version_id),
  result_status VARCHAR(30) NOT NULL CHECK (result_status IN ('SATISFIED','DEFICIENT','NOT_APPLICABLE','UNABLE_TO_DETERMINE','WARNING')),
  expected_value JSONB,
  observed_value JSONB,
  explanation TEXT NOT NULL,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Findings are internal review records. Institution users must NOT receive direct
-- SELECT access to this table. Applicant-facing communication is in rectification_*.
CREATE TABLE findings (
  finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id),
  validation_run_id UUID REFERENCES validation_runs(validation_run_id),
  validation_result_id UUID REFERENCES validation_results(validation_result_id),
  category finding_category NOT NULL,
  severity finding_severity NOT NULL DEFAULT 'MEDIUM',
  status finding_status NOT NULL DEFAULT 'OPEN',
  title VARCHAR(250) NOT NULL,
  internal_reason TEXT NOT NULL,
  recommended_action TEXT,
  is_internal_only BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_findings_app_status ON findings(application_id, status, severity);

CREATE TABLE finding_evidence (
  finding_evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
  document_version_id UUID REFERENCES document_versions(document_version_id),
  extracted_field_id UUID REFERENCES extracted_fields(extracted_field_id),
  verification_attempt_id UUID REFERENCES verification_attempts(verification_attempt_id),
  validation_result_id UUID REFERENCES validation_results(validation_result_id),
  page_number INTEGER CHECK (page_number > 0),
  evidence_type VARCHAR(80) NOT NULL,
  evidence_reference TEXT,
  evidence_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_finding_evidence_target CHECK (
    num_nonnulls(document_version_id, extracted_field_id, verification_attempt_id, validation_result_id) >= 1
  )
);

CREATE TABLE document_integrity_checks (
  document_integrity_check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  check_type VARCHAR(80) NOT NULL CHECK (check_type IN ('HASH_DUPLICATE','PDF_METADATA','VISUAL_TAMPERING_INDICATOR','SIGNATURE_STRUCTURE','FILE_STRUCTURE')),
  outcome VARCHAR(40) NOT NULL CHECK (outcome IN ('PASS','WARNING','ANOMALY','ERROR','INCONCLUSIVE')),
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  tool_name VARCHAR(120),
  tool_version VARCHAR(80),
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 8. AUDITOR ASSIGNMENTS, REVIEWS, RECTIFICATION & LEAD ESCALATION
-- ---------------------------------------------------------------------------
CREATE TABLE application_assignments (
  application_assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  assignee_user_id UUID NOT NULL REFERENCES users(user_id),
  assignment_role assignment_role NOT NULL,
  review_team_id UUID REFERENCES review_teams(review_team_id),
  assigned_by UUID NOT NULL REFERENCES users(user_id),
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  assignment_note TEXT
);
CREATE INDEX idx_assignments_active_user ON application_assignments(assignee_user_id, application_id) WHERE ended_at IS NULL;

CREATE TABLE finding_review_actions (
  finding_review_action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID NOT NULL REFERENCES findings(finding_id),
  reviewer_user_id UUID NOT NULL REFERENCES users(user_id),
  reviewer_role assignment_role NOT NULL,
  action finding_review_action NOT NULL,
  note TEXT,
  previous_status finding_status,
  resulting_status finding_status,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rectification_requests (
  rectification_request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id),
  requested_by UUID NOT NULL REFERENCES users(user_id),
  status rectification_status NOT NULL DEFAULT 'OPEN',
  applicant_message TEXT NOT NULL, -- Carefully worded; do not expose internal anomaly reasoning.
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  due_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ
);
ALTER TABLE application_revisions ADD CONSTRAINT fk_revision_rectification_request
  FOREIGN KEY(rectification_request_id) REFERENCES rectification_requests(rectification_request_id);

CREATE TABLE rectification_editable_fields (
  rectification_request_id UUID NOT NULL REFERENCES rectification_requests(rectification_request_id) ON DELETE CASCADE,
  field_definition_id UUID NOT NULL REFERENCES application_field_definitions(field_definition_id),
  PRIMARY KEY(rectification_request_id, field_definition_id)
);

CREATE TABLE rectification_items (
  rectification_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rectification_request_id UUID NOT NULL REFERENCES rectification_requests(rectification_request_id) ON DELETE CASCADE,
  application_requirement_id UUID REFERENCES application_requirements(application_requirement_id),
  applicant_instruction TEXT NOT NULL,
  item_status VARCHAR(30) NOT NULL DEFAULT 'OPEN' CHECK (item_status IN ('OPEN','RESPONDED','ACCEPTED','REJECTED','CLOSED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Internal-only mapping between an applicant-facing rectification item and its finding.
-- Keep this table inaccessible to Institution User and Admin roles.
CREATE TABLE finding_rectification_links (
  rectification_item_id UUID NOT NULL REFERENCES rectification_items(rectification_item_id) ON DELETE CASCADE,
  finding_id UUID NOT NULL REFERENCES findings(finding_id),
  linked_by UUID NOT NULL REFERENCES users(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(rectification_item_id, finding_id)
);

CREATE TABLE rectification_responses (
  rectification_response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rectification_item_id UUID NOT NULL REFERENCES rectification_items(rectification_item_id) ON DELETE CASCADE,
  response_by UUID NOT NULL REFERENCES users(user_id),
  response_text TEXT,
  replacement_document_version_id UUID REFERENCES document_versions(document_version_id),
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE escalations (
  escalation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  finding_id UUID REFERENCES findings(finding_id),
  raised_by UUID NOT NULL REFERENCES users(user_id),
  assigned_lead_user_id UUID REFERENCES users(user_id),
  review_team_id UUID REFERENCES review_teams(review_team_id),
  reason TEXT NOT NULL,
  priority finding_severity NOT NULL DEFAULT 'HIGH',
  status VARCHAR(30) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_REVIEW','RESOLVED','CANCELLED')),
  raised_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE TABLE lead_recommendations (
  lead_recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  application_revision_id UUID NOT NULL REFERENCES application_revisions(application_revision_id),
  lead_auditor_user_id UUID NOT NULL REFERENCES users(user_id),
  recommendation recommendation_type NOT NULL,
  rationale TEXT NOT NULL,
  requires_physical_inspection BOOLEAN NOT NULL DEFAULT FALSE,
  supersedes_recommendation_id UUID REFERENCES lead_recommendations(lead_recommendation_id),
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inspection_cases (
  inspection_case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  lead_recommendation_id UUID NOT NULL REFERENCES lead_recommendations(lead_recommendation_id),
  status inspection_status NOT NULL DEFAULT 'RECOMMENDED',
  reason TEXT NOT NULL,
  assigned_to UUID REFERENCES users(user_id),
  scheduled_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inspection_observations (
  inspection_observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inspection_case_id UUID NOT NULL REFERENCES inspection_cases(inspection_case_id) ON DELETE CASCADE,
  observer_user_id UUID NOT NULL REFERENCES users(user_id),
  observation TEXT NOT NULL,
  evidence_document_version_id UUID REFERENCES document_versions(document_version_id),
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 9. CASE AUDIT, SYSTEM LOGS, CONFIGURATION LOGS & NOTIFICATIONS
-- ---------------------------------------------------------------------------
CREATE TABLE case_audit_events (
  case_audit_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(application_id),
  actor_user_id UUID REFERENCES users(user_id),
  action_code VARCHAR(100) NOT NULL,
  resource_type VARCHAR(80) NOT NULL,
  resource_id UUID,
  visibility audit_visibility NOT NULL DEFAULT 'INTERNAL_ONLY',
  event_summary TEXT,
  redacted_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_case_audit_app_time ON case_audit_events(application_id, occurred_at DESC);

-- Admin-visible operational logs must not contain document text, findings, decision
-- rationale, credentials, tokens or other application-content payloads.
CREATE TABLE system_settings (
  setting_key VARCHAR(150) PRIMARY KEY,
  setting_value JSONB NOT NULL,
  description TEXT,
  is_sensitive BOOLEAN NOT NULL DEFAULT FALSE, -- Sensitive secrets belong in a vault, not here.
  updated_by UUID REFERENCES users(user_id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE system_audit_logs (
  system_audit_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES users(user_id),
  action_code VARCHAR(100) NOT NULL,
  component VARCHAR(100) NOT NULL,
  outcome VARCHAR(30) NOT NULL,
  correlation_id VARCHAR(160),
  redacted_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE configuration_audit_logs (
  configuration_audit_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID NOT NULL REFERENCES users(user_id),
  configuration_type VARCHAR(80) NOT NULL,
  configuration_id UUID,
  action_code VARCHAR(40) NOT NULL CHECK (action_code IN ('CREATE','UPDATE','PUBLISH','DISABLE','DELETE')),
  before_state JSONB,
  after_state JSONB,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
  notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_user_id UUID NOT NULL REFERENCES users(user_id),
  application_id UUID REFERENCES applications(application_id),
  notification_type VARCHAR(80) NOT NULL,
  title VARCHAR(200) NOT NULL,
  message TEXT NOT NULL,
  safe_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_recipient ON notifications(recipient_user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- 10. ACCESS-CONTROL HELPERS & ROW-LEVEL SECURITY BASELINE
-- ---------------------------------------------------------------------------
-- The trusted backend must set this transaction-local context only after verifying
-- the authenticated identity. Never allow the browser/client to set it directly.
CREATE SCHEMA IF NOT EXISTS app_security;
CREATE OR REPLACE FUNCTION app_security.current_user_id()
RETURNS UUID LANGUAGE SQL STABLE AS $$
  SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

-- SECURITY DEFINER helpers avoid recursive RLS checks on membership/assignment tables.
-- In production, own these functions with a dedicated no-login DB role and restrict EXECUTE.
CREATE OR REPLACE FUNCTION app_security.is_institution_member(p_institution_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, app_security AS $$
  SELECT EXISTS (
    SELECT 1 FROM institution_memberships im
    WHERE im.institution_id = p_institution_id
      AND im.user_id = app_security.current_user_id()
      AND im.is_active = TRUE
  )
$$;

CREATE OR REPLACE FUNCTION app_security.is_assigned_auditor(p_application_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, app_security AS $$
  SELECT EXISTS (
    SELECT 1 FROM application_assignments aa
    WHERE aa.application_id = p_application_id
      AND aa.assignee_user_id = app_security.current_user_id()
      AND aa.assignment_role = 'AUDITOR'
      AND aa.ended_at IS NULL
  )
$$;

CREATE OR REPLACE FUNCTION app_security.is_lead_for_application(p_application_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, app_security AS $$
  SELECT EXISTS (
    SELECT 1
    FROM applications a
    JOIN review_team_members rtm ON rtm.review_team_id = a.review_team_id
    WHERE a.application_id = p_application_id
      AND rtm.user_id = app_security.current_user_id()
      AND rtm.team_role = 'LEAD_AUDITOR'
      AND rtm.is_active = TRUE
  ) OR EXISTS (
    SELECT 1 FROM application_assignments aa
    WHERE aa.application_id = p_application_id
      AND aa.assignee_user_id = app_security.current_user_id()
      AND aa.assignment_role = 'LEAD_AUDITOR'
      AND aa.ended_at IS NULL
  )
$$;

-- Enable RLS on sensitive case-content tables. No Admin policy is intentionally added.
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_field_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_document_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE finding_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE rectification_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE rectification_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE rectification_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_cases ENABLE ROW LEVEL SECURITY;

CREATE POLICY application_document_links_select_policy ON application_document_links FOR SELECT USING (
  EXISTS (SELECT 1 FROM application_revisions ar JOIN applications a USING(application_id)
    WHERE ar.application_revision_id = application_document_links.application_revision_id
      AND (app_security.is_institution_member(a.institution_id)
        OR app_security.is_assigned_auditor(a.application_id)
        OR app_security.is_lead_for_application(a.application_id)))
);
CREATE POLICY application_document_links_institution_insert_policy ON application_document_links FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM application_revisions ar JOIN applications a USING(application_id)
    WHERE ar.application_revision_id = application_document_links.application_revision_id
      AND app_security.is_institution_member(a.institution_id)
      AND ar.status = 'DRAFT' AND a.status IN ('DRAFT','RECTIFICATION_REQUESTED'))
);

-- Applications: institution members see their institution; assigned auditors see assigned
-- cases; team Lead Auditors see their team's cases. Admins get no case-content policy.
CREATE POLICY applications_select_policy ON applications FOR SELECT USING (
  app_security.is_institution_member(institution_id)
  OR app_security.is_assigned_auditor(application_id)
  OR app_security.is_lead_for_application(application_id)
);

CREATE POLICY applications_institution_update_policy ON applications FOR UPDATE USING (
  app_security.is_institution_member(institution_id) AND status IN ('DRAFT','RECTIFICATION_REQUESTED')
) WITH CHECK (
  app_security.is_institution_member(institution_id) AND status IN ('DRAFT','RECTIFICATION_REQUESTED','RESUBMITTED')
);

CREATE POLICY application_revisions_select_policy ON application_revisions FOR SELECT USING (
  EXISTS (SELECT 1 FROM applications a WHERE a.application_id = application_revisions.application_id
    AND (app_security.is_institution_member(a.institution_id)
      OR app_security.is_assigned_auditor(a.application_id)
      OR app_security.is_lead_for_application(a.application_id)))
);

CREATE POLICY application_field_values_select_policy ON application_field_values FOR SELECT USING (
  EXISTS (SELECT 1 FROM application_revisions ar JOIN applications a USING(application_id)
    WHERE ar.application_revision_id = application_field_values.application_revision_id
      AND (app_security.is_institution_member(a.institution_id)
        OR app_security.is_assigned_auditor(a.application_id)
        OR app_security.is_lead_for_application(a.application_id)))
);

CREATE POLICY application_requirements_select_policy ON application_requirements FOR SELECT USING (
  EXISTS (SELECT 1 FROM application_revisions ar JOIN applications a USING(application_id)
    WHERE ar.application_revision_id = application_requirements.application_revision_id
      AND (app_security.is_institution_member(a.institution_id)
        OR app_security.is_assigned_auditor(a.application_id)
        OR app_security.is_lead_for_application(a.application_id)))
);

CREATE POLICY documents_select_policy ON documents FOR SELECT USING (
  app_security.is_institution_member(institution_id)
  OR EXISTS (SELECT 1 FROM application_document_links adl
    JOIN application_revisions ar ON ar.application_revision_id = adl.application_revision_id
    WHERE adl.document_version_id IN (SELECT dv.document_version_id FROM document_versions dv WHERE dv.document_id = documents.document_id)
      AND (app_security.is_assigned_auditor(ar.application_id) OR app_security.is_lead_for_application(ar.application_id)))
);

CREATE POLICY document_versions_select_policy ON document_versions FOR SELECT USING (
  EXISTS (SELECT 1 FROM documents d WHERE d.document_id = document_versions.document_id
    AND app_security.is_institution_member(d.institution_id))
  OR EXISTS (SELECT 1 FROM application_document_links adl
    JOIN application_revisions ar ON ar.application_revision_id = adl.application_revision_id
    WHERE adl.document_version_id = document_versions.document_version_id
      AND (app_security.is_assigned_auditor(ar.application_id) OR app_security.is_lead_for_application(ar.application_id)))
);

-- Crucial: findings and finding evidence are visible to assigned Auditors/Lead Auditors only.
-- Institution users and Admins have no SELECT policy on these tables.
CREATE POLICY findings_internal_select_policy ON findings FOR SELECT USING (
  app_security.is_assigned_auditor(application_id)
  OR app_security.is_lead_for_application(application_id)
);
CREATE POLICY finding_evidence_internal_select_policy ON finding_evidence FOR SELECT USING (
  EXISTS (SELECT 1 FROM findings f WHERE f.finding_id = finding_evidence.finding_id
    AND (app_security.is_assigned_auditor(f.application_id) OR app_security.is_lead_for_application(f.application_id)))
);

CREATE POLICY verification_attempts_select_policy ON verification_attempts FOR SELECT USING (
  EXISTS (SELECT 1 FROM application_document_links adl
    JOIN application_revisions ar ON ar.application_revision_id = adl.application_revision_id
    WHERE adl.document_version_id = verification_attempts.document_version_id
      AND (app_security.is_assigned_auditor(ar.application_id) OR app_security.is_lead_for_application(ar.application_id)))
);

CREATE POLICY rectification_requests_select_policy ON rectification_requests FOR SELECT USING (
  EXISTS (SELECT 1 FROM applications a WHERE a.application_id = rectification_requests.application_id
    AND (app_security.is_institution_member(a.institution_id)
      OR app_security.is_assigned_auditor(a.application_id)
      OR app_security.is_lead_for_application(a.application_id)))
);
CREATE POLICY rectification_items_select_policy ON rectification_items FOR SELECT USING (
  EXISTS (SELECT 1 FROM rectification_requests rr JOIN applications a USING(application_id)
    WHERE rr.rectification_request_id = rectification_items.rectification_request_id
      AND (app_security.is_institution_member(a.institution_id)
        OR app_security.is_assigned_auditor(a.application_id)
        OR app_security.is_lead_for_application(a.application_id)))
);
CREATE POLICY rectification_responses_select_policy ON rectification_responses FOR SELECT USING (
  EXISTS (SELECT 1 FROM rectification_items ri JOIN rectification_requests rr USING(rectification_request_id)
    JOIN applications a USING(application_id)
    WHERE ri.rectification_item_id = rectification_responses.rectification_item_id
      AND (app_security.is_institution_member(a.institution_id)
        OR app_security.is_assigned_auditor(a.application_id)
        OR app_security.is_lead_for_application(a.application_id)))
);

CREATE POLICY case_audit_internal_select_policy ON case_audit_events FOR SELECT USING (
  app_security.is_assigned_auditor(application_id)
  OR app_security.is_lead_for_application(application_id)
);
-- An institution-facing activity feed should be exposed through a narrowly scoped VIEW/API
-- that filters visibility='INSTITUTION_ACTIVITY'; do not grant direct access to this table.

CREATE POLICY lead_recommendations_select_policy ON lead_recommendations FOR SELECT USING (
  app_security.is_lead_for_application(application_id)
  OR app_security.is_assigned_auditor(application_id)
);
CREATE POLICY inspection_cases_select_policy ON inspection_cases FOR SELECT USING (
  app_security.is_lead_for_application(application_id)
  OR app_security.is_assigned_auditor(application_id)
);

-- ---------------------------------------------------------------------------
-- 11. IMPLEMENTATION NOTES
-- ---------------------------------------------------------------------------
-- 1) Apply table/column GRANTs to separate application DB roles. RLS is not a substitute
--    for least-privilege GRANTs, API authorization, encryption or secure object storage.
-- 2) Admin access: grant Admin only to configuration tables, users/roles management,
--    system_audit_logs and configuration_audit_logs. Do NOT grant application content tables.
-- 3) Institution API must expose rectification request instructions and own application
--    state, never findings, finding_evidence, finding_rectification_links, internal audit
--    events or anomaly details. Return an allowlisted projection of rectification_items.
-- 4) Only Lead Auditor endpoints may insert lead_recommendations or create inspection_cases.
--    Enforce this in backend authorization and preferably stored procedures/triggers too.
-- 5) Submitted revisions/document versions should be immutable. Rectification creates a
--    new application_revision and new document_version; never overwrite evidence in place.
-- 6) Every validation_run must pin the checklist template and rule versions used. For a
--    production build add validation_run_rule_versions(run_id, rule_version_id) to record
--    the exact full set of evaluated rules.
-- 7) Configure retention, encryption-at-rest, TLS, malware scanning, backups, secrets vault,
--    and a formal approval process for any external source connector before real data use.


-- ---------------------------------------------------------------------------
-- 12. VERSIONED APPLICATION CATEGORIES AND OFFICIAL IDENTIFIERS
-- ---------------------------------------------------------------------------
-- Keep internal UUID keys separate from externally assigned AICTE identifiers.
-- application_family is a broad grouping; application_category_id is the exact,
-- extensible and clause-aware category used by checklist and rule selection.
CREATE TABLE application_categories (
  application_category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_code VARCHAR(80) NOT NULL UNIQUE,
  category_name VARCHAR(240) NOT NULL,
  application_family application_family NOT NULL,
  chapter_reference VARCHAR(160),
  description TEXT,
  active_from DATE,
  active_to DATE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE(application_category_id, application_family)
);

-- Category names reflect the APH's application pathways. A published rule set must
-- still carry the exact clause, academic-year applicability and effective dates.
INSERT INTO application_categories(category_code, category_name, application_family, chapter_reference, description)
VALUES
 ('NEW_TECHNICAL_INSTITUTION','Grant of approval for a new technical institution','NEW_INSTITUTION','APH 2024-27, Chapter I','New-institution pathway; configure category-specific eligibility and documents.'),
 ('EOA_SELF_DISCLOSURE','EoA based on self-disclosure','EXISTING_INSTITUTION','APH 2024-27, Chapter II / Annexure 2.1','Prototype target; the selected demo pins the supplied APH 2024-27 baseline.'),
 ('EOA_AFTER_BREAK','EoA after a break in preceding academic years','EXISTING_INSTITUTION','APH 2024-27, Chapter II / Annexure 2.1','Full-solution pathway; requirements are clause- and fact-dependent.'),
 ('EOA_RESTORATION_INTAKE','Restoration of intake','EXISTING_INSTITUTION','APH 2024-27, Chapter II / Annexure 2.1','Full-solution pathway; requirements are clause- and fact-dependent.'),
 ('INCREASE_INTAKE','Increase in intake','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; additional evidence and EVC flow as applicable.'),
 ('ADDITIONAL_COURSE','Introduction of additional course(s)','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('NEW_PROGRAMME_LEVEL','Start a new programme / level in an existing institution','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('NRI_SEATS','Introduction / continuation of NRI seats','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; verify precise applicable conditions.'),
 ('FOREIGN_NATIONAL_SUPERNUMERARY_SEATS','Foreign national / OCI / children of Indian workers in Gulf supernumerary seats','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; verify precise applicable conditions.'),
 ('INTEGRATED_DUAL_DEGREE','Introduction of integrated / dual degree course','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('OFF_CAMPUS','Introduction of off-campus','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('FELLOW_PROGRAMME_MANAGEMENT','Introduction / continuation of Fellow Programme in Management','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('MERGER_INSTITUTIONS','Merger of institutions','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; common-campus/city and management facts require rule mapping.'),
 ('DIPLOMA_DEGREE_CONVERSION','Conversion of diploma level into degree level or vice versa','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('WOMEN_COED_CONVERSION','Conversion of women’s institution into co-educational institution or vice versa','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('CHANGE_SITE_LOCATION','Change of site / location','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('COURSE_CHANGE_MERGER_REDUCTION_CLOSURE','Course name change, course merger, intake reduction or course/programme closure','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('INSTITUTION_UNIVERSITY_NAME_CHANGE','Change in institution name, affiliating university/board or institution type','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('TRUST_SOCIETY_COMPANY_CHANGE','Change in trust / society / company name or address','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; category-specific rule set required.'),
 ('CLOSURE_INSTITUTION','Closure of institution','EXISTING_INSTITUTION','APH 2024-27, Chapter II','Full-solution pathway; closure and student-protection conditions require rule mapping.'),
 ('UNIVERSITY_TECHNICAL_PROGRAMME','University / deemed-to-be-university technical programme approval pathway','UNIVERSITY','APH 2024-27, Chapter IV','Separate university pathway; do not reuse institution EoA checklist.'),
 ('ODL_ONLINE','Open and Distance Learning / Online Learning approval pathway','UNIVERSITY','APH 2024-27, Chapter V','Separate pathway; category-specific rules and approvals required.'),
 ('OTHER_APPROVAL_PATHWAY','Other published AICTE approval pathway','OTHER','APH / subsequent official notification','Use only after an authoritative clause and checklist are approved.')
ON CONFLICT (category_code) DO NOTHING;

-- A submission has a broad family plus one exact, version-aware category. The family
-- is for shared form fields; category_id drives checklist/rule selection.
ALTER TABLE applications
  ADD COLUMN IF NOT EXISTS application_category_id UUID,
  ADD COLUMN IF NOT EXISTS aicte_application_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS aicte_file_number VARCHAR(100);
ALTER TABLE applications ALTER COLUMN application_category_id SET NOT NULL;
ALTER TABLE applications ADD CONSTRAINT fk_applications_category_family
  FOREIGN KEY(application_category_id, application_family)
  REFERENCES application_categories(application_category_id, application_family);
CREATE INDEX IF NOT EXISTS idx_applications_category_year
  ON applications(application_category_id, academic_year, status);

-- Checklist templates are always pinned to one exact application category.
ALTER TABLE checklist_templates ADD COLUMN IF NOT EXISTS application_category_id UUID;
ALTER TABLE checklist_templates ALTER COLUMN application_category_id SET NOT NULL;
ALTER TABLE checklist_templates ADD CONSTRAINT fk_checklist_category_family
  FOREIGN KEY(application_category_id, application_family)
  REFERENCES application_categories(application_category_id, application_family);

-- A rule version may be reused across more than one category through this mapping table.
CREATE TABLE IF NOT EXISTS validation_rule_version_categories (
  validation_rule_version_id UUID NOT NULL REFERENCES validation_rule_versions(validation_rule_version_id) ON DELETE CASCADE,
  application_category_id UUID NOT NULL REFERENCES application_categories(application_category_id),
  PRIMARY KEY(validation_rule_version_id, application_category_id)
);

-- Dynamic fields may be enabled for specific categories as well as broad families.
CREATE TABLE IF NOT EXISTS application_field_definition_categories (
  field_definition_id UUID NOT NULL REFERENCES application_field_definitions(field_definition_id) ON DELETE CASCADE,
  application_category_id UUID NOT NULL REFERENCES application_categories(application_category_id),
  PRIMARY KEY(field_definition_id, application_category_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_applications_aicte_application_id
  ON applications(aicte_application_id) WHERE aicte_application_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_applications_file_number
  ON applications(aicte_file_number) WHERE aicte_file_number IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 13. REGULATORY SOURCE GOVERNANCE AND MODEL/PIPELINE VERSIONING
-- ---------------------------------------------------------------------------
CREATE TABLE regulatory_sources (
  regulatory_source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_title VARCHAR(300) NOT NULL,
  source_type VARCHAR(80) NOT NULL,
  issuing_body VARCHAR(240) NOT NULL,
  publication_date DATE,
  effective_from DATE,
  effective_to DATE,
  source_url TEXT,
  source_file_sha256 CHAR(64),
  source_file_storage_key TEXT,
  is_authoritative BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rule_approval_records (
  rule_approval_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_version_id UUID NOT NULL REFERENCES validation_rule_versions(validation_rule_version_id),
  submitted_by UUID NOT NULL REFERENCES users(user_id),
  reviewed_by UUID REFERENCES users(user_id),
  approved_by UUID REFERENCES users(user_id),
  approval_status VARCHAR(24) NOT NULL CHECK (approval_status IN ('DRAFT','IN_REVIEW','APPROVED','REJECTED','RETIRED')),
  review_comment TEXT,
  submitted_at TIMESTAMPTZ,
  reviewed_at TIMESTAMPTZ,
  approved_at TIMESTAMPTZ,
  effective_from DATE,
  effective_to DATE,
  UNIQUE(rule_version_id, submitted_at)
);

CREATE TABLE model_registry (
  model_registry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  component_code VARCHAR(80) NOT NULL,
  model_name VARCHAR(200) NOT NULL,
  model_version VARCHAR(100) NOT NULL,
  model_artifact_sha256 CHAR(64),
  library_name VARCHAR(150),
  library_version VARCHAR(80),
  language_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluation_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  approved_for_use BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(component_code, model_name, model_version)
);

-- Record the exact OCR/rule/matcher versions involved in a processing run.
CREATE TABLE processing_component_runs (
  processing_component_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  validation_run_id UUID REFERENCES validation_runs(validation_run_id),
  document_processing_job_id UUID REFERENCES document_processing_jobs(document_processing_job_id),
  model_registry_id UUID REFERENCES model_registry(model_registry_id),
  component_code VARCHAR(80) NOT NULL,
  configuration_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status VARCHAR(24) NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','PARTIAL','FAILED','CANCELLED')),
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- ---------------------------------------------------------------------------
-- 14. FILE-SAFETY, SIGNATURE AND METADATA EVIDENCE
-- ---------------------------------------------------------------------------
CREATE TABLE document_security_scans (
  document_security_scan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  scanner_name VARCHAR(120) NOT NULL,
  scanner_version VARCHAR(80),
  signature_database_version VARCHAR(100),
  scan_status VARCHAR(24) NOT NULL CHECK (scan_status IN ('CLEAN','DETECTED','ERROR','NOT_SCANNED')),
  threat_name VARCHAR(240),
  scanned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  scan_log_reference TEXT
);

CREATE TABLE document_metadata_observations (
  document_metadata_observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  metadata_source VARCHAR(40) NOT NULL CHECK (metadata_source IN ('PDF_INFO','XMP','EXIF','FILE_SYSTEM','SERVER_INGEST')),
  metadata_key VARCHAR(160) NOT NULL,
  metadata_value TEXT,
  trust_level VARCHAR(24) NOT NULL DEFAULT 'UNTRUSTED' CHECK (trust_level IN ('UNTRUSTED','SERVER_OBSERVED','CRYPTOGRAPHICALLY_BOUND')),
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE digital_signature_checks (
  digital_signature_check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id UUID NOT NULL REFERENCES document_versions(document_version_id),
  signature_index INTEGER NOT NULL DEFAULT 0,
  signature_format VARCHAR(40),
  digest_algorithm VARCHAR(40),
  signer_subject TEXT,
  signer_certificate_fingerprint CHAR(64),
  signature_integrity_valid BOOLEAN,
  certificate_chain_valid BOOLEAN,
  revocation_status VARCHAR(32) CHECK (revocation_status IN ('GOOD','REVOKED','UNKNOWN','UNAVAILABLE','NOT_CHECKED')),
  timestamp_status VARCHAR(32) CHECK (timestamp_status IN ('VALID','INVALID','UNAVAILABLE','NOT_PRESENT','NOT_CHECKED')),
  trust_policy_id VARCHAR(120),
  validation_details JSONB NOT NULL DEFAULT '{}'::jsonb,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 15. CROSS-INSTITUTION CANDIDATE LINKS (REVIEW SIGNALS, NOT VERDICTS)
-- ---------------------------------------------------------------------------
CREATE TABLE cross_institution_candidate_links (
  cross_institution_candidate_link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  left_institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  right_institution_id UUID NOT NULL REFERENCES institutions(institution_id),
  left_entity_type VARCHAR(40) NOT NULL CHECK (left_entity_type IN ('FACULTY','DOCUMENT','IMAGE','LAND_RECORD','ASSET')),
  right_entity_type VARCHAR(40) NOT NULL CHECK (right_entity_type IN ('FACULTY','DOCUMENT','IMAGE','LAND_RECORD','ASSET')),
  left_entity_ref UUID NOT NULL,
  right_entity_ref UUID NOT NULL,
  match_method VARCHAR(80) NOT NULL,
  match_score NUMERIC(6,2),
  score_is_probability BOOLEAN NOT NULL DEFAULT FALSE,
  evidence_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  review_status VARCHAR(24) NOT NULL DEFAULT 'UNREVIEWED' CHECK (review_status IN ('UNREVIEWED','CONFIRMED_LINK','DISMISSED','NEEDS_MORE_EVIDENCE')),
  reviewed_by UUID REFERENCES users(user_id),
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (left_institution_id <> right_institution_id)
);
CREATE INDEX idx_cross_institution_candidate_score
  ON cross_institution_candidate_links(match_score DESC, created_at DESC);

-- ---------------------------------------------------------------------------
-- 16. NOTIFICATION OUTBOX (RELIABLE, RETRYABLE, AUDITABLE DELIVERY)
-- ---------------------------------------------------------------------------
CREATE TABLE notification_outbox (
  notification_outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  notification_id UUID REFERENCES notifications(notification_id),
  channel VARCHAR(20) NOT NULL CHECK (channel IN ('IN_APP','EMAIL','SMS','WEBHOOK')),
  destination_ref TEXT,
  template_code VARCHAR(100) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  delivery_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (delivery_status IN ('PENDING','SENDING','SENT','RETRY','FAILED','SUPPRESSED')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_error_code VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ
);
CREATE INDEX idx_notification_outbox_retry
  ON notification_outbox(delivery_status, next_attempt_at)
  WHERE delivery_status IN ('PENDING','RETRY');

-- ---------------------------------------------------------------------------
-- 17. IMMUTABLE COMPLIANCE PROVENANCE LEDGER (ICPL) PROTOTYPE TABLES
-- ---------------------------------------------------------------------------
-- Do not store PDFs, personal data, or raw OCR content in a public/permissioned
-- ledger. The database stores off-chain event references and cryptographic data.
-- A trusted ledger anchor, if activated, carries only a batch root + opaque ID.
CREATE TABLE icpl_events (
  icpl_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID REFERENCES applications(application_id),
  case_audit_event_id UUID REFERENCES case_audit_events(case_audit_event_id),
  sequence_no BIGINT NOT NULL UNIQUE,
  event_type VARCHAR(80) NOT NULL,
  actor_pseudonym CHAR(64),
  occurred_at TIMESTAMPTZ NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_reference VARCHAR(160) NOT NULL,
  canonical_event JSONB NOT NULL,
  commitment_salt_ciphertext BYTEA NOT NULL,
  previous_event_hash CHAR(64),
  event_hash CHAR(64) NOT NULL UNIQUE,
  batch_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_icpl_events_application_sequence ON icpl_events(application_id, sequence_no);

CREATE TABLE icpl_batches (
  icpl_batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_sequence_no BIGINT NOT NULL,
  last_sequence_no BIGINT NOT NULL,
  leaf_count INTEGER NOT NULL CHECK (leaf_count > 0),
  hash_algorithm VARCHAR(32) NOT NULL DEFAULT 'SHA-256',
  tree_algorithm VARCHAR(80) NOT NULL DEFAULT 'RFC6962_DOMAIN_SEPARATED_MERKLE',
  merkle_root CHAR(64) NOT NULL,
  anchor_status VARCHAR(24) NOT NULL DEFAULT 'UNANCHORED' CHECK (anchor_status IN ('UNANCHORED','SUBMITTED','ANCHORED','FAILED','REVOKED')),
  anchor_network VARCHAR(100),
  anchor_transaction_ref VARCHAR(240),
  anchor_timestamp TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (last_sequence_no >= first_sequence_no)
);
ALTER TABLE icpl_events ADD CONSTRAINT fk_icpl_event_batch
  FOREIGN KEY(batch_id) REFERENCES icpl_batches(icpl_batch_id);

CREATE TABLE icpl_merkle_proofs (
  icpl_merkle_proof_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  icpl_event_id UUID NOT NULL REFERENCES icpl_events(icpl_event_id),
  icpl_batch_id UUID NOT NULL REFERENCES icpl_batches(icpl_batch_id),
  leaf_index INTEGER NOT NULL CHECK (leaf_index >= 0),
  sibling_hashes JSONB NOT NULL,
  sibling_positions JSONB NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(icpl_event_id, icpl_batch_id)
);

-- Explicitly separate ledger anchor administration from case access. The
-- production write path must be a privileged, audited service, not a browser.
CREATE TABLE icpl_anchor_operations (
  icpl_anchor_operation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  icpl_batch_id UUID NOT NULL REFERENCES icpl_batches(icpl_batch_id),
  requested_by_service VARCHAR(120) NOT NULL,
  target_network VARCHAR(120),
  operation_status VARCHAR(24) NOT NULL CHECK (operation_status IN ('QUEUED','SUBMITTED','CONFIRMED','FAILED')),
  transaction_reference TEXT,
  response_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Security note: ICPL event/proof/anchor tables are service-only and require explicit
-- least-privilege GRANTs; add RLS where these tables are directly exposed to user roles.
-- Institution users must never receive raw finding/audit payloads through ICPL endpoints;
-- use a narrowly filtered status/activity projection. Admin has no case-content
-- access. Ledger anchors and operations are service-only permissions.

-- ---------------------------------------------------------------------------
-- 18. IDENTIFIER AND PROTOTYPE CONFIGURATION NOTES
-- ---------------------------------------------------------------------------
-- Internal UUIDs remain the relational primary keys. The three official
-- identifiers from the provided workbook are separate business references:
-- 1) AICTE Permanent Institution ID -> institutions.aicte_permanent_institution_id
-- 2) AICTE Application ID -> applications.aicte_application_id
-- 3) AICTE File Number -> applications.aicte_file_number
-- Verify format/uniqueness rules against authorized records before production.


-- ---------------------------------------------------------------------------
-- 19. V4 ADDITIVE EXTENSION: SOURCE SYNCHRONIZATION, TEMPORAL REPLAY & AIC ASSIST
-- ---------------------------------------------------------------------------
-- Existing v3 application/document/rule/review model is retained. These tables
-- record source ingestion provenance, freeze source versions used by each
-- validation run, and support cited role-aware AIC Assist conversations.
-- Store only sanitized response metadata/digests here; keep secrets in a vault.

CREATE TABLE source_sync_runs (
  source_sync_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  verification_source_id UUID NOT NULL REFERENCES verification_sources(verification_source_id),
  environment VARCHAR(20) NOT NULL CHECK (environment IN ('SIMULATED','SANDBOX','PRODUCTION','PUBLIC_DATA')),
  sync_kind VARCHAR(40) NOT NULL CHECK (sync_kind IN ('FULL','INCREMENTAL','ON_DEMAND','HEALTH_CHECK')),
  adapter_version VARCHAR(80) NOT NULL,
  status VARCHAR(24) NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','PARTIAL','FAILED','CANCELLED')),
  request_correlation_id VARCHAR(160),
  source_published_at TIMESTAMPTZ,
  source_updated_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  records_received INTEGER NOT NULL DEFAULT 0 CHECK (records_received >= 0),
  response_sha256 CHAR(64),
  sanitized_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_code VARCHAR(100),
  error_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (completed_at IS NULL OR completed_at >= started_at)
);
CREATE INDEX idx_source_sync_runs_source_time
  ON source_sync_runs(verification_source_id, started_at DESC);
CREATE INDEX idx_source_sync_runs_status_time
  ON source_sync_runs(status, started_at DESC);

ALTER TABLE institution_record_versions
  ADD COLUMN source_sync_run_id UUID REFERENCES source_sync_runs(source_sync_run_id),
  ADD COLUMN source_updated_at TIMESTAMPTZ,
  ADD COLUMN source_payload_sha256 CHAR(64);
CREATE INDEX idx_institution_record_versions_source_sync
  ON institution_record_versions(source_sync_run_id);

ALTER TABLE validation_runs
  ADD COLUMN evaluation_as_of TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE validation_run_source_versions (
  validation_run_id UUID NOT NULL REFERENCES validation_runs(validation_run_id) ON DELETE CASCADE,
  institution_record_version_id UUID NOT NULL REFERENCES institution_record_versions(institution_record_version_id),
  source_sync_run_id UUID REFERENCES source_sync_runs(source_sync_run_id),
  source_code VARCHAR(100) NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(validation_run_id, institution_record_version_id)
);
CREATE INDEX idx_validation_run_source_versions_source
  ON validation_run_source_versions(source_code, captured_at DESC);

-- FTS is the default retrieval layer for the small/medium regulatory corpus.
-- pgvector is deliberately not required by this schema; add it only after a
-- measured semantic-search requirement and infrastructure review.
CREATE TABLE knowledge_chunks (
  knowledge_chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regulatory_source_id UUID NOT NULL REFERENCES regulatory_sources(regulatory_source_id) ON DELETE CASCADE,
  chunk_sequence INTEGER NOT NULL CHECK (chunk_sequence >= 0),
  section_reference VARCHAR(240),
  page_number INTEGER CHECK (page_number IS NULL OR page_number > 0),
  content_locator TEXT,
  chunk_text TEXT NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  approved_for_retrieval BOOLEAN NOT NULL DEFAULT FALSE,
  search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple'::regconfig, chunk_text)) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(regulatory_source_id, chunk_sequence)
);
CREATE INDEX idx_knowledge_chunks_search ON knowledge_chunks USING GIN(search_vector);
CREATE INDEX idx_knowledge_chunks_approved ON knowledge_chunks(approved_for_retrieval, regulatory_source_id);

CREATE TABLE assistant_conversations (
  assistant_conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id),
  role_code VARCHAR(40) NOT NULL CHECK (role_code IN ('INSTITUTION_USER','AUDITOR','LEAD_AUDITOR','ADMIN')),
  institution_id UUID REFERENCES institutions(institution_id),
  application_id UUID REFERENCES applications(application_id),
  access_scope_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ
);
CREATE INDEX idx_assistant_conversations_user_time
  ON assistant_conversations(user_id, created_at DESC);

CREATE TABLE assistant_messages (
  assistant_message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assistant_conversation_id UUID NOT NULL REFERENCES assistant_conversations(assistant_conversation_id) ON DELETE CASCADE,
  speaker VARCHAR(12) NOT NULL CHECK (speaker IN ('USER','ASSISTANT','SYSTEM')),
  message_text TEXT NOT NULL,
  model_registry_id UUID REFERENCES model_registry(model_registry_id),
  response_status VARCHAR(24) NOT NULL DEFAULT 'ANSWERED' CHECK (response_status IN ('ANSWERED','RETRIEVAL_ONLY','REFUSED','FAILED')),
  retrieval_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_assistant_messages_conversation_time
  ON assistant_messages(assistant_conversation_id, created_at);

CREATE TABLE assistant_message_citations (
  assistant_message_citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assistant_message_id UUID NOT NULL REFERENCES assistant_messages(assistant_message_id) ON DELETE CASCADE,
  knowledge_chunk_id UUID REFERENCES knowledge_chunks(knowledge_chunk_id),
  finding_evidence_id UUID REFERENCES finding_evidence(finding_evidence_id),
  institution_record_version_id UUID REFERENCES institution_record_versions(institution_record_version_id),
  validation_rule_version_id UUID REFERENCES validation_rule_versions(validation_rule_version_id),
  citation_label VARCHAR(300) NOT NULL,
  locator_text TEXT,
  excerpt_sha256 CHAR(64),
  sort_order SMALLINT NOT NULL DEFAULT 1 CHECK (sort_order > 0),
  CHECK (num_nonnulls(knowledge_chunk_id, finding_evidence_id,
                       institution_record_version_id, validation_rule_version_id) >= 1),
  UNIQUE(assistant_message_id, sort_order)
);
CREATE INDEX idx_assistant_citations_message
  ON assistant_message_citations(assistant_message_id, sort_order);

-- Security grants/RLS for these tables must follow the same least-privilege
-- model as the existing schema. Assistant retrieval must apply the caller's
-- role/institution/case scope before returning evidence; Admin has no case data.
-- User-facing message endpoints must not expose connector credentials, raw source
-- responses, hidden findings or another institution's records.


-- ---------------------------------------------------------------------------
-- V4 ROW-LEVEL SECURITY: SOURCE SNAPSHOTS AND AIC ASSIST
-- ---------------------------------------------------------------------------
-- Run with the trusted migration owner. The application connection must use a
-- non-owner, non-BYPASSRLS role and receive only the grants required by its API.
-- Source synchronization and frozen validation-source mappings are service data:
-- no direct application-role policies are created for these two tables.

ALTER TABLE institution_record_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS institution_record_versions_case_select_policy ON institution_record_versions;
CREATE POLICY institution_record_versions_case_select_policy
ON institution_record_versions FOR SELECT USING (
  app_security.is_institution_member(institution_id)
  OR EXISTS (
    SELECT 1 FROM applications a
    WHERE a.institution_id = institution_record_versions.institution_id
      AND (app_security.is_assigned_auditor(a.application_id)
        OR app_security.is_lead_for_application(a.application_id))
  )
);

ALTER TABLE source_sync_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_run_source_versions ENABLE ROW LEVEL SECURITY;
-- No policies for source_sync_runs or validation_run_source_versions: application
-- roles cannot read or write source connector telemetry or frozen replay mappings.
-- Grant access only to a separately provisioned ingestion/replay service role.

ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS knowledge_chunks_approved_select_policy ON knowledge_chunks;
CREATE POLICY knowledge_chunks_approved_select_policy
ON knowledge_chunks FOR SELECT USING (approved_for_retrieval = TRUE);
-- Only the curated-content ingestion/migration role may insert or update chunks.

ALTER TABLE assistant_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistant_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistant_message_citations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS assistant_conversations_select_own_policy ON assistant_conversations;
CREATE POLICY assistant_conversations_select_own_policy
ON assistant_conversations FOR SELECT USING (user_id = app_security.current_user_id());
DROP POLICY IF EXISTS assistant_conversations_insert_own_policy ON assistant_conversations;
CREATE POLICY assistant_conversations_insert_own_policy
ON assistant_conversations FOR INSERT WITH CHECK (user_id = app_security.current_user_id());
DROP POLICY IF EXISTS assistant_conversations_update_own_policy ON assistant_conversations;
CREATE POLICY assistant_conversations_update_own_policy
ON assistant_conversations FOR UPDATE USING (user_id = app_security.current_user_id())
WITH CHECK (user_id = app_security.current_user_id());

DROP POLICY IF EXISTS assistant_messages_select_own_policy ON assistant_messages;
CREATE POLICY assistant_messages_select_own_policy
ON assistant_messages FOR SELECT USING (
  EXISTS (SELECT 1 FROM assistant_conversations ac
    WHERE ac.assistant_conversation_id = assistant_messages.assistant_conversation_id
      AND ac.user_id = app_security.current_user_id())
);
DROP POLICY IF EXISTS assistant_messages_insert_own_policy ON assistant_messages;
CREATE POLICY assistant_messages_insert_own_policy
ON assistant_messages FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM assistant_conversations ac
    WHERE ac.assistant_conversation_id = assistant_messages.assistant_conversation_id
      AND ac.user_id = app_security.current_user_id())
);

-- A user can see only their own assistant citations, and each citation target
-- must itself be visible to that user. Institution users can receive approved
-- handbook citations and their own institution-record references. Internal
-- finding evidence remains visible only to assigned Auditors/Lead Auditors.
DROP POLICY IF EXISTS assistant_citations_select_scoped_policy ON assistant_message_citations;
CREATE POLICY assistant_citations_select_scoped_policy
ON assistant_message_citations FOR SELECT USING (
  EXISTS (SELECT 1 FROM assistant_messages am
    JOIN assistant_conversations ac USING (assistant_conversation_id)
    WHERE am.assistant_message_id = assistant_message_citations.assistant_message_id
      AND ac.user_id = app_security.current_user_id())
  AND (
    (knowledge_chunk_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM knowledge_chunks kc
      WHERE kc.knowledge_chunk_id = assistant_message_citations.knowledge_chunk_id
        AND kc.approved_for_retrieval = TRUE))
    OR
    (finding_evidence_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM finding_evidence fe JOIN findings f USING (finding_id)
      WHERE fe.finding_evidence_id = assistant_message_citations.finding_evidence_id
        AND (app_security.is_assigned_auditor(f.application_id)
          OR app_security.is_lead_for_application(f.application_id))))
    OR
    (institution_record_version_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM institution_record_versions irv
      WHERE irv.institution_record_version_id = assistant_message_citations.institution_record_version_id))
    OR
    (validation_rule_version_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM validation_rule_versions rv
      WHERE rv.validation_rule_version_id = assistant_message_citations.validation_rule_version_id
        AND rv.approved_by IS NOT NULL AND rv.approved_at IS NOT NULL))
  )
);
DROP POLICY IF EXISTS assistant_citations_insert_scoped_policy ON assistant_message_citations;
CREATE POLICY assistant_citations_insert_scoped_policy
ON assistant_message_citations FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM assistant_messages am
    JOIN assistant_conversations ac USING (assistant_conversation_id)
    WHERE am.assistant_message_id = assistant_message_citations.assistant_message_id
      AND ac.user_id = app_security.current_user_id())
  AND (
    (knowledge_chunk_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM knowledge_chunks kc
      WHERE kc.knowledge_chunk_id = assistant_message_citations.knowledge_chunk_id
        AND kc.approved_for_retrieval = TRUE))
    OR
    (finding_evidence_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM finding_evidence fe JOIN findings f USING (finding_id)
      WHERE fe.finding_evidence_id = assistant_message_citations.finding_evidence_id
        AND (app_security.is_assigned_auditor(f.application_id)
          OR app_security.is_lead_for_application(f.application_id))))
    OR
    (institution_record_version_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM institution_record_versions irv
      WHERE irv.institution_record_version_id = assistant_message_citations.institution_record_version_id))
    OR
    (validation_rule_version_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM validation_rule_versions rv
      WHERE rv.validation_rule_version_id = assistant_message_citations.validation_rule_version_id
        AND rv.approved_by IS NOT NULL AND rv.approved_at IS NOT NULL))
  )
);

-- Assistant tables are append-oriented: no delete/update policy is provided for
-- messages or citations. Retention/purge runs through a separately controlled job.

-- V4 table count: 80 total (74 v3 tables + 6 new tables).
