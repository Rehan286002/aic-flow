import { request } from '@/lib/api';
import type {
  DocumentExtraction,
  DocumentExtractionTextResponse,
  DocumentHistoryResponse,
  DocumentProcessingJob,
  DocumentUploadResponse,
  ExtractedFieldReview,
  ExtractedFieldReviewCreate,
} from '@/types/document';

export const documentsApi = {
  /**
   * Upload an evidence document for an application requirement.
   * Performs multipart streaming, validation, ClamAV antivirus inspection,
   * SHA-256 calculation, and versioning.
   */
  async upload(
    requirementId: string,
    file: File
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return request<DocumentUploadResponse>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents`,
      {
        method: 'POST',
        body: formData,
      },
      true
    );
  },

  /**
   * Fetch full version history, security scans, and processing jobs for a requirement.
   */
  async getHistory(requirementId: string): Promise<DocumentHistoryResponse> {
    return request<DocumentHistoryResponse>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents`,
      { method: 'GET' }
    );
  },

  /**
   * Retry antivirus scan on a quarantined or failed document version.
   */
  async retryScan(
    requirementId: string,
    versionId: string
  ): Promise<DocumentUploadResponse> {
    return request<DocumentUploadResponse>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/retry-scan`,
      { method: 'POST' },
      true
    );
  },

  /**
   * Explicitly trigger OCR and structured content extraction for a clean document.
   * Returns HTTP 202 Accepted with authoritative job state.
   */
  async process(
    requirementId: string,
    versionId: string
  ): Promise<DocumentProcessingJob> {
    return request<DocumentProcessingJob>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/process`,
      { method: 'POST' },
      true
    );
  },

  /**
   * Fetch structured candidate fields and extraction metadata.
   */
  async getExtraction(
    requirementId: string,
    versionId: string
  ): Promise<DocumentExtraction> {
    return request<DocumentExtraction>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/extraction`,
      { method: 'GET' }
    );
  },

  /**
   * Fetch page-by-page extracted text for document inspection.
   */
  async getExtractionText(
    requirementId: string,
    versionId: string,
    page?: number
  ): Promise<DocumentExtractionTextResponse> {
    const query = page ? `?page=${encodeURIComponent(page)}` : '';
    return request<DocumentExtractionTextResponse>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/extraction/text${query}`,
      { method: 'GET' }
    );
  },

  /**
   * Build direct URL to stream/download verified clean document.
   */
  getDownloadUrl(requirementId: string, versionId: string): string {
    return `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/download`;
  },

  /**
   * Submit an authoritative regulatory review (acceptance or correction) for an extracted field.
   * Only AUDITOR and LEAD_AUDITOR roles can perform this action.
   */
  async createFieldReview(
    requirementId: string,
    versionId: string,
    fieldId: string,
    payload: ExtractedFieldReviewCreate
  ): Promise<ExtractedFieldReview> {
    return request<ExtractedFieldReview>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/fields/${encodeURIComponent(fieldId)}/reviews`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      },
      true
    );
  },

  /**
   * Fetch complete review history for an extracted field.
   */
  async getFieldReviews(
    requirementId: string,
    versionId: string,
    fieldId: string
  ): Promise<ExtractedFieldReview[]> {
    return request<ExtractedFieldReview[]>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/fields/${encodeURIComponent(fieldId)}/reviews`,
      { method: 'GET' }
    );
  },
};
