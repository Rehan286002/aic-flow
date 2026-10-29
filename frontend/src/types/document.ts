export type ScanStatus = 'CLEAN' | 'DETECTED' | 'ERROR' | 'NOT_SCANNED';
export type ProcessingStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface DocumentSecurityScan {
  document_security_scan_id: string;
  scanner_name: string;
  scanner_version: string | null;
  signature_database_version: string | null;
  scan_status: ScanStatus;
  threat_name: string | null;
  scanned_at: string;
  scan_log_reference: string | null;
}

export interface DocumentProcessingJob {
  document_processing_job_id: string;
  document_version_id: string;
  processing_status: ProcessingStatus;
  pipeline_name: string;
  pipeline_version: string | null;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface DocumentVersion {
  document_version_id: string;
  document_id: string;
  version_number: number;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hex: string;
  uploaded_at: string;
  uploaded_by: string;
  replaces_document_version_id: string | null;
  security_scan: DocumentSecurityScan | null;
  processing_job: DocumentProcessingJob | null;
  is_clean: boolean;
  is_downloadable: boolean;
}

export interface DocumentUploadResponse {
  message: string;
  application_requirement_id: string;
  document_version: DocumentVersion;
  requirement_status: string;
  active_version_id: string | null;
}

export interface DocumentHistoryResponse {
  application_requirement_id: string;
  checklist_item_code: string;
  checklist_item_title: string;
  requirement_status: string;
  active_version_id: string | null;
  versions: DocumentVersion[];
}

export interface ExtractedField {
  extracted_field_id: string;
  document_extraction_id: string;
  field_code: string;
  field_label: string | null;
  raw_value: string | null;
  normalized_value: any | null;
  confidence: number | null;
  page_number: number | null;
  bounding_box: {
    x?: number;
    y?: number;
    width?: number;
    height?: number;
    [key: string]: any;
  } | null;
  created_at: string | null;
  ocr_confidence: number | null;
  matching_strength: number | null;
  review_category: 'HIGH' | 'MEDIUM_REVIEW' | 'LOW_UNCERTAIN' | string | null;
  source_snippet: string | null;
  extraction_method: 'NATIVE_TEXT' | 'OCR' | string | null;
  notes: string | null;
  latest_review?: ExtractedFieldReview | null;
}

export interface DocumentExtraction {
  document_extraction_id: string;
  document_version_id: string;
  processing_job_id: string | null;
  extraction_status: string;
  extraction_engine: string;
  engine_version: string | null;
  language_code: string | null;
  created_at: string;
  job: DocumentProcessingJob | null;
  fields: ExtractedField[];
}

export interface ExtractionTextPage {
  page_number: number;
  extraction_method: 'NATIVE_TEXT' | 'OCR' | string;
  page_text: string;
  char_count: number;
  line_count: number;
  ocr_line_count: number;
}

export interface DocumentExtractionTextResponse {
  document_version_id: string;
  document_extraction_id: string | null;
  total_pages: number;
  overall_method: string;
  selected_page: number | null;
  pages: ExtractionTextPage[];
  full_text: string | null;
}

export interface ExtractedFieldReviewCreate {
  accepted_as_extracted: boolean;
  corrected_value?: any;
  review_note?: string | null;
}

export interface ExtractedFieldReview {
  extracted_field_review_id: string;
  extracted_field_id: string;
  reviewed_by?: string;
  reviewer_name?: string;
  reviewer_role?: 'AUDITOR' | 'LEAD_AUDITOR' | string;
  accepted_as_extracted: boolean;
  has_correction?: boolean;
  corrected_value?: any;
  review_note?: string | null;
  reviewed_at: string;
}
