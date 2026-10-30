import type { Role } from './roles';

export interface UserProfile {
  user_id: string;
  full_name: string;
  email: string;
  status: string;
}

export interface RoleContext {
  role_code:
    | 'INSTITUTION_USER'
    | 'INTAKE_OFFICER'
    | 'SCRUTINY_OFFICER'
    | 'REGIONAL_OFFICER'
    | 'EVC_COORDINATOR'
    | 'EVC_MEMBER'
    | 'COMMITTEE_SECRETARIAT'
    | 'BUREAU_SUPERVISOR'
    | 'COMPETENT_AUTHORITY'
    | 'REGULATORY_POLICY_PUBLISHER'
    | 'AUDITOR'
    | 'LEAD_AUDITOR'
    | 'ADMIN'
    | string;
  institution_id: string | null;
  review_team_id: string | null;
}

export interface CurrentUserResponse {
  user: UserProfile;
  roles: RoleContext[];
}

export interface LoginResponse {
  message: string;
  user: UserProfile;
}

export interface CSRFResponse {
  csrf_token: string;
}

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'error';

export function roleCodeToWorkspace(roleCode: string): Role | null {
  switch (roleCode) {
    case 'INSTITUTION_USER': return 'institution';
    case 'AUDITOR':
    case 'INTAKE_OFFICER':
    case 'SCRUTINY_OFFICER': return 'auditor';
    case 'REGIONAL_OFFICER':
    case 'EVC_COORDINATOR': return 'regional';
    case 'EVC_MEMBER':
    case 'COMMITTEE_SECRETARIAT': return 'committee';
    case 'LEAD_AUDITOR':
    case 'BUREAU_SUPERVISOR':
    case 'COMPETENT_AUTHORITY': return 'lead';
    case 'ADMIN':
    case 'REGULATORY_POLICY_PUBLISHER': return 'admin';
    default: return null;
  }
}

export function workspaceToRoleCode(role: Role): string {
  switch (role) {
    case 'institution': return 'INSTITUTION_USER';
    case 'auditor': return 'AUDITOR';
    case 'regional': return 'REGIONAL_OFFICER';
    case 'committee': return 'COMMITTEE_SECRETARIAT';
    case 'lead': return 'LEAD_AUDITOR';
    case 'admin': return 'ADMIN';
  }
}

export function getRoleContextKey(rc: RoleContext): string {
  return rc.role_code + ':' + (rc.institution_id || '') + ':' + (rc.review_team_id || '');
}

export function formatRoleContextLabel(rc: RoleContext): string {
  const teamSuffix = rc.review_team_id ? ' · Team ' + rc.review_team_id.slice(0, 8) : '';
  switch (rc.role_code) {
    case 'INSTITUTION_USER':
      return rc.institution_id ? 'Institution · ' + rc.institution_id.slice(0, 8) : 'Institution Representative';
    case 'INTAKE_OFFICER': return 'Intake / Registry Officer' + teamSuffix;
    case 'SCRUTINY_OFFICER':
    case 'AUDITOR': return 'Scrutiny / Processing Officer' + teamSuffix;
    case 'REGIONAL_OFFICER': return 'Regional Officer / Coordinator' + teamSuffix;
    case 'EVC_COORDINATOR': return 'EVC Coordinator' + teamSuffix;
    case 'EVC_MEMBER': return 'EVC Assigned Participant' + teamSuffix;
    case 'COMMITTEE_SECRETARIAT': return 'Committee Secretariat' + teamSuffix;
    case 'BUREAU_SUPERVISOR': return 'Bureau Supervisor' + teamSuffix;
    case 'COMPETENT_AUTHORITY': return 'Competent Authority' + teamSuffix;
    case 'LEAD_AUDITOR': return 'Senior / Lead Officer' + teamSuffix;
    case 'REGULATORY_POLICY_PUBLISHER': return 'Regulatory Policy Publisher / Approver';
    case 'ADMIN': return 'Platform Administrator';
    default: return rc.role_code;
  }
}
