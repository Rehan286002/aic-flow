import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PERMITTED_FINDING_TRANSITIONS,
  type FindingStatus,
  type ValidationResultRead,
  type ContradictionStatus,
} from '../features/validation/types.ts';

// Helper: Validate rationale whitespace constraint (minimum 5 non-whitespace characters)
export function validateReviewNote(note: string | null | undefined): { isValid: boolean; nonWsCount: number } {
  if (!note) {
    return { isValid: false, nonWsCount: 0 };
  }
  const nonWsCount = note.replace(/\s+/g, '').length;
  return { isValid: nonWsCount >= 5, nonWsCount };
}

// Helper: Check if a finding status transition is valid according to the authoritative state machine
export function isValidFindingTransition(current: FindingStatus, target: FindingStatus): boolean {
  if (current === target) return true;
  const permitted = PERMITTED_FINDING_TRANSITIONS[current] || [];
  return permitted.includes(target);
}

// Helper: Calculate dynamic validation summary metrics
export function computeValidationMetrics(results: ValidationResultRead[]) {
  return {
    total: results.length,
    satisfied: results.filter((r) => r.result_status === 'SATISFIED').length,
    deficient: results.filter((r) => r.result_status === 'DEFICIENT').length,
    unableToDetermine: results.filter((r) => r.result_status === 'UNABLE_TO_DETERMINE').length,
    notApplicable: results.filter((r) => r.result_status === 'NOT_APPLICABLE').length,
  };
}

// Helper: Derive contradiction status given declaration, OCR extraction, and external source values
export function evaluateContradictionStatus(params: {
  declared: string | null | undefined;
  ocrCandidate: string | null | undefined;
  sourceValue: string | null | undefined;
}): ContradictionStatus {
  const { declared, ocrCandidate, sourceValue } = params;

  const srcLower = (sourceValue || '').toLowerCase();
  if (
    !sourceValue ||
    srcLower.includes('not found') ||
    srcLower.includes('no active') ||
    srcLower.includes('no record') ||
    srcLower.includes('missing')
  ) {
    return 'ABSENT_IN_SOURCE';
  }

  if (!ocrCandidate || ocrCandidate.toLowerCase().includes('inconclusive') || ocrCandidate.toLowerCase().includes('unparsed')) {
    return 'UNVERIFIED';
  }

  if (declared && sourceValue && declared.trim() !== sourceValue.trim()) {
    return 'CONTRADICTION';
  }

  return 'MATCH';
}

test('Authoritative Finding State Machine: validates permitted and blocks invalid transitions', () => {
  // OPEN transitions
  assert.equal(isValidFindingTransition('OPEN', 'ACCEPTED'), true);
  assert.equal(isValidFindingTransition('OPEN', 'DISMISSED'), true);
  assert.equal(isValidFindingTransition('OPEN', 'CLARIFICATION_REQUESTED'), true);
  assert.equal(isValidFindingTransition('OPEN', 'ESCALATED'), true);
  assert.equal(isValidFindingTransition('OPEN', 'RESOLVED'), false); // Cannot jump straight to RESOLVED from OPEN

  // CLARIFICATION_REQUESTED transitions
  assert.equal(isValidFindingTransition('CLARIFICATION_REQUESTED', 'RESOLVED'), true);
  assert.equal(isValidFindingTransition('CLARIFICATION_REQUESTED', 'ACCEPTED'), true);
  assert.equal(isValidFindingTransition('CLARIFICATION_REQUESTED', 'DISMISSED'), true);
  assert.equal(isValidFindingTransition('CLARIFICATION_REQUESTED', 'ESCALATED'), true);
  assert.equal(isValidFindingTransition('CLARIFICATION_REQUESTED', 'OPEN'), false);

  // ESCALATED transitions
  assert.equal(isValidFindingTransition('ESCALATED', 'ACCEPTED'), true);
  assert.equal(isValidFindingTransition('ESCALATED', 'DISMISSED'), true);
  assert.equal(isValidFindingTransition('ESCALATED', 'RESOLVED'), true);
  assert.equal(isValidFindingTransition('ESCALATED', 'OPEN'), false);

  // ACCEPTED transitions
  assert.equal(isValidFindingTransition('ACCEPTED', 'RESOLVED'), true);
  assert.equal(isValidFindingTransition('ACCEPTED', 'ESCALATED'), true);
  assert.equal(isValidFindingTransition('ACCEPTED', 'DISMISSED'), false);

  // DISMISSED transitions (can re-open)
  assert.equal(isValidFindingTransition('DISMISSED', 'OPEN'), true);
  assert.equal(isValidFindingTransition('DISMISSED', 'RESOLVED'), false);

  // RESOLVED transitions (can re-open or escalate)
  assert.equal(isValidFindingTransition('RESOLVED', 'OPEN'), true);
  assert.equal(isValidFindingTransition('RESOLVED', 'ESCALATED'), true);
  assert.equal(isValidFindingTransition('RESOLVED', 'ACCEPTED'), false);

  // SUPERSEDED is strictly terminal
  assert.equal(isValidFindingTransition('SUPERSEDED', 'OPEN'), false);
  assert.equal(isValidFindingTransition('SUPERSEDED', 'RESOLVED'), false);
});

