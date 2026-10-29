import { request } from '@/lib/api';
import type {
  FindingCategory,
  FindingRead,
  FindingSeverity,
  FindingStatus,
  FindingStatusUpdate,
  ValidationRunCreate,
  ValidationRunRead,
  ValidationRunSummary,
} from './types';

export interface ListFindingsParams {
  validation_run_id?: string;
  category?: FindingCategory;
  severity?: FindingSeverity;
  status?: FindingStatus;
  latest_run_only?: boolean;
}

export const validationApi = {
  /**
   * Fetch full validation run details including results, pinned versions, and findings.
   */
  async getValidationRun(
    institutionId: string,
    applicationId: string,
    validationRunId: string
  ): Promise<ValidationRunRead> {
    return request<ValidationRunRead>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications/${encodeURIComponent(
        applicationId
      )}/validation/runs/${encodeURIComponent(validationRunId)}`,
      { method: 'GET' }
    );
  },

  /**
   * List summary history of all validation runs executed for an application.
   */
  async listValidationRuns(
    institutionId: string,
    applicationId: string
  ): Promise<ValidationRunSummary[]> {
    return request<ValidationRunSummary[]>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications/${encodeURIComponent(
        applicationId
      )}/validation/runs`,
      { method: 'GET' }
    );
  },

  /**
   * List application findings with optional filtering. Sanitizes internal observations for institution users.
   */
  async listFindings(
    institutionId: string,
    applicationId: string,
    params?: ListFindingsParams
  ): Promise<FindingRead[]> {
    const query = new URLSearchParams();
    if (params?.validation_run_id) {
      query.set('validation_run_id', params.validation_run_id);
    }
    if (params?.category) {
      query.set('category', params.category);
    }
    if (params?.severity) {
      query.set('severity', params.severity);
    }
    if (params?.status) {
      query.set('status', params.status);
    }
    if (params?.latest_run_only) {
      query.set('latest_run_only', 'true');
    }

    const qs = query.toString();
    const endpoint = `/api/v1/institutions/${encodeURIComponent(
      institutionId
    )}/applications/${encodeURIComponent(applicationId)}/validation/findings${qs ? `?${qs}` : ''}`;

    return request<FindingRead[]>(endpoint, { method: 'GET' });
  },

  /**
   * Trigger a new deterministic validation run for the application revision.
   * Requires CSRF token.
   */
  async triggerValidationRun(
    institutionId: string,
    applicationId: string,
    payload: ValidationRunCreate = { run_type: 'FULL' }
  ): Promise<ValidationRunRead> {
    return request<ValidationRunRead>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications/${encodeURIComponent(
        applicationId
      )}/validation/runs`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      true
    );
  },

  /**
   * Update finding review status with mandatory auditor rationale and audit trail.
   * NOTE: The historical Apex reference run (5822d8f2...) is strictly read-only and
   * must NOT be mutated via this endpoint.
   * Requires CSRF token.
   */
  async updateFindingStatus(
    institutionId: string,
    applicationId: string,
    findingId: string,
    payload: FindingStatusUpdate
  ): Promise<FindingRead> {
    return request<FindingRead>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications/${encodeURIComponent(
        applicationId
      )}/validation/findings/${encodeURIComponent(findingId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
      true
    );
  },
};

