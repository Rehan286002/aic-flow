export type Role = 'institution' | 'auditor' | 'lead' | 'admin';

export interface RoleConfig {
  id: Role;
  name: string;
  label: string;
  shortDescription: string;
  defaultPath: string;
  userDisplayName: string;
  userTitle: string;
  avatarInitials: string;
  organization: string;
  badgeVariant: 'default' | 'secondary' | 'outline';
}

export const ROLES: Record<Role, RoleConfig> = {
  institution: {
    id: 'institution',
    name: 'Institution User',
    label: 'Institution Portal',
    shortDescription: 'Applicant self-disclosure, document submission & compliance checklist',
    defaultPath: '/workflow',
    userDisplayName: 'Institution User',
    userTitle: 'Authorized Representative',
    avatarInitials: 'RS',
    organization: 'Institution Workspace',
    badgeVariant: 'secondary',
  },
  auditor: {
    id: 'auditor',
    name: 'Auditor',
    label: 'Auditor Verification Workspace',
    shortDescription: 'Document verification, discrepancy triage & finding review',
    defaultPath: '/workflow',
    userDisplayName: 'Processing Officer',
    userTitle: 'Senior Regulatory Auditor',
    avatarInitials: 'RV',
    organization: 'Regulatory Processing Workspace',
    badgeVariant: 'default',
  },
  lead: {
    id: 'lead',
    name: 'Lead Auditor',
    label: 'Lead Auditor Oversight',
    shortDescription: 'Escalation review, temporal compliance replay & final recommendations',
    defaultPath: '/workflow',
    userDisplayName: 'Senior Officer',
    userTitle: 'Lead Compliance Auditor',
    avatarInitials: 'SK',
    organization: 'Supervisory Workspace',
    badgeVariant: 'outline',
  },
  admin: {
    id: 'admin',
    name: 'Admin',
    label: 'System & Rule Administration',
    shortDescription: 'User management, rule configurations & simulated connector health',
    defaultPath: '/workflow',
    userDisplayName: 'Platform Administrator',
    userTitle: 'Platform Administrator',
    avatarInitials: 'VR',
    organization: 'Platform Operations',
    badgeVariant: 'outline',
  },
};
