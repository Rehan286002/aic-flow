/**
 * AIC-Flow — Validation Feature TypeScript Definitions
 * 
 * Accurately mirrors backend Pydantic schemas from backend/app/schemas/validation.py
 * and StrEnums from backend/app/models/enums.py.
 */

// Statutory evaluation outcomes produced by deterministic rule evaluators
export type ValidationResultStatus =
  | 'SATISFIED'
  | 'DEFICIENT'
  | 'NOT_APPLICABLE'
  | 'UNABLE_TO_DETERMINE';

// Permitted lifecycle states for regulatory findings
export type FindingStatus =
  | 'OPEN'
  | 'ACCEPTED'
  | 'DISMISSED'
  | 'CLARIFICATION_REQUESTED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'SUPERSEDED';

// Authoritative finding state machine mapping permitted status transitions
export const PERMITTED_FINDING_TRANSITIONS: Record<FindingStatus, FindingStatus[]> = {
  OPEN: ['ACCEPTED', 'DISMISSED', 'CLARIFICATION_REQUESTED', 'ESCALATED'],
  CLARIFICATION_REQUESTED: ['RESOLVED', 'ACCEPTED', 'DISMISSED', 'ESCALATED'],
  ESCALATED: ['ACCEPTED', 'DISMISSED', 'RESOLVED'],
  ACCEPTED: ['RESOLVED', 'ESCALATED'],
  DISMISSED: ['OPEN'],
  RESOLVED: ['OPEN', 'ESCALATED'],
  SUPERSEDED: [],
};

// Finding severity levels matching FindingSeverity StrEnum
export type FindingSeverity =
  | 'INFO'
  | 'LOW'
  | 'MEDIUM'
  | 'HIGH'
  | 'CRITICAL';

// Finding categories matching FindingCategory StrEnum
export type FindingCategory =
  | 'MISSING_DOCUMENT'
  | 'INCOMPLETE_DOCUMENT'
  | 'EXPIRED_DOCUMENT'
  | 'FIELD_MISMATCH'
  | 'DUPLICATE_DOCUMENT'
  | 'METADATA_ANOMALY'
  | 'CONTENT_ANOMALY'
  | 'SIGNATURE_ISSUE'
  | 'SOURCE_MISMATCH'
  | 'SOURCE_UNAVAILABLE'
  | 'LOW_OCR_CONFIDENCE'
  | 'REGULATORY_GAP'
  | 'INFRASTRUCTURE_OBSERVATION'
  | 'OTHER';

// Registered external source connector codes
export type SourceConnectorCode =
  | 'SRC_AICTE_PORTAL'
  | 'SRC_REVENUE_LAND'
  | 'SRC_MUNICIPAL_BLDG'
  | 'SRC_FIRE_SERVICES'
  | 'SRC_ICAI_UDIN'
  | 'SRC_BHUVAN_GEOMAP';

// Evidence link attached to a Finding (FindingEvidenceRead)
export interface FindingEvidenceRead {
  finding_evidence_id: string;
  finding_id?: string;
  validation_result_id?: string | null;
  document_version_id?: string | null;
  extracted_field_id?: string | null;
  verification_attempt_id?: string | null;
  page_number?: number | null;
  evidence_type: string;
  evidence_reference?: string | null;
  evidence_summary?: string | null;
  created_at: string;
}

// Regulatory Finding (FindingRead)
export interface FindingRead {
  finding_id: string;
  application_id: string;
  application_revision_id: string;
  validation_run_id?: string | null;
  validation_result_id?: string | null;
  category: FindingCategory;
  severity: FindingSeverity;
  status: FindingStatus;
  title: string;
  internal_reason?: string | null;
  recommended_action?: string | null;
  is_internal_only: boolean;
  created_at: string;
  updated_at: string;
  evidence: FindingEvidenceRead[];
}

// Single Requirement Rule Evaluation Result (ValidationResultRead)
export interface ValidationResultRead {
  validation_result_id: string;
  validation_run_id: string;
  application_requirement_id?: string | null;
  validation_rule_version_id?: string | null;
  result_status: ValidationResultStatus;
  expected_value?: unknown;
  observed_value?: unknown;
  explanation: string;
  evaluated_at: string;
  findings: FindingRead[];
}

// Summary Metrics for a Validation Run (ValidationRunSummary)
export interface ValidationRunSummary {
  validation_run_id: string;
  status: string; // 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  run_type: string; // 'FULL' | 'RULE_ONLY' | 'RECHECK'
  engine_version?: string | null;
  started_at: string;
  completed_at?: string | null;
  total_results: number;
  satisfied_count: number;
  deficient_count: number;
  not_applicable_count: number;
  unable_to_determine_count: number;
  warning_count?: number;
  findings_by_severity: Record<string, number>;
}

// Complete Validation Run Details (ValidationRunRead)
export interface ValidationRunRead {
  validation_run_id: string;
  application_revision_id: string;
  checklist_template_id?: string | null;
  run_type: string;
  engine_version?: string | null;
  status: string;
  started_at: string;
  completed_at?: string | null;
  evaluation_as_of: string;
  results: ValidationResultRead[];
  summary?: ValidationRunSummary | null;
}

// Payload for triggering a run (ValidationRunCreate)
export interface ValidationRunCreate {
  run_type?: string;
  checklist_item_ids?: string[] | null;
}

// Payload for auditor status update (FindingStatusUpdate)
export interface FindingStatusUpdate {
  status: FindingStatus;
  review_note: string; // Enforces minimum 5 non-whitespace chars
}

// Contradiction Explorer 4-tier comparison structure
export type ContradictionStatus =
  | 'MATCH'
  | 'CONTRADICTION'
  | 'ABSENT_IN_SOURCE'
  | 'UNVERIFIED';

export interface ContradictionRow {
  item_code: string; // e.g. 'EOA-SD-01'
  requirement_title: string;
  field_name: string;
  declared_value: string;
  ocr_extracted_value: string;
  ocr_confidence: number | null;
  ocr_bounding_box?: unknown;
  auditor_reviewed_value: string | null;
  auditor_review_status: 'ACCEPTED' | 'CORRECTED' | 'UNREVIEWED';
  source_registry_value: string | null;
  source_registry_code: SourceConnectorCode;
  source_provenance: 'SIMULATED';
  source_payload_hash: string | null;
  contradiction_status: ContradictionStatus;
  evaluation_outcome: ValidationResultStatus;
}

