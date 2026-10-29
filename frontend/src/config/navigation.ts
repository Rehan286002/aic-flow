import { FilePlus, Workflow } from 'lucide-react';
import type { Role } from '../types/roles';
import type { NavItem } from '../types/navigation';

const workflowItem: NavItem = {
  title: 'Approval Workflow',
  path: '/workflow',
  icon: Workflow,
  description: 'Application routing, scrutiny, EVC, decisions, obligations and alerts',
};

export const ROLE_NAVIGATION: Record<Role, NavItem[]> = {
  institution: [
    workflowItem,
    {
      title: 'New Application',
      path: '/institution/applications/new',
      icon: FilePlus,
      description: 'Start an approval application for your authorised institution',
    },
  ],
  auditor: [workflowItem],
  lead: [workflowItem],
  admin: [workflowItem],
};
