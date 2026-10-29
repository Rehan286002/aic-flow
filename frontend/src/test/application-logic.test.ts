import test from 'node:test';
import assert from 'node:assert/strict';
import type {
  ApplicationRequirementItem,
  ApplicabilityStatus,
} from '../types/application.ts';

// Helper for testing requirement counting logic
function computeChecklistMetrics(requirements: ApplicationRequirementItem[]) {
  return {
    total: requirements.length,
    applicable: requirements.filter((r) => r.applicability_status === 'APPLICABLE').length,
    notApplicable: requirements.filter((r) => r.applicability_status === 'NOT_APPLICABLE').length,
    pendingDet: requirements.filter((r) => r.applicability_status === 'PENDING_DETERMINATION').length,
    satisfied: requirements.filter((r) => r.status === 'SATISFIED').length,
  };
}

// Client-side date check helper reflecting Annexure 2.1 clause 4 boundary logic
function evaluateStructuralStabilityApplicability(
  completionDateStr: string | null | undefined,
  assessmentDateStr = '2026-07-01'
): ApplicabilityStatus {
  if (!completionDateStr || !completionDateStr.trim()) {
    return 'PENDING_DETERMINATION';
  }

  const completionDate = new Date(completionDateStr.trim());
  const assessmentDate = new Date(assessmentDateStr);

  // Exact 30-year cutoff date: 30 years prior to assessment date
  const cutoffDate = new Date(assessmentDate);
  cutoffDate.setFullYear(cutoffDate.getFullYear() - 30);

  // AICTE Annexure 2.1 rule: "when the building is more than 30 years from the issue of its Completion Certificate"
  // completionDate < cutoffDate means strictly older than 30 years -> APPLICABLE
  if (completionDate.getTime() < cutoffDate.getTime()) {
    return 'APPLICABLE';
  }
  // Exactly 30 years or less -> NOT_APPLICABLE
  return 'NOT_APPLICABLE';
}

test('computeChecklistMetrics aggregates requirements correctly', () => {
  const reqs: ApplicationRequirementItem[] = [
    {
      application_requirement_id: 'req-1',
      application_revision_id: 'rev-1',
      checklist_item_id: 'item-1',
      item_code: 'EOA-SD-01',
      title: 'Affidavit 2',
      description: 'Affidavit 2',
      expected_document_type_code: 'AFFIDAVIT_2',
      applicability_status: 'APPLICABLE',
      status: 'SATISFIED',
      determination_reason: 'Mandatory',
      last_evaluated_at: null,
      display_order: 1,
    },
    {
      application_requirement_id: 'req-2',
      application_revision_id: 'rev-1',
      checklist_item_id: 'item-2',
      item_code: 'EOA-SD-02',
      title: 'Payment Receipt',
      description: 'Copy of AICTE Web-Portal payment receipt, if any.',
      expected_document_type_code: 'PAYMENT_RECEIPT',
      applicability_status: 'PENDING_DETERMINATION',
      status: 'PENDING',
      determination_reason: 'Payment status not yet declared',
      last_evaluated_at: null,
      display_order: 2,
    },
    {
      application_requirement_id: 'req-4',
      application_revision_id: 'rev-1',
      checklist_item_id: 'item-4',
      item_code: 'EOA-SD-04',
      title: 'Structural Stability Certificate',
      description: 'Building stability certificate',
      expected_document_type_code: 'STRUCTURAL_STABILITY_CERTIFICATE',
      applicability_status: 'NOT_APPLICABLE',
      status: 'NOT_APPLICABLE',
      determination_reason: 'Building age does not exceed 30 years',
      last_evaluated_at: null,
      display_order: 4,
    },
  ];

  const metrics = computeChecklistMetrics(reqs);
  assert.equal(metrics.total, 3);
  assert.equal(metrics.applicable, 1);
  assert.equal(metrics.pendingDet, 1);
  assert.equal(metrics.notApplicable, 1);
  assert.equal(metrics.satisfied, 1);
});

test('evaluateStructuralStabilityApplicability enforces exact 30-year regulatory threshold', () => {
  // Assessment date: 2026-07-01
  // Exact 30 years prior: 1996-07-01
  // Rule: strictly MORE THAN 30 years

  // Case 1: More than 30 years (e.g., 1996-06-30 or 1990-05-15) -> APPLICABLE
  assert.equal(evaluateStructuralStabilityApplicability('1990-05-15'), 'APPLICABLE');
  assert.equal(evaluateStructuralStabilityApplicability('1996-06-30'), 'APPLICABLE');

  // Case 2: Exactly 30 years (1996-07-01) -> NOT_APPLICABLE (threshold is more than 30 years)
  assert.equal(evaluateStructuralStabilityApplicability('1996-07-01'), 'NOT_APPLICABLE');

  // Case 3: Less than 30 years (e.g., 1996-07-02 or 2008-01-10) -> NOT_APPLICABLE
  assert.equal(evaluateStructuralStabilityApplicability('1996-07-02'), 'NOT_APPLICABLE');
  assert.equal(evaluateStructuralStabilityApplicability('2008-01-10'), 'NOT_APPLICABLE');

  // Case 4: Missing or empty date -> PENDING_DETERMINATION
  assert.equal(evaluateStructuralStabilityApplicability(null), 'PENDING_DETERMINATION');
  assert.equal(evaluateStructuralStabilityApplicability(''), 'PENDING_DETERMINATION');
  assert.equal(evaluateStructuralStabilityApplicability('   '), 'PENDING_DETERMINATION');
});
