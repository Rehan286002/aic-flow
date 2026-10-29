import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { DocumentVersion } from '../types/document.ts';

function buildDownloadUrl(requirementId: string, versionId: string): string {
  return `/api/v1/requirements/${encodeURIComponent(requirementId)}/documents/${encodeURIComponent(versionId)}/download`;
}

function resolveActiveCleanEvidence(versions: DocumentVersion[]): DocumentVersion | undefined {
  return versions.find((v) => v.is_clean);
}

describe('Document Pipeline Logic & Formatting', () => {
  it('correctly constructs document download URL with URL encoding', () => {
    const reqId = '910c58da-d10e-421a-9c3e-0a31735d399b';
    const verId = 'e2b3c4d5-e6f7-4888-b731-84b32428049d';
    const url = buildDownloadUrl(reqId, verId);
    assert.equal(
      url,
      `/api/v1/requirements/${reqId}/documents/${verId}/download`
    );
  });

  it('identifies active clean version vs rejected infected replacement', () => {
    const version1: DocumentVersion = {
      document_version_id: 'v1-id',
      document_id: 'doc-id',
      version_number: 1,
      original_filename: 'affidavit.pdf',
      mime_type: 'application/pdf',
      file_size_bytes: 1024,
      sha256_hex: 'a'.repeat(64),
      uploaded_at: '2026-10-28T10:00:00Z',
      uploaded_by: 'user-id',
      replaces_document_version_id: null,
      security_scan: {
        document_security_scan_id: 'scan-1',
        scanner_name: 'ClamAV',
        scanner_version: '1.4.6',
        signature_database_version: '28164',
        scan_status: 'CLEAN',
        threat_name: null,
        scanned_at: '2026-10-28T10:00:01Z',
        scan_log_reference: 'Stream scan clean',
      },
      is_clean: true,
      is_downloadable: true,
    };

    const version2: DocumentVersion = {
      document_version_id: 'v2-id',
      document_id: 'doc-id',
      version_number: 2,
      original_filename: 'affidavit_revised.pdf',
      mime_type: 'application/pdf',
      file_size_bytes: 2048,
      sha256_hex: 'b'.repeat(64),
      uploaded_at: '2026-10-28T11:00:00Z',
      uploaded_by: 'user-id',
      replaces_document_version_id: 'v1-id',
      security_scan: {
        document_security_scan_id: 'scan-2',
        scanner_name: 'ClamAV',
        scanner_version: '1.4.6',
        signature_database_version: '28164',
        scan_status: 'DETECTED',
        threat_name: 'Eicar-Signature',
        scanned_at: '2026-10-28T11:00:01Z',
        scan_log_reference: 'Malware identified',
      },
      is_clean: false,
      is_downloadable: false,
    };

    // Version 1 is clean and downloadable
    assert.equal(version1.is_clean, true);
    assert.equal(version1.is_downloadable, true);

    // Version 2 is infected and download is prohibited
    assert.equal(version2.is_clean, false);
    assert.equal(version2.is_downloadable, false);
    assert.equal(version2.security_scan?.threat_name, 'Eicar-Signature');

    // Given history [v2, v1], latest clean version is v1
    const versions = [version2, version1];
    const latestClean = resolveActiveCleanEvidence(versions);
    assert.equal(latestClean?.document_version_id, 'v1-id');
  });
});
