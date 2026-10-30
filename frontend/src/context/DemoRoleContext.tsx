import { useState, useMemo, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Role, RoleConfig } from '../types/roles';
import { ROLES } from '../types/roles';
import { roleCodeToWorkspace } from '../types/auth';
import { useAuth } from '@/hooks/useAuth';
import { DemoRoleContext } from './demo-role-context';

const SIDEBAR_STORAGE_KEY = 'aic_flow_sidebar_collapsed';

function getRoleFromPath(path: string): Role | null {
  if (path.startsWith('/institution')) return 'institution';
  if (path.startsWith('/office') || path.startsWith('/auditor')) return 'auditor';
  if (path.startsWith('/regional')) return 'regional';
  if (path.startsWith('/committee')) return 'committee';
  if (path.startsWith('/bureau') || path.startsWith('/lead')) return 'lead';
  if (path.startsWith('/admin')) return 'admin';
  return null;
}

function getInitials(name?: string): string {
  if (!name) return 'AV';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function DemoRoleProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const auth = useAuth();

  const [sidebarCollapsed, setSidebarCollapsedState] = useState<boolean>(() => {
    const saved = localStorage.getItem(SIDEBAR_STORAGE_KEY);
    return saved === 'true';
  });

  // Derive current role based on active route path or user's active backend context
  const roleFromPath = getRoleFromPath(location.pathname);
  const currentRole: Role = useMemo(() => {
    if (roleFromPath && auth.hasWorkspace(roleFromPath)) {
      return roleFromPath;
    }
    if (auth.activeWorkspace) {
      return auth.activeWorkspace;
    }
    return 'auditor';
  }, [roleFromPath, auth]);

  const setRole = (role: Role, navigateToDefault = true) => {
    // Only allow switching to a workspace if the user has an actual backend-verified role context
    const matchingContext = auth.roles.find(
      (r) => roleCodeToWorkspace(r.role_code) === role
    );
    if (matchingContext) {
      auth.switchContext(matchingContext);
      if (navigateToDefault) {
        navigate(ROLES[role].defaultPath);
      }
    } else {
      console.warn(`User does not have permission for workspace: ${role}`);
    }
  };

  const setSidebarCollapsed = (collapsed: boolean) => {
    setSidebarCollapsedState(collapsed);
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(collapsed));
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Build dynamic currentRoleConfig blending static labels with verified user profile & scope
  const currentRoleConfig: RoleConfig = useMemo(() => {
    const base = ROLES[currentRole];
    if (!auth.user) return base;

    let dynamicOrg = base.organization;
    if (auth.activeContext) {
      if (auth.activeContext.institution_id) {
        dynamicOrg = 'Institution account';
      } else if (auth.activeContext.review_team_id) {
        dynamicOrg = 'Assigned review team';
      }
    }

    return {
      ...base,
      userDisplayName: auth.user.full_name,
      avatarInitials: getInitials(auth.user.full_name),
      organization: dynamicOrg,
    };
  }, [currentRole, auth.user, auth.activeContext]);

  return (
    <DemoRoleContext.Provider
      value={{
        currentRole,
        currentRoleConfig,
        setRole,
        sidebarCollapsed,
        setSidebarCollapsed,
        toggleSidebar,
      }}
    >
      {children}
    </DemoRoleContext.Provider>
  );
}
