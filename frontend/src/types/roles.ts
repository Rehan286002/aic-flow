export type Role = 'institution' | 'auditor' | 'regional' | 'committee' | 'lead' | 'admin';

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
    name: 'Institution Representative',
    label: 'Institution Portal',
    shortDescription: 'Applications, clarifications, conditions, documents and renewals for the authorised institution',
    defaultPath: '/institution/overview',
    userDisplayName: 'Institution User',
    userTitle: 'Authorised Representative',
    avatarInitials: 'IR',
    organization: 'Institution Workspace',
    badgeVariant: 'secondary',
  },
  auditor: {
    id: 'auditor',
    name: 'Processing Office',
    label: 'Processing Office',
    shortDescription: 'Registry intake, assigned scrutiny, clarification, re-scrutiny and case dossiers',
    defaultPath: '/office',
    userDisplayName: 'Processing Officer',
    userTitle: 'Intake / Scrutiny Officer',
    avatarInitials: 'PO',
    organization: 'Processing Office',
    badgeVariant: 'default',
  },
  regional: {
    id: 'regional',
    name: 'Regional Coordination',
    label: 'Regional Coordination',
    shortDescription: 'Regional queues, EVC scheduling, ageing, calendar and escalation follow-up',
    defaultPath: '/regional',
    userDisplayName: 'Regional Coordinator',
    userTitle: 'Regional Officer / EVC Coordinator',
    avatarInitials: 'RC',
    organization: 'Regional Workspace',
    badgeVariant: 'outline',
  },
  committee: {
    id: 'committee',
    name: 'Committee / Proceeding',
    label: 'Committee Workspace',
    shortDescription: 'Assigned EVC and distinct SHC / SAC proceeding schedules, materials and records',
    defaultPath: '/committee',
    userDisplayName: 'Proceeding Participant',
    userTitle: 'EVC Participant / Committee Secretariat',
    avatarInitials: 'CP',
    organization: 'Proceeding Workspace',
    badgeVariant: 'outline',
  },
  lead: {
    id: 'lead',
    name: 'Bureau / Senior Oversight',
    label: 'Bureau & Senior Oversight',
    shortDescription: 'Control tower, officer workload, overdue dossiers and competent-authority decision queue',
    defaultPath: '/bureau',
    userDisplayName: 'Senior Officer',
    userTitle: 'Bureau Supervisor / Competent Authority',
    avatarInitials: 'BS',
    organization: 'Bureau Workspace',
    badgeVariant: 'outline',
  },
  admin: {
    id: 'admin',
    name: 'Administration',
    label: 'Platform & Policy Administration',
    shortDescription: 'Technical operations or separate regulatory policy governance',
    defaultPath: '/admin/overview',
    userDisplayName: 'Platform Administrator',
    userTitle: 'Platform Administrator',
    avatarInitials: 'PA',
    organization: 'Administration Workspace',
    badgeVariant: 'outline',
  },
};
