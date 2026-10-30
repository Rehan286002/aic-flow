import { request } from '@/lib/api';
import type { ApplicationRequirementItem } from '@/types/application';

export interface WorkflowCase {
  workflow_case_id: string;
  application_id: string;
  application_number: string;
  institution_id: string;
  institution_name: string;
  review_team_id?: string | null;
  review_team_name?: string | null;
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
  actor_user_id: string | null;
  occurred_at: string;
}

export interface ComplianceObligation {
  obligation_id: string;
  workflow_case_id: string;
  application_id: string;
  title: string;
  description: string;
  source_condition: string;
  due_at: string;
  status: string;
  evidence_document_id: string | null;
  evidence_reference: string | null;
  verification_note: string | null;
}

export interface WorkflowDetail extends WorkflowCase {
  requirements: ApplicationRequirementItem[];
  events: WorkflowEvent[];
  obligations: ComplianceObligation[];
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


export interface DocumentValidityRecord {
  document_validity_id: string;
  workflow_case_id: string;
  application_id: string;
  institution_id: string;
  document_id: string;
  document_version_id: string;
  document_type: string;
  issuer: string;
  valid_from: string | null;
  valid_until: string;
  document_reference: string;
  verification_status: string;
  verification_note: string | null;
  replacement_of_id: string | null;
  created_by: string;
  verified_by: string | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
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
  event: (id: string, event_type: string, summary: string, event_payload: Record<string, unknown> = {}) =>
    request<WorkflowEvent>(`/api/v1/workflow/cases/${id}/events`, {
      method: 'POST', body: JSON.stringify({ event_type, summary, event_payload }),
    }, true),
  createObligation: (id: string, payload: { title: string; description: string; source_condition: string; due_at: string }) =>
    request<ComplianceObligation>(`/api/v1/workflow/cases/${id}/obligations`, {
      method: 'POST', body: JSON.stringify(payload),
    }, true),
  obligationAction: (id: string, action: string, note: string, evidence_reference?: string, evidence_document_id?: string) =>
    request<ComplianceObligation>(`/api/v1/workflow/obligations/${id}`, {
      method: 'PATCH', body: JSON.stringify({ action, note, evidence_reference, evidence_document_id }),
    }, true),
  obligations: () => request<ComplianceObligation[]>('/api/v1/workflow/obligations'),
  documentValidity: () => request<DocumentValidityRecord[]>('/api/v1/document-validity'),
  createDocumentValidity: (caseId: string, payload: {
    document_id: string;
    document_version_id: string;
    document_type: string;
    issuer: string;
    valid_from: string | null;
    valid_until: string;
    document_reference: string;
  }) => request<DocumentValidityRecord>(`/api/v1/document-validity/cases/${caseId}`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true),
  reviewDocumentValidity: (id: string, action: 'VERIFY' | 'RETURN', note: string) =>
    request<DocumentValidityRecord>(`/api/v1/document-validity/${id}`, {
      method: 'PATCH', body: JSON.stringify({ action, note }),
    }, true),
  notifications: () => request<WorkflowNotification[]>('/api/v1/workflow/notifications'),
  markRead: (id: string) => request<WorkflowNotification>(`/api/v1/workflow/notifications/${id}/read`, { method: 'PATCH' }, true),
};
