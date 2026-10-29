-- Upgrade migration: AICTE Regulatory Platform schema v3 -> v4
-- Run once against a database that has successfully applied schema v3.
-- The migration is additive and preserves existing application data.
CREATE TABLE IF NOT EXISTS source_sync_runs (
  source_sync_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  verification_source_id UUID NOT NULL REFERENCES verification_sources(verification_source_id),
  environment VARCHAR(20) NOT NULL CHECK (environment IN ('SIMULATED','SANDBOX','PRODUCTION','PUBLIC_DATA')),
  sync_kind VARCHAR(40) NOT NULL CHECK (sync_kind IN ('FULL','INCREMENTAL','ON_DEMAND','HEALTH_CHECK')),
  adapter_version VARCHAR(80) NOT NULL,
  status VARCHAR(24) NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','PARTIAL','FAILED','CANCELLED')),
  request_correlation_id VARCHAR(160), source_published_at TIMESTAMPTZ, source_updated_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ,
  records_received INTEGER NOT NULL DEFAULT 0 CHECK (records_received >= 0),
  response_sha256 CHAR(64), sanitized_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_code VARCHAR(100), error_summary TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (completed_at IS NULL OR completed_at >= started_at)
);
CREATE INDEX IF NOT EXISTS idx_source_sync_runs_source_time ON source_sync_runs(verification_source_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_sync_runs_status_time ON source_sync_runs(status, started_at DESC);

ALTER TABLE institution_record_versions ADD COLUMN IF NOT EXISTS source_sync_run_id UUID REFERENCES source_sync_runs(source_sync_run_id);
ALTER TABLE institution_record_versions ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ;
ALTER TABLE institution_record_versions ADD COLUMN IF NOT EXISTS source_payload_sha256 CHAR(64);
CREATE INDEX IF NOT EXISTS idx_institution_record_versions_source_sync ON institution_record_versions(source_sync_run_id);
ALTER TABLE validation_runs ADD COLUMN IF NOT EXISTS evaluation_as_of TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS validation_run_source_versions (
  validation_run_id UUID NOT NULL REFERENCES validation_runs(validation_run_id) ON DELETE CASCADE,
  institution_record_version_id UUID NOT NULL REFERENCES institution_record_versions(institution_record_version_id),
  source_sync_run_id UUID REFERENCES source_sync_runs(source_sync_run_id),
  source_code VARCHAR(100) NOT NULL, captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(validation_run_id, institution_record_version_id)
);
CREATE INDEX IF NOT EXISTS idx_validation_run_source_versions_source ON validation_run_source_versions(source_code, captured_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  knowledge_chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regulatory_source_id UUID NOT NULL REFERENCES regulatory_sources(regulatory_source_id) ON DELETE CASCADE,
  chunk_sequence INTEGER NOT NULL CHECK (chunk_sequence >= 0), section_reference VARCHAR(240),
  page_number INTEGER CHECK (page_number IS NULL OR page_number > 0), content_locator TEXT,
  chunk_text TEXT NOT NULL, content_sha256 CHAR(64) NOT NULL,
  approved_for_retrieval BOOLEAN NOT NULL DEFAULT FALSE,
  search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple'::regconfig, chunk_text)) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(regulatory_source_id, chunk_sequence)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_search ON knowledge_chunks USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_approved ON knowledge_chunks(approved_for_retrieval, regulatory_source_id);

CREATE TABLE IF NOT EXISTS assistant_conversations (
  assistant_conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id),
  role_code VARCHAR(40) NOT NULL CHECK (role_code IN ('INSTITUTION_USER','AUDITOR','LEAD_AUDITOR','ADMIN')),
  institution_id UUID REFERENCES institutions(institution_id), application_id UUID REFERENCES applications(application_id),
  access_scope_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), closed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_assistant_conversations_user_time ON assistant_conversations(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS assistant_messages (
  assistant_message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assistant_conversation_id UUID NOT NULL REFERENCES assistant_conversations(assistant_conversation_id) ON DELETE CASCADE,
  speaker VARCHAR(12) NOT NULL CHECK (speaker IN ('USER','ASSISTANT','SYSTEM')),
  message_text TEXT NOT NULL, model_registry_id UUID REFERENCES model_registry(model_registry_id),
  response_status VARCHAR(24) NOT NULL DEFAULT 'ANSWERED' CHECK (response_status IN ('ANSWERED','RETRIEVAL_ONLY','REFUSED','FAILED')),
  retrieval_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_assistant_messages_conversation_time ON assistant_messages(assistant_conversation_id, created_at);

CREATE TABLE IF NOT EXISTS assistant_message_citations (
  assistant_message_citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assistant_message_id UUID NOT NULL REFERENCES assistant_messages(assistant_message_id) ON DELETE CASCADE,
  knowledge_chunk_id UUID REFERENCES knowledge_chunks(knowledge_chunk_id),
  finding_evidence_id UUID REFERENCES finding_evidence(finding_evidence_id),
  institution_record_version_id UUID REFERENCES institution_record_versions(institution_record_version_id),
  validation_rule_version_id UUID REFERENCES validation_rule_versions(validation_rule_version_id),
  citation_label VARCHAR(300) NOT NULL, locator_text TEXT, excerpt_sha256 CHAR(64),
  sort_order SMALLINT NOT NULL DEFAULT 1 CHECK (sort_order > 0),
  CHECK (num_nonnulls(knowledge_chunk_id, finding_evidence_id, institution_record_version_id, validation_rule_version_id) >= 1),
  UNIQUE(assistant_message_id, sort_order)
);
CREATE INDEX IF NOT EXISTS idx_assistant_citations_message ON assistant_message_citations(assistant_message_id, sort_order);


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
