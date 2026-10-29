import { createContext } from 'react';
import type { Role, RoleConfig } from '../types/roles';

export interface DemoRoleContextType {
  currentRole: Role;
  currentRoleConfig: RoleConfig;
  setRole: (role: Role, navigateToDefault?: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
}

export const DemoRoleContext = createContext<DemoRoleContextType | undefined>(undefined);
