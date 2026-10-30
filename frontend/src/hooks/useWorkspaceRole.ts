import { useContext } from 'react';
import { WorkspaceRoleContext } from '@/context/workspace-role-context';

export function useWorkspaceRole() {
  const context = useContext(WorkspaceRoleContext);
  if (!context) {
    throw new Error('useWorkspaceRole must be used within a WorkspaceRoleProvider');
  }
  return context;
}
