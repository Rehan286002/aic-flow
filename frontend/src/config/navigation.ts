import {
  Activity,
  Bell,
  BookOpen,
  Building2,
  CalendarClock,
  CalendarDays,
  ClipboardCheck,
  ClipboardList,
  FileClock,
  FilePlus,
  FileText,
  Gavel,
  History,
  Landmark,
  Network,
  Search,
  Settings,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  Workflow,
} from 'lucide-react';
import type { Role } from '../types/roles';
import type { NavItem } from '../types/navigation';

const item = (title: string, path: string, icon: NavItem['icon'], description: string): NavItem => ({
  title, path, icon, description,
});

export const ROLE_NAVIGATION: Record<Role, NavItem[]> = {
  institution: [
    item('Overview', '/institution/overview', Building2, 'Applications and institutional compliance summary'),
    item('My Applications', '/institution/applications', FileText, 'View and track all authorised institution applications'),
    item('Create Application', '/institution/applications/new', FilePlus, 'Prepare a new approval application'),
    item('Clarifications', '/institution/rectification', ClipboardCheck, 'Respond to authorised deficiency requests'),
    item('Obligations', '/institution/obligations', ClipboardList, 'Submit evidence against approval conditions'),
    item('Documents & Renewals', '/institution/renewals', FileClock, 'Manage validity and replacement document records'),
    item('Notifications', '/institution/notifications', Bell, 'Review action requests and deadline alerts'),
    item('Application History', '/institution/activity', History, 'Review stage movement and communication history'),
    item('Document Centre', '/institution/documents', FileText, 'Upload, scan and inspect document versions'),
  ],
  auditor: [
    item('Office Overview', '/office', Activity, 'Intake and scrutiny work in the current team scope'),
    item('Intake Register', '/office/intake', ClipboardList, 'Review newly submitted cases and prepare routing'),
    item('Work Queue', '/office/queue', Workflow, 'Review cases assigned to the current processing role'),
    item('Scrutiny Workbench', '/office/scrutiny', Search, 'Inspect documents, requirements and evidence observations'),
    item('Clarifications', '/office/clarification', Bell, 'Track requests awaiting institutional response'),
    item('Re-scrutiny', '/office/re-scrutiny', ClipboardCheck, 'Review new revisions and resolve prior observations'),
    item('Case Dossiers', '/office/dossiers', FileText, 'Open route, documents, actions and audit history'),
    item('Reports', '/office/reports', FileClock, 'Export the current authorised processing workload'),
    item('Evidence Verification', '/auditor/dashboard', ShieldCheck, 'Existing AIC-Verify evidence review subsystem'),
  ],
  regional: [
    item('Regional Dashboard', '/regional', Activity, 'Regional processing and EVC status overview'),
    item('Regional Queue', '/regional/queue', ClipboardList, 'Review cases in the authorised regional team scope'),
    item('EVC Queue', '/regional/evc', CalendarClock, 'Coordinate route-eligible EVC tasks'),
    item('EVC Calendar', '/regional/calendar', CalendarDays, 'Review proposed and scheduled visits'),
    item('Overdue Work', '/regional/overdue', ShieldAlert, 'Review due dates and record supervisory actions'),
    item('Regional Reports', '/regional/reports', FileClock, 'Export the regional workload and EVC register'),
  ],
  committee: [
    item('Proceeding Dashboard', '/committee', Activity, 'View assigned proceeding activities'),
    item('Assigned Activities', '/committee/assigned', Landmark, 'Open only assigned EVC and proceeding work'),
    item('Schedule', '/committee/schedule', CalendarDays, 'Review visit or proceeding schedules'),
    item('Case Materials', '/committee/materials', BookOpen, 'Open permitted, version-specific case materials'),
    item('Observations & Reports', '/committee/observations', ClipboardCheck, 'Record observations and recommendations'),
    item('Completion', '/committee/completion', FileClock, 'Record completion and onward referral'),
  ],
  lead: [
    item('Bureau Control Tower', '/bureau', Activity, 'Review active cases within delegated oversight scope'),
    item('Regional Comparison', '/bureau/regions', Building2, 'Compare permitted team and regional work queues'),
    item('Officer Workload', '/bureau/workload', Users, 'Review case ownership and workload distribution'),
    item('Escalation Dossiers', '/bureau/escalations', ShieldAlert, 'Review overdue triggers and acknowledgements'),
    item('Decision Queue', '/bureau/decisions', Gavel, 'Competent authority docket when DECIDE is granted'),
    item('Compliance Oversight', '/bureau/obligations', ClipboardCheck, 'Monitor institutional conditions and evidence'),
    item('Analytics & Reports', '/bureau/analytics', FileClock, 'Export scoped processing and compliance reports'),
    item('Evidence Investigation', '/lead/overview', ShieldCheck, 'Existing AIC-Verify supervisory evidence tools'),
    item('Audit History', '/lead/audit-history', History, 'Review prior evidence and case audit history'),
  ],
  admin: [
    item('Administration Overview', '/admin/overview', Settings, 'Technical administration and operational health'),
    item('Users & Roles', '/admin/users', Users, 'Provision accounts and permission packages'),
    item('Review Teams', '/admin/teams', Network, 'Manage operational team membership'),
    item('Rule Configuration', '/admin/rules', SlidersHorizontal, 'Review configured validation rules'),
    item('Connectors', '/admin/connectors', Network, 'Inspect integration metadata and sandbox settings'),
    item('System Health', '/admin/health', Activity, 'Review platform services and health signals'),
    item('Operational Logs', '/admin/logs', FileText, 'Inspect technical events and errors'),
    item('Settings', '/admin/settings', Settings, 'Platform configuration'),
    item('Regulatory Sources', '/admin/policy/sources', BookOpen, 'Policy publisher source catalogue'),
    item('Route Simulator', '/admin/policy/route-simulator', Workflow, 'Preview configured category route profiles'),
    item('Deadline Policies', '/admin/policy/deadlines', CalendarClock, 'Review deadline class and source provenance'),
    item('Notification Policies', '/admin/policy/notifications', Bell, 'Review reminders, recipients and escalations'),
  ],
};

