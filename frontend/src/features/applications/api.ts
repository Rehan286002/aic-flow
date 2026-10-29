import { request } from '@/lib/api';
import type {
  ApplicationListItem,
  ApplicationDetail,
  ApplicationCreatePayload,
  ApplicationUpdatePayload,
} from '@/types/application';

export const applicationsApi = {
  /**
   * Fetch all applications for the specified institution.
   */
  async list(institutionId: string): Promise<ApplicationListItem[]> {
    return request<ApplicationListItem[]>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications`,
      { method: 'GET' }
    );
  },

  /**
   * Fetch full application detail including current revision declarations and 7 requirements.
   */
  async getDetail(
    institutionId: string,
    applicationId: string
  ): Promise<ApplicationDetail> {
    return request<ApplicationDetail>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications/${encodeURIComponent(applicationId)}`,
      { method: 'GET' }
    );
  },

  /**
   * Create an initial draft application and initialize 7 Annexure 2.1 requirements.
   * Requires CSRF token (automatically added by request for POST).
   */
  async createDraft(
    institutionId: string,
    payload: ApplicationCreatePayload
  ): Promise<ApplicationDetail> {
    return request<ApplicationDetail>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      true
    );
  },

  /**
   * Update self-disclosure declarations on an active draft revision.
   * Recalculates requirement applicability dynamically.
   * Requires CSRF token (automatically added by request for PATCH).
   */
  async updateDraft(
    institutionId: string,
    applicationId: string,
    payload: ApplicationUpdatePayload
  ): Promise<ApplicationDetail> {
    return request<ApplicationDetail>(
      `/api/v1/institutions/${encodeURIComponent(institutionId)}/applications/${encodeURIComponent(applicationId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
      true
    );
  },
};

