export type ApplicationFamily =
  | 'NEW_INSTITUTION'
  | 'EXISTING_INSTITUTION'
  | 'UNIVERSITY'
  | 'OTHER';

export type ApplicationStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'VALIDATING'
  | 'RECTIFICATION_REQUESTED'
  | 'RESUBMITTED'
  | 'UNDER_AUDITOR_REVIEW'
  | 'ESCALATED_TO_LEAD'
  | 'UNDER_LEAD_REVIEW'
  | 'INSPECTION_REQUIRED'
  | 'RECOMMENDATION_ISSUED'
  | 'AWAITING_AUTHORITY_DISPOSITION'
  | 'ON_HOLD'
  | 'CLOSED';

export type RevisionStatus = 'DRAFT' | 'SUBMITTED' | 'SUPERSEDED';

export type RequirementStatus =
  | 'PENDING'
  | 'UPLOADED'
  | 'SATISFIED'
  | 'DEFICIENT'
  | 'NOT_APPLICABLE'
  | 'UNABLE_TO_DETERMINE'
  | 'UNDER_REVIEW';

export type ApplicabilityStatus =
  | 'APPLICABLE'
  | 'NOT_APPLICABLE'
  | 'PENDING_DETERMINATION';

export interface ApplicationListItem {
  application_id: string;
  application_number: string;
  institution_id: string;
  application_family: ApplicationFamily;
  process_type: string;
  academic_year: string;
  status: ApplicationStatus;
  current_revision_id: string | null;
  current_revision_number: number | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationRevision {
  application_revision_id: string;
  application_id: string;
  revision_number: number;
  status: RevisionStatus;
  created_at: string;
  submitted_at: string | null;
  declarations: Record<string, any>;
}

export interface StatusHistoryEntry {
  application_status_history_id: string;
  application_id: string;
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  changed_by: string | null;
  change_reason: string | null;
  changed_at: string;
}

export interface ApplicationRequirementItem {
  application_requirement_id: string;
  application_revision_id: string;
  checklist_item_id: string;
  item_code: string;
  title: string;
  description: string | null;
  expected_document_type_code: string | null;
  applicability_status: ApplicabilityStatus;
  status: RequirementStatus;
  determination_reason: string | null;
  last_evaluated_at: string | null;
  display_order: number;
}

export interface ApplicationDetail {
  application_id: string;
  application_number: string;
  institution_id: string;
  application_family: ApplicationFamily;
  process_type: string;
  academic_year: string;
  status: ApplicationStatus;
  current_revision: ApplicationRevision;
  status_history: StatusHistoryEntry[];
  requirements: ApplicationRequirementItem[];
  total_requirements: number;
  applicable_requirements: number;
  not_applicable_requirements: number;
  pending_requirements: number;
  satisfied_requirements: number;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreatePayload {
  process_type: string;
  academic_year: string;
  application_family: ApplicationFamily;
  completion_certificate_issue_date?: string | null;
  payment_applicable?: boolean | null;
  application_remarks?: string | null;
}

export interface ApplicationUpdatePayload {
  completion_certificate_issue_date?: string | null;
  payment_applicable?: boolean | null;
  application_remarks?: string | null;
}

