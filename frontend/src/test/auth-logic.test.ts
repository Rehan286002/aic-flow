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

test('roleCodeToWorkspace maps all AIC-Flow permission packages to their workspace', () => {
  assert.equal(roleCodeToWorkspace('INSTITUTION_USER'), 'institution');
  assert.equal(roleCodeToWorkspace('AUDITOR'), 'auditor');
  for (const role of ['INTAKE_OFFICER', 'SCRUTINY_OFFICER', 'EVC_COORDINATOR', 'EVC_MEMBER', 'COMMITTEE_SECRETARIAT']) assert.equal(roleCodeToWorkspace(role), 'auditor');
  for (const role of ['REGIONAL_OFFICER', 'BUREAU_SUPERVISOR', 'COMPETENT_AUTHORITY', 'LEAD_AUDITOR']) assert.equal(roleCodeToWorkspace(role), 'lead');
  assert.equal(roleCodeToWorkspace('REGULATORY_POLICY_PUBLISHER'), 'admin');
  assert.equal(roleCodeToWorkspace('LEAD_AUDITOR'), 'lead');
  assert.equal(roleCodeToWorkspace('ADMIN'), 'admin');
  assert.equal(roleCodeToWorkspace('UNKNOWN_ROLE'), null);
});

test('workspaceToRoleCode maps workspaces to statutory role codes', () => {
  assert.equal(workspaceToRoleCode('institution'), 'INSTITUTION_USER');
  assert.equal(workspaceToRoleCode('auditor'), 'AUDITOR');
  assert.equal(workspaceToRoleCode('lead'), 'LEAD_AUDITOR');
  assert.equal(workspaceToRoleCode('admin'), 'ADMIN');
});

test('getRoleContextKey creates distinct keys preserving scope without deduplication', () => {
  const context1: RoleContext = {
    role_code: 'AUDITOR',
    institution_id: null,
    review_team_id: 'team-west-01',
  };
  const context2: RoleContext = {
    role_code: 'AUDITOR',
    institution_id: null,
    review_team_id: 'team-north-02',
  };
  const context3: RoleContext = {
    role_code: 'INSTITUTION_USER',
    institution_id: 'inst-synth-001',
    review_team_id: null,
  };

  const key1 = getRoleContextKey(context1);
  const key2 = getRoleContextKey(context2);
  const key3 = getRoleContextKey(context3);

  assert.equal(key1, 'AUDITOR::team-west-01');
  assert.equal(key2, 'AUDITOR::team-north-02');
  assert.equal(key3, 'INSTITUTION_USER:inst-synth-001:');

  // Verify that same role_code with different teams produces distinct keys
  assert.notEqual(key1, key2);
});

test('formatRoleContextLabel formats regulatory scope labels with truncated IDs', () => {
  const institutionContext: RoleContext = {
    role_code: 'INSTITUTION_USER',
    institution_id: 'SYNTH-AICTE-0001',
    review_team_id: null,
  };
  const teamContext: RoleContext = {
    role_code: 'AUDITOR',
    institution_id: null,
    review_team_id: 'TEAM-WEST-001',
  };
  const adminContext: RoleContext = {
    role_code: 'ADMIN',
    institution_id: null,
    review_team_id: null,
  };

  assert.equal(formatRoleContextLabel(institutionContext), 'Institution · SYNTH-AI');
  assert.equal(formatRoleContextLabel(teamContext), 'Scrutiny / Processing Officer · Team TEAM-WES');
  assert.equal(formatRoleContextLabel(adminContext), 'Platform Administrator');
});


test('formatRoleContextLabel preserves distinct PS 26262 permission package names', () => {
  const cases: Array<[string, string]> = [
    ['INTAKE_OFFICER', 'Intake / Registry Officer'],
    ['SCRUTINY_OFFICER', 'Scrutiny / Processing Officer'],
    ['REGIONAL_OFFICER', 'Regional Officer / Coordinator'],
    ['EVC_COORDINATOR', 'EVC Coordinator'],
    ['EVC_MEMBER', 'EVC Assigned Participant'],
    ['COMMITTEE_SECRETARIAT', 'Committee Secretariat'],
    ['BUREAU_SUPERVISOR', 'Bureau Supervisor'],
    ['COMPETENT_AUTHORITY', 'Competent Authority'],
    ['REGULATORY_POLICY_PUBLISHER', 'Regulatory Policy Publisher / Approver'],
  ];
  for (const [role_code, expected] of cases) {
    assert.equal(formatRoleContextLabel({ role_code, institution_id: null, review_team_id: null }), expected);
  }
});

test('ApiError correctly captures status, detail, and network error classification', () => {
  const networkErr = new ApiError(0, 'Failed to fetch', 'Connection refused', true);
  assert.equal(networkErr.status, 0);
  assert.equal(networkErr.isNetworkError, true);
  assert.equal(networkErr.detail, 'Connection refused');

  const authErr = new ApiError(401, 'Unauthorized', 'Invalid email or password', false);
  assert.equal(authErr.status, 401);
  assert.equal(authErr.isNetworkError, false);
  assert.equal(authErr.detail, 'Invalid email or password');

  const forbiddenErr = new ApiError(403, 'Forbidden', 'Account is inactive', false);
  assert.equal(forbiddenErr.status, 403);
  assert.equal(forbiddenErr.isNetworkError, false);
});

test('CSRF cache functions manage in-memory token correctly', () => {
  clearCachedCsrfToken();
  assert.equal(getCachedCsrfToken(), null);
});
