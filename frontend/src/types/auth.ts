import type { Role } from './roles';

export interface UserProfile {
  user_id: string;
  full_name: string;
  email: string;
  status: string;
}

export interface RoleContext {
  role_code: 'INSTITUTION_USER' | 'AUDITOR' | 'LEAD_AUDITOR' | 'ADMIN' | string;
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
    case 'INSTITUTION_USER':
      return 'institution';
    case 'AUDITOR':
    case 'INTAKE_OFFICER':
    case 'SCRUTINY_OFFICER':
    case 'EVC_COORDINATOR':
    case 'EVC_MEMBER':
    case 'COMMITTEE_SECRETARIAT':
    case 'SAC_SECRETARIAT':
      return 'auditor';
    case 'LEAD_AUDITOR':
    case 'REGIONAL_OFFICER':
    case 'BUREAU_SUPERVISOR':
    case 'COMPETENT_AUTHORITY':
    case 'COUNCIL_SECRETARIAT':
      return 'lead';
    case 'ADMIN':
    case 'REGULATORY_POLICY_PUBLISHER':
      return 'admin';
    default:
      return null;
  }
}

export function workspaceToRoleCode(role: Role): string {
  switch (role) {
    case 'institution':
      return 'INSTITUTION_USER';
    case 'auditor':
      return 'AUDITOR';
    case 'lead':
      return 'LEAD_AUDITOR';
    case 'admin':
      return 'ADMIN';
  }
}

export function getRoleContextKey(rc: RoleContext): string {
  return `${rc.role_code}:${rc.institution_id || ''}:${rc.review_team_id || ''}`;
}

export function formatRoleContextLabel(rc: RoleContext): string {
  switch (rc.role_code) {
    case 'INSTITUTION_USER':
      return 'Institution Representative';
    case 'INTAKE_OFFICER':
      return 'Intake / Registry Officer';
    case 'SCRUTINY_OFFICER':
    case 'AUDITOR':
      return 'Scrutiny / Processing Officer';
    case 'REGIONAL_OFFICER':
      return 'Regional Officer / Coordinator';
    case 'EVC_COORDINATOR':
      return 'EVC Coordinator';
    case 'EVC_MEMBER':
      return 'EVC Assigned Participant';
    case 'COMMITTEE_SECRETARIAT':
      return 'Standing Hearing Committee Secretariat';
    case 'SAC_SECRETARIAT':
      return 'Standing Appellate Committee Secretariat';
    case 'COUNCIL_SECRETARIAT':
      return 'Council Secretariat';
    case 'BUREAU_SUPERVISOR':
      return 'Bureau Supervisor';
    case 'COMPETENT_AUTHORITY':
      return 'Competent Authority';
    case 'LEAD_AUDITOR':
      return 'Senior / Lead Officer';
    case 'REGULATORY_POLICY_PUBLISHER':
      return 'Regulatory Policy Publisher / Approver';
    case 'ADMIN':
      return 'Platform Administrator';
    default:
      return rc.role_code;
  }
}