export function getRoleNavigation(workspace: Role, roleCode?: string): NavItem[] {
  const items = ROLE_NAVIGATION[workspace] || [];
  if (workspace === 'auditor' && roleCode === 'INTAKE_OFFICER') {
    return items.filter((entry) => ['/office', '/office/intake', '/office/queue', '/office/dossiers', '/office/reports'].includes(entry.path));
  }
  if (workspace === 'auditor' && roleCode === 'SCRUTINY_OFFICER') {
    return items.filter((entry) => entry.path !== '/office/intake');
  }
  if (workspace === 'regional' && roleCode === 'EVC_COORDINATOR') {
    return items.filter((entry) => ['/regional', '/regional/evc', '/regional/calendar', '/regional/overdue', '/regional/reports'].includes(entry.path));
  }
  if (workspace === 'committee' && roleCode === 'EVC_MEMBER') {
    return items.filter((entry) => !['/committee/observations'].includes(entry.path));
  }
  if (workspace === 'lead' && roleCode === 'COMPETENT_AUTHORITY') {
    return items.filter((entry) => ['/bureau', '/bureau/decisions', '/bureau/analytics'].includes(entry.path));
  }
  if (workspace === 'lead' && roleCode === 'BUREAU_SUPERVISOR') {
    return items.filter((entry) => entry.path !== '/bureau/decisions');
  }
  if (workspace === 'lead' && roleCode === 'LEAD_AUDITOR') {
    return items.filter((entry) => entry.path !== '/bureau/decisions');
  }
  if (workspace === 'admin' && roleCode === 'REGULATORY_POLICY_PUBLISHER') {
    return items.filter((entry) => entry.path.startsWith('/admin/policy/'));
  }
  if (workspace === 'admin' && roleCode === 'ADMIN') {
    return items.filter((entry) => !entry.path.startsWith('/admin/policy/'));
  }
  return items;
}
