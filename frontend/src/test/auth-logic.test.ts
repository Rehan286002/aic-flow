import test from 'node:test';
import assert from 'node:assert/strict';
import {
  roleCodeToWorkspace,
  workspaceToRoleCode,
  getRoleContextKey,
  formatRoleContextLabel,
  type RoleContext,
} from '../types/auth.ts';
import { ApiError, getCachedCsrfToken, clearCachedCsrfToken } from '../lib/api.ts';

test('each PS 26262 permission package maps to the correct workspace', () => {
  const cases: Array<[string, string | null]> = [
    ['INSTITUTION_USER', 'institution'],
    ['INTAKE_OFFICER', 'auditor'],
    ['SCRUTINY_OFFICER', 'auditor'],
    ['AUDITOR', 'auditor'],
    ['REGIONAL_OFFICER', 'regional'],
    ['EVC_COORDINATOR', 'regional'],
    ['EVC_MEMBER', 'committee'],
    ['COMMITTEE_SECRETARIAT', 'committee'],
    ['BUREAU_SUPERVISOR', 'lead'],
    ['COMPETENT_AUTHORITY', 'lead'],
    ['LEAD_AUDITOR', 'lead'],
    ['ADMIN', 'admin'],
    ['REGULATORY_POLICY_PUBLISHER', 'admin'],
    ['UNKNOWN_ROLE', null],
  ];
  for (const [role, workspace] of cases) assert.equal(roleCodeToWorkspace(role), workspace);
});

test('workspace defaults and role labels are explicit', () => {
  const defaults: Array<[RoleContext['role_code'], string]> = [
    ['INSTITUTION_USER', 'Institution Representative'],
    ['INTAKE_OFFICER', 'Intake / Registry Officer'],
    ['SCRUTINY_OFFICER', 'Scrutiny / Processing Officer'],
    ['REGIONAL_OFFICER', 'Regional Officer / Coordinator'],
    ['EVC_COORDINATOR', 'EVC Coordinator'],
    ['EVC_MEMBER', 'EVC Assigned Participant'],
    ['COMMITTEE_SECRETARIAT', 'Committee Secretariat'],
    ['BUREAU_SUPERVISOR', 'Bureau Supervisor'],
    ['COMPETENT_AUTHORITY', 'Competent Authority'],
    ['REGULATORY_POLICY_PUBLISHER', 'Regulatory Policy Publisher / Approver'],
    ['ADMIN', 'Platform Administrator'],
  ];
  for (const [role_code, expected] of defaults) {
    assert.equal(formatRoleContextLabel({ role_code, institution_id: null, review_team_id: null }), expected);
  }
});

test('workspace default role mapping covers all workspaces', () => {
  assert.equal(workspaceToRoleCode('institution'), 'INSTITUTION_USER');
  assert.equal(workspaceToRoleCode('auditor'), 'AUDITOR');
  assert.equal(workspaceToRoleCode('regional'), 'REGIONAL_OFFICER');
  assert.equal(workspaceToRoleCode('committee'), 'COMMITTEE_SECRETARIAT');
  assert.equal(workspaceToRoleCode('lead'), 'LEAD_AUDITOR');
  assert.equal(workspaceToRoleCode('admin'), 'ADMIN');
});

test('role context keys preserve distinct role and team scopes', () => {
  const a: RoleContext = { role_code: 'AUDITOR', institution_id: null, review_team_id: 'team-a' };
  const b: RoleContext = { role_code: 'AUDITOR', institution_id: null, review_team_id: 'team-b' };
  assert.notEqual(getRoleContextKey(a), getRoleContextKey(b));
  assert.equal(getRoleContextKey(a), 'AUDITOR::team-a');
});

test('ApiError captures HTTP and network failure information', () => {
  const network = new ApiError(0, 'Failed to fetch', 'Connection refused', true);
  assert.equal(network.status, 0);
  assert.equal(network.isNetworkError, true);
  assert.equal(network.detail, 'Connection refused');
  const forbidden = new ApiError(403, 'Forbidden', 'Not allowed', false);
  assert.equal(forbidden.status, 403);
  assert.equal(forbidden.isNetworkError, false);
});

test('CSRF cache functions manage their in-memory token', () => {
  clearCachedCsrfToken();
  assert.equal(getCachedCsrfToken(), null);
});
