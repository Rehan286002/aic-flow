import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type {
  DocumentVersion,
  ExtractedField,
  DocumentExtractionTextResponse,
} from '../types/document.ts';

// Helper logic mirrored from component behavior
function canTriggerExtraction(ver: DocumentVersion): boolean {
  if (!ver.is_clean) return false;
  const status = ver.processing_job?.processing_status;
  return status === undefined || status === null || status === 'QUEUED' || status === 'FAILED';
}

function formatMatchingStrength(field: ExtractedField): string | null {
  const strength = field.matching_strength ?? field.confidence;
  if (strength === null || strength === undefined) return null;
  return `${Math.round(strength * 100)}%`;
}

function formatOcrConfidence(field: ExtractedField): string | null {
  if (field.ocr_confidence === null || field.ocr_confidence === undefined) {
    if (field.extraction_method === 'NATIVE_TEXT') return 'Native Text (100%)';
    return null;
  }
  return `OCR: ${Math.round(field.ocr_confidence * 100)}%`;
}

function formatBoundingBox(field: ExtractedField): string | null {
  if (!field.bounding_box) return null;
  const x = Math.round(field.bounding_box.x ?? 0);
  const y = Math.round(field.bounding_box.y ?? 0);
  const w = Math.round(field.bounding_box.width ?? 0);
  const h = Math.round(field.bounding_box.height ?? 0);
  return `Box: [x:${x}, y:${y}, w:${w}, h:${h}]`;
}

