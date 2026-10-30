import test from 'node:test';
import assert from 'node:assert/strict';
import {
  countWorkflowCasesDueWithinSevenDays,
  filterWorkflowCases,
  isWorkflowCaseOverdue,
  type WorkflowQueueItem,
} from '../features/workflow/filters.ts';

const NOW = Date.parse('2026-10-30T10:00:00+05:30');
const caseItem = (
  current_stage: string,
  due_at: string | null,
  assigned_user_id: string | null,
): WorkflowQueueItem => ({ current_stage, due_at, assigned_user_id });

test('overdue filter excludes completed cases and respects the current clock', () => {
  const items = [
    caseItem('SCRUTINY', '2026-10-29T10:00:00+05:30', 'officer-1'),
    caseItem('APPROVED', '2026-10-29T10:00:00+05:30', 'officer-1'),
    caseItem('SCRUTINY', '2026-10-31T10:00:00+05:30', 'officer-1'),
    caseItem('SCRUTINY', null, 'officer-1'),
  ];
  assert.equal(isWorkflowCaseOverdue(items[0], NOW), true);
  assert.deepEqual(filterWorkflowCases(items, 'OVERDUE', NOW), [items[0]]);
});

test('due soon includes dates from now through seven days and excludes expired or closed cases', () => {
  const items = [
    caseItem('SCRUTINY', '2026-10-30T10:00:00+05:30', 'officer-1'),
    caseItem('SCRUTINY', '2026-11-06T10:00:00+05:30', 'officer-1'),
    caseItem('SCRUTINY', '2026-11-06T10:00:01+05:30', 'officer-1'),
    caseItem('SCRUTINY', '2026-10-29T10:00:00+05:30', 'officer-1'),
    caseItem('CLOSED', '2026-10-31T10:00:00+05:30', 'officer-1'),
  ];
  assert.equal(countWorkflowCasesDueWithinSevenDays(items, NOW), 2);
  assert.deepEqual(filterWorkflowCases(items, 'DUE_SOON', NOW), [items[0], items[1]]);
});

test('unassigned filter excludes closed records but preserves cases waiting for assignment', () => {
  const items = [
    caseItem('SUBMITTED', '2026-11-01T10:00:00+05:30', null),
    caseItem('SCRUTINY', null, 'officer-1'),
    caseItem('CLOSED', null, null),
  ];
  assert.deepEqual(filterWorkflowCases(items, 'UNASSIGNED', NOW), [items[0]]);
});

test('needs your response filter contains only institution-owned draft and clarification stages', () => {
  const items = [
    caseItem('DRAFT', null, null),
    caseItem('CLARIFICATION_REQUESTED', null, 'officer-1'),
    caseItem('RESUBMITTED', null, 'officer-1'),
    caseItem('SCRUTINY', null, 'officer-1'),
  ];
  assert.deepEqual(filterWorkflowCases(items, 'MY_ACTIONS', NOW), [items[0], items[1]]);
});

test('all filter returns all records without mutating the source array', () => {
  const items = [caseItem('SUBMITTED', null, null)];
  const result = filterWorkflowCases(items, 'ALL', NOW);
  assert.deepEqual(result, items);
  assert.notEqual(result, items);
});


test('notification links open the appropriate application page for each workspace', async () => {
  const { workflowApplicationLinkPath } = await import('../features/workflow/filters.ts');
  assert.equal(workflowApplicationLinkPath('institution'), '/institution/activity');
  assert.equal(workflowApplicationLinkPath('auditor'), '/office/dossiers');
  assert.equal(workflowApplicationLinkPath('regional'), '/regional/queue');
  assert.equal(workflowApplicationLinkPath('committee'), '/committee/assigned');
  assert.equal(workflowApplicationLinkPath('lead'), '/bureau');
  assert.equal(workflowApplicationLinkPath('admin'), '/admin/overview');
  assert.equal(workflowApplicationLinkPath('unknown'), '/');
});