test('Auditor Review Rationale: enforces minimum 5 non-whitespace characters', () => {
  // Empty / Null
  assert.equal(validateReviewNote(null).isValid, false);
  assert.equal(validateReviewNote('').isValid, false);

  // Whitespace only
  assert.equal(validateReviewNote('     ').isValid, false);
  assert.equal(validateReviewNote(' \n\t  \r ').isValid, false);

  // Less than 5 non-whitespace characters
  assert.equal(validateReviewNote('a').isValid, false);
  assert.equal(validateReviewNote('  ab  ').isValid, false);
  assert.equal(validateReviewNote('1 2 3 4').isValid, false); // 4 non-ws chars

  // Exactly 5 non-whitespace characters
  const exactFive = validateReviewNote('1 2 3 4 5');
  assert.equal(exactFive.isValid, true);
  assert.equal(exactFive.nonWsCount, 5);

  // Normal valid rationale
  const validRationale = validateReviewNote('Building certificate missing in bundle.');
  assert.equal(validRationale.isValid, true);
  assert.ok(validRationale.nonWsCount > 20);
});

test('Validation Metrics: dynamically calculates breakdown without hardcoding', () => {
  const dummyResults: ValidationResultRead[] = [
    {
      validation_result_id: 'r1',
      validation_run_id: 'run-1',
      result_status: 'DEFICIENT',
      explanation: 'Deficient item 1',
      evaluated_at: new Date().toISOString(),
      findings: [],
    },
    {
      validation_result_id: 'r2',
      validation_run_id: 'run-1',
      result_status: 'DEFICIENT',
      explanation: 'Deficient item 2',
      evaluated_at: new Date().toISOString(),
      findings: [],
    },
    {
      validation_result_id: 'r3',
      validation_run_id: 'run-1',
      result_status: 'UNABLE_TO_DETERMINE',
      explanation: 'Inconclusive item',
      evaluated_at: new Date().toISOString(),
      findings: [],
    },
    {
      validation_result_id: 'r4',
      validation_run_id: 'run-1',
      result_status: 'SATISFIED',
      explanation: 'Satisfied item',
      evaluated_at: new Date().toISOString(),
      findings: [],
    },
    {
      validation_result_id: 'r5',
      validation_run_id: 'run-1',
      result_status: 'NOT_APPLICABLE',
      explanation: 'Exempt item',
      evaluated_at: new Date().toISOString(),
      findings: [],
    },
  ];

  const metrics = computeValidationMetrics(dummyResults);
  assert.equal(metrics.total, 5);
  assert.equal(metrics.satisfied, 1);
  assert.equal(metrics.deficient, 2);
  assert.equal(metrics.unableToDetermine, 1);
  assert.equal(metrics.notApplicable, 1);
});

test('Contradiction Status: identifies mismatch, absent in source, unverified, and match', () => {
  // Absent in source
  const absentStatus = evaluateContradictionStatus({
    declared: 'Valid NOC Claimed',
    ocrCandidate: 'Text found',
    sourceValue: 'No active NOC record found in Fire Directorate',
  });
  assert.equal(absentStatus, 'ABSENT_IN_SOURCE');

  // Unverified (low OCR / unparsed)
  const unverifiedStatus = evaluateContradictionStatus({
    declared: '28.6139° N, 77.2090° E',
    ocrCandidate: 'Text unparsed / inconclusive',
    sourceValue: 'Cadastral boundary verified at 28.6142° N',
  });
  assert.equal(unverifiedStatus, 'UNVERIFIED');

  // Contradiction (declared differs from source)
  const contradictionStatus = evaluateContradictionStatus({
    declared: 'Exemption Claimed',
    ocrCandidate: 'Exemption declaration text',
    sourceValue: 'Fee mandatory: No exemption order on file',
  });
  assert.equal(contradictionStatus, 'CONTRADICTION');

  // Match
  const matchStatus = evaluateContradictionStatus({
    declared: '₹100 E-Stamp Paper',
    ocrCandidate: '₹100 E-Stamp Paper',
    sourceValue: '₹100 E-Stamp Paper',
  });
  assert.equal(matchStatus, 'MATCH');
});
