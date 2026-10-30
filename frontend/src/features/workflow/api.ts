import { request } from '@/lib/api';
import type { ApplicationRequirementItem } from '@/types/application';
import type { DocumentUploadResponse } from '@/types/document';

export interface WorkflowCase {
  workflow_case_id: string;
  application_id: string;
  application_number: string;
  institution_id: string;
  institution_name: string;
  academic_year: string;
  process_type: string;
  route_code: string;
  regulatory_version: string;
  route_snapshot: Record<string, unknown>;
  current_stage: string;
  assigned_role_code: string | null;
  assigned_user_id: string | null;
  due_at: string | null;
  stage_entered_at: string;
  updated_at: string;
}

export interface WorkflowEvent {
  workflow_event_id: string;
  event_type: string;
  from_stage: string | null;
  to_stage: string | null;
  summary: string;
  event_payload: Record<string, unknown>;
  actor_user_id: string;
  occurred_at: string;
}

export interface ComplianceObligation {
  obligation_id: string;
  title: string;
  description: string;
  source_condition: string;
  due_at: string;
  status: string;
  evidence_document_id: string | null;
  evidence_document_version_id: string | null;
  evidence_requirement_id: string | null;
  evidence_reference: string | null;
  verification_note: string | null;
}

export interface EVCVisit {
  evc_visit_id: string;
  workflow_case_id: string;
  application_id: string;
  status: 'DETAILS_REQUIRED' | 'SCHEDULED' | 'COMPLETED' | 'CANCELLED';
  visit_mode: 'ONLINE' | 'OFFLINE' | null;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  venue_or_meeting_details: string | null;
  official_schedule_reference: string | null;
  institution_contact_name: string | null;
  institution_contact_email: string | null;
  coordination_note: string | null;
  schedule_revision: number;
  report_reference: string | null;
  report_summary: string | null;
  report_outcome: 'NO_DEFICIENCY_RECORDED' | 'DEFICIENCIES_OBSERVED' | 'FOLLOW_UP_REQUIRED' | 'INCONCLUSIVE' | null;
  report_recorded_by: string | null;
  report_recorded_at: string | null;
  cancellation_reason: string | null;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SHCProceeding {
  shc_proceeding_id: string;
  workflow_case_id: string;
  application_id: string;
  status: 'PREPARATION' | 'SCHEDULED' | 'HEARING_RECORDED' | 'RECOMMENDATION_RECORDED';
  notice_reference: string | null;
  hearing_mode: 'ONLINE' | 'IN_PERSON' | null;
  hearing_scheduled_at: string | null;
  hearing_details: string | null;
  official_schedule_reference: string | null;
  schedule_revision: number;
  institution_submission_reference: string | null;
  representative_one_name: string | null;
  representative_one_designation: string | null;
  representative_two_name: string | null;
  representative_two_designation: string | null;
  hearing_summary: string | null;
  hearing_recorded_by: string | null;
  hearing_recorded_at: string | null;
  recommendation_code: 'COMPLIANCE_REVIEWED' | 'FURTHER_COMPLIANCE_REQUIRED' | 'DEFICIENCIES_REMAIN' | 'INCONCLUSIVE' | null;
  recommendation_text: string | null;
  recommendation_reference: string | null;
  recommendation_recorded_by: string | null;
  recommendation_recorded_at: string | null;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutiveCommitteeDecision {
  executive_committee_decision_id: string;
  workflow_case_id: string;
  application_id: string;
  outcome_code: 'APPROVED' | 'APPROVED_WITH_CONDITIONS' | 'REJECTED';
  decision_reference: string;
  decision_reasons: string;
  speaking_order_reference: string;
  speaking_order_uploaded_at: string;
  appeal_deadline_at: string;
  recorded_by: string;
  recorded_at: string;
  created_at: string;
}

export interface SACAppeal {
  sac_appeal_id: string;
  executive_committee_decision_id: string;
  workflow_case_id: string;
  application_id: string;
  shc_proceeding_id: string | null;
  status: 'FILED' | 'SCHEDULED' | 'HEARING_RECORDED' | 'RECOMMENDATION_RECORDED' | 'COUNCIL_DECISION_RECORDED';
  appeal_reference: string | null;
  appeal_grounds: string;
  supporting_material_reference: string;
  filed_by: string;
  filed_at: string;
  appeal_deadline_at: string;
  hearing_mode: 'ONLINE' | 'IN_PERSON' | null;
  hearing_scheduled_at: string | null;
  hearing_details: string | null;
  official_schedule_reference: string | null;
  schedule_revision: number;
  regulation_bureau_observation_reference: string | null;
  regulation_bureau_observations: string | null;
  bureau_observations_recorded_by: string | null;
  bureau_observations_recorded_at: string | null;
  representative_one_name: string | null;
  representative_one_designation: string | null;
  representative_one_id_reference: string | null;
  representative_one_id_self_attested: boolean | null;
  representative_two_name: string | null;
  representative_two_designation: string | null;
  representative_two_id_reference: string | null;
  representative_two_id_self_attested: boolean | null;
  hearing_summary: string | null;
  hearing_recorded_by: string | null;
  hearing_recorded_at: string | null;
  recommendation_code: 'RECOMMEND_TO_COUNCIL' | 'NOT_RECOMMEND_TO_COUNCIL' | 'FURTHER_REVIEW_REQUIRED' | null;
  recommendation_text: string | null;
  recommendation_reference: string | null;
  recommendation_recorded_by: string | null;
  recommendation_recorded_at: string | null;
  council_outcome_code: 'UPHOLD_EXECUTIVE_COMMITTEE' | 'SET_ASIDE_EXECUTIVE_COMMITTEE' | 'MODIFY_EXECUTIVE_COMMITTEE' | 'REMAND_FOR_RECONSIDERATION' | null;
  council_decision_reference: string | null;
  council_decision_text: string | null;
  council_decision_uploaded_at: string | null;
  council_decision_recorded_by: string | null;
  council_decision_recorded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends WorkflowCase {
  requirements: ApplicationRequirementItem[];
  events: WorkflowEvent[];
  obligations: ComplianceObligation[];
  evc_visit: EVCVisit | null;
  shc_proceeding: SHCProceeding | null;
  executive_committee_decision: ExecutiveCommitteeDecision | null;
  sac_appeal: SACAppeal | null;
}

export interface WorkflowReminderPolicy {
  reminder_policy_id: string;
  policy_code: string;
  target_type: 'WORKFLOW_CASE' | 'OBLIGATION';
  days_from_due: number;
  recipient_group: 'INSTITUTION' | 'ASSIGNEE' | 'SUPERVISORS';
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  title_template: string;
  body_template: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowNotification {
  notification_id: string;
  application_id: string | null;
  event_key: string;
  title: string;
  body: string;
  severity: string;
  read_at: string | null;
  created_at: string;
}

export const workflowApi = {
  cases: () => request<WorkflowCase[]>('/api/v1/workflow/cases'),
  detail: (id: string) => request<WorkflowDetail>(`/api/v1/workflow/cases/${id}`),
  transition: (id: string, to_stage: string, reason: string) =>
    request<WorkflowDetail>(`/api/v1/workflow/cases/${id}/transition`, {
      method: 'POST', body: JSON.stringify({ to_stage, reason }),
    }, true),
  assign: (id: string, review_team_id: string, note: string) =>
    request<WorkflowDetail>(`/api/v1/workflow/cases/${id}/assign`, {
      method: 'POST', body: JSON.stringify({ review_team_id, assigned_role_code: 'INTAKE_OFFICER', note }),
    }, true),
  fileSacAppeal: (caseId: string, payload: {
    appeal_reference?: string | null;
    appeal_grounds: string;
    supporting_material_reference: string;
  }) => request<SACAppeal>(`/api/v1/workflow/cases/${caseId}/sac-appeal`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  scheduleSacHearing: (appealId: string, payload: {
    hearing_mode: 'ONLINE' | 'IN_PERSON';
    hearing_scheduled_at: string;
    hearing_details: string;
    official_schedule_reference?: string | null;
  }) => request<SACAppeal>(`/api/v1/workflow/sac-appeals/${appealId}/schedule`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordSacBureauObservations: (appealId: string, payload: {
    observation_reference: string;
    observations: string;
  }) => request<SACAppeal>(`/api/v1/workflow/sac-appeals/${appealId}/bureau-observations`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordSacHearing: (appealId: string, payload: {
    representative_one_name: string;
    representative_one_designation: string;
    representative_one_id_reference: string;
    representative_one_id_self_attested: true;
    representative_two_name: string;
    representative_two_designation: string;
    representative_two_id_reference: string;
    representative_two_id_self_attested: true;
    hearing_summary: string;
  }) => request<SACAppeal>(`/api/v1/workflow/sac-appeals/${appealId}/hearing`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordSacRecommendation: (appealId: string, payload: {
    recommendation_code: 'RECOMMEND_TO_COUNCIL' | 'NOT_RECOMMEND_TO_COUNCIL' | 'FURTHER_REVIEW_REQUIRED';
    recommendation_text: string;
    recommendation_reference?: string | null;
  }) => request<SACAppeal>(`/api/v1/workflow/sac-appeals/${appealId}/recommendation`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordCouncilAppealDecision: (appealId: string, payload: {
    outcome_code: 'UPHOLD_EXECUTIVE_COMMITTEE' | 'SET_ASIDE_EXECUTIVE_COMMITTEE' | 'MODIFY_EXECUTIVE_COMMITTEE' | 'REMAND_FOR_RECONSIDERATION';
    decision_reference: string;
    decision_text: string;
    decision_uploaded_at: string;
  }) => request<SACAppeal>(`/api/v1/workflow/sac-appeals/${appealId}/council-decision`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordExecutiveCommitteeDecision: (caseId: string, payload: {
    outcome_code: 'APPROVED' | 'APPROVED_WITH_CONDITIONS' | 'REJECTED';
    decision_reference: string;
    decision_reasons: string;
    speaking_order_reference: string;
    speaking_order_uploaded_at: string;
  }) => request<WorkflowDetail>(`/api/v1/workflow/cases/${caseId}/executive-committee-decision`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  scheduleShcHearing: (caseId: string, payload: {
    hearing_mode: 'ONLINE' | 'IN_PERSON';
    hearing_scheduled_at: string;
    hearing_details: string;
    notice_reference?: string | null;
    official_schedule_reference?: string | null;
  }) => request<SHCProceeding>(`/api/v1/workflow/cases/${caseId}/shc-proceeding/schedule`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  submitShcCompliance: (proceedingId: string, payload: { submission_reference: string; note: string }) =>
    request<SHCProceeding>(`/api/v1/workflow/shc-proceedings/${proceedingId}/compliance-submission`, {
      method: 'POST', body: JSON.stringify(payload),
    }, true),
  recordShcHearing: (proceedingId: string, payload: {
    representative_one_name: string;
    representative_one_designation: string;
    representative_two_name: string;
    representative_two_designation: string;
    hearing_summary: string;
    note: string;
  }) => request<SHCProceeding>(`/api/v1/workflow/shc-proceedings/${proceedingId}/hearing`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordShcRecommendation: (proceedingId: string, payload: {
    recommendation_code: 'COMPLIANCE_REVIEWED' | 'FURTHER_COMPLIANCE_REQUIRED' | 'DEFICIENCIES_REMAIN' | 'INCONCLUSIVE';
    recommendation_text: string;
    recommendation_reference?: string | null;
  }) => request<SHCProceeding>(`/api/v1/workflow/shc-proceedings/${proceedingId}/recommendation`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  scheduleEvcVisit: (caseId: string, payload: {
    visit_mode: 'ONLINE' | 'OFFLINE';
    scheduled_start_at: string;
    scheduled_end_at?: string | null;
    venue_or_meeting_details: string;
    official_schedule_reference?: string | null;
    institution_contact_name?: string | null;
    institution_contact_email?: string | null;
    coordination_note: string;
  }) => request<EVCVisit>(`/api/v1/workflow/cases/${caseId}/evc-visit`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  recordEvcReport: (visitId: string, payload: {
    report_reference: string;
    report_summary: string;
    report_outcome: 'NO_DEFICIENCY_RECORDED' | 'DEFICIENCIES_OBSERVED' | 'FOLLOW_UP_REQUIRED' | 'INCONCLUSIVE';
    note: string;
  }) => request<EVCVisit>(`/api/v1/workflow/evc-visits/${visitId}/report`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  cancelEvcVisit: (visitId: string, reason: string) =>
    request<EVCVisit>(`/api/v1/workflow/evc-visits/${visitId}/cancel`, {
      method: 'POST', body: JSON.stringify({ reason }),
    }, true),
  event: (id: string, event_type: string, summary: string) =>
    request<WorkflowEvent>(`/api/v1/workflow/cases/${id}/events`, {
      method: 'POST', body: JSON.stringify({ event_type, summary, event_payload: {} }),
    }, true),
  createObligation: (id: string, payload: { title: string; description: string; source_condition: string; due_at: string }) =>
    request<ComplianceObligation>(`/api/v1/workflow/cases/${id}/obligations`, {
      method: 'POST', body: JSON.stringify(payload),
    }, true),
  obligationAction: (id: string, action: string, note: string, evidence_reference?: string, evidence_document_version_id?: string) =>
    request<ComplianceObligation>(`/api/v1/workflow/obligations/${id}`, {
      method: 'PATCH', body: JSON.stringify({ action, note, evidence_reference, evidence_document_version_id }),
    }, true),
  uploadObligationEvidence: async (obligationId: string, requirementId: string, file: File, note: string): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('note', note);
    return request<DocumentUploadResponse>(
      `/api/v1/workflow/obligations/${encodeURIComponent(obligationId)}/evidence/${encodeURIComponent(requirementId)}`,
      { method: 'POST', body: formData },
      true,
    );
  },
  getObligationEvidenceDownloadUrl: (obligationId: string) =>
    `/api/v1/workflow/obligations/${encodeURIComponent(obligationId)}/evidence/download`,
  reminderPolicies: () => request<WorkflowReminderPolicy[]>('/api/v1/workflow/reminder-policies'),
  updateReminderPolicy: (id: string, payload: {
    is_enabled?: boolean;
    days_from_due?: number;
    recipient_group?: 'INSTITUTION' | 'ASSIGNEE' | 'SUPERVISORS';
    severity?: 'INFO' | 'WARNING' | 'CRITICAL';
  }) => request<WorkflowReminderPolicy>(`/api/v1/workflow/reminder-policies/${id}`, {
    method: 'PATCH', body: JSON.stringify(payload),
  }, true),
  notifications: () => request<WorkflowNotification[]>('/api/v1/workflow/notifications'),
  markRead: (id: string) => request<WorkflowNotification>(`/api/v1/workflow/notifications/${id}/read`, { method: 'PATCH' }, true),
};