describe('Document Intelligence & Extraction Frontend Logic', () => {
  it('separates antivirus status from extraction status', () => {
    const cleanQueued: DocumentVersion = {
      document_version_id: 'v1',
      document_id: 'doc-1',
      version_number: 1,
      original_filename: 'fire_noc.pdf',
      mime_type: 'application/pdf',
      file_size_bytes: 51200,
      sha256_hex: 'a'.repeat(64),
      uploaded_at: '2026-10-28T10:00:00Z',
      uploaded_by: 'user-1',
      replaces_document_version_id: null,
      security_scan: {
        document_security_scan_id: 'scan-1',
        scanner_name: 'ClamAV',
        scanner_version: '1.4.6',
        signature_database_version: '28164',
        scan_status: 'CLEAN',
        threat_name: null,
        scanned_at: '2026-10-28T10:00:01Z',
        scan_log_reference: 'Clean stream scan',
      },
      processing_job: {
        document_processing_job_id: 'job-1',
        document_version_id: 'v1',
        processing_status: 'QUEUED',
        pipeline_name: 'DOCUMENT_INGESTION_V1',
        pipeline_version: '1.0.0',
        queued_at: '2026-10-28T10:00:02Z',
        started_at: null,
        completed_at: null,
        error_code: null,
        error_message: null,
      },
      is_clean: true,
      is_downloadable: true,
    };

    assert.equal(cleanQueued.security_scan?.scan_status, 'CLEAN');
    assert.equal(cleanQueued.processing_job?.processing_status, 'QUEUED');
    assert.equal(canTriggerExtraction(cleanQueued), true);
  });

  it('strictly blocks extraction triggering for infected documents', () => {
    const infectedDoc: DocumentVersion = {
      document_version_id: 'v2',
      document_id: 'doc-1',
      version_number: 2,
      original_filename: 'fire_noc_infected.pdf',
      mime_type: 'application/pdf',
      file_size_bytes: 1024,
      sha256_hex: 'b'.repeat(64),
      uploaded_at: '2026-10-28T11:00:00Z',
      uploaded_by: 'user-1',
      replaces_document_version_id: 'v1',
      security_scan: {
        document_security_scan_id: 'scan-2',
        scanner_name: 'ClamAV',
        scanner_version: '1.4.6',
        signature_database_version: '28164',
        scan_status: 'DETECTED',
        threat_name: 'Win.Test.EICAR_HDB-1',
        scanned_at: '2026-10-28T11:00:01Z',
        scan_log_reference: 'Malware detected',
      },
      processing_job: {
        document_processing_job_id: 'job-2',
        document_version_id: 'v2',
        processing_status: 'FAILED',
        pipeline_name: 'DOCUMENT_INGESTION_V1',
        pipeline_version: '1.0.0',
        queued_at: '2026-10-28T11:00:02Z',
        started_at: null,
        completed_at: null,
        error_code: 'MALWARE_DETECTED',
        error_message: 'Win.Test.EICAR_HDB-1',
      },
      is_clean: false,
      is_downloadable: false,
    };

    assert.equal(infectedDoc.is_clean, false);
    assert.equal(infectedDoc.is_downloadable, false);
    assert.equal(canTriggerExtraction(infectedDoc), false);
  });

  it('keeps OCR confidence distinct from pattern matching strength', () => {
    const field1: ExtractedField = {
      extracted_field_id: 'f-1',
      document_extraction_id: 'ext-1',
      field_code: 'noc_number',
      field_label: 'NOC / Certificate Number',
      raw_value: 'DFS/HQ/2026/8942',
      normalized_value: 'DFS/HQ/2026/8942',
      confidence: 0.95,
      page_number: 1,
      bounding_box: { x: 120.4, y: 340.2, width: 450.8, height: 28.1 },
      created_at: '2026-10-28T10:05:00Z',
      ocr_confidence: 0.985,
      matching_strength: 0.95,
      review_category: 'HIGH',
      source_snippet: 'Certificate No: DFS/HQ/2026/8942 dated 15-Jan-2026',
      extraction_method: 'OCR',
      notes: 'Matched regex pattern DFS/\\d{4}/\\d+',
    };

    assert.equal(formatMatchingStrength(field1), '95%');
    assert.equal(formatOcrConfidence(field1), 'OCR: 99%');
    assert.equal(formatBoundingBox(field1), 'Box: [x:120, y:340, w:451, h:28]');
    assert.equal(field1.review_category, 'HIGH');

    // Digital PDF native text field (no OCR confidence)
    const field2: ExtractedField = {
      ...field1,
      extracted_field_id: 'f-2',
      ocr_confidence: null,
      matching_strength: 0.88,
      extraction_method: 'NATIVE_TEXT',
    };

    assert.equal(formatMatchingStrength(field2), '88%');
    assert.equal(formatOcrConfidence(field2), 'Native Text (100%)');
  });

  it('safely handles missing candidate values without fabrication', () => {
    const missingField: ExtractedField = {
      extracted_field_id: 'f-3',
      document_extraction_id: 'ext-1',
      field_code: 'hazard_category',
      field_label: 'Hazard Category',
      raw_value: null,
      normalized_value: null,
      confidence: null,
      page_number: null,
      bounding_box: null,
      created_at: '2026-10-28T10:05:00Z',
      ocr_confidence: null,
      matching_strength: null,
      review_category: 'LOW_UNCERTAIN',
      source_snippet: null,
      extraction_method: null,
      notes: 'No hazard classification keywords identified on page 1',
    };

    assert.equal(missingField.raw_value, null);
    assert.equal(missingField.normalized_value, null);
    assert.equal(formatMatchingStrength(missingField), null);
    assert.equal(formatOcrConfidence(missingField), null);
    assert.equal(formatBoundingBox(missingField), null);
  });

  it('handles page-by-page text navigation and metrics calculation', () => {
    const textResponse: DocumentExtractionTextResponse = {
      document_version_id: 'v-1',
      document_extraction_id: 'ext-1',
      total_pages: 2,
      overall_method: 'HYBRID',
      selected_page: null,
      pages: [
        {
          page_number: 1,
          extraction_method: 'NATIVE_TEXT',
          page_text: 'DELHI FIRE SERVICES\nNO OBJECTION CERTIFICATE',
          char_count: 45,
          line_count: 2,
          ocr_line_count: 0,
        },
        {
          page_number: 2,
          extraction_method: 'OCR',
          page_text: 'Conditions of Certificate\n1. Building must maintain alarms.',
          char_count: 59,
          line_count: 2,
          ocr_line_count: 2,
        },
      ],
      full_text: 'DELHI FIRE SERVICES\nNO OBJECTION CERTIFICATE\n\nConditions of Certificate\n1. Building must maintain alarms.',
    };

    assert.equal(textResponse.total_pages, 2);
    assert.equal(textResponse.pages[0].extraction_method, 'NATIVE_TEXT');
    assert.equal(textResponse.pages[1].extraction_method, 'OCR');
    assert.equal(textResponse.pages[1].ocr_line_count, 2);
    assert.ok(textResponse.full_text?.includes('DELHI FIRE SERVICES'));
  });

  it('enforces review note whitespace constraints (minimum 5 non-whitespace chars)', () => {
    const countNonWs = (str: string) => str.replace(/\s/g, '').length;

    assert.equal(countNonWs('   \t\n  '), 0);
    assert.equal(countNonWs('   a b c d   '), 4);
    assert.equal(countNonWs('   a b c d e   '), 5);
    assert.equal(countNonWs('Correction justified by seal.'), 26);

    const isCorrectionValid = (note: string, val: string) =>
      val.trim().length > 0 && countNonWs(note) >= 5 && note.length <= 2000;

    assert.equal(isCorrectionValid('   \t  ', '123'), false);
    assert.equal(isCorrectionValid('abcd', '123'), false);
    assert.equal(isCorrectionValid('abcde', ''), false);
    assert.equal(isCorrectionValid('Valid official remark', '123'), true);
  });

  it('redacts confidential auditor identity and review notes from institution user view', () => {
    const auditorReview = {
      extracted_field_review_id: 'rev-1',
      extracted_field_id: 'f-1',
      reviewed_by: 'u-auditor-1',
      reviewer_name: 'Synthetic Auditor',
      reviewer_role: 'AUDITOR',
      accepted_as_extracted: false,
      corrected_value: 'NOC/CORRECTED/2026',
      review_note: 'CONFIDENTIAL: Internal auditor finding regarding stamp mismatch.',
      reviewed_at: '2026-10-28T12:00:00Z',
    };

    // Sanitize for institution user
    const sanitizeForInstitution = (rev: typeof auditorReview) => ({
      extracted_field_review_id: rev.extracted_field_review_id,
      extracted_field_id: rev.extracted_field_id,
      accepted_as_extracted: rev.accepted_as_extracted,
      has_correction: !rev.accepted_as_extracted,
      corrected_value: rev.corrected_value,
      reviewed_at: rev.reviewed_at,
    });

    const institutionProjection = sanitizeForInstitution(auditorReview);

    assert.equal(institutionProjection.has_correction, true);
    assert.equal(institutionProjection.corrected_value, 'NOC/CORRECTED/2026');
    assert.equal('review_note' in institutionProjection, false);
    assert.equal('reviewed_by' in institutionProjection, false);
    assert.equal('reviewer_name' in institutionProjection, false);
    assert.equal('reviewer_role' in institutionProjection, false);
  });
});

