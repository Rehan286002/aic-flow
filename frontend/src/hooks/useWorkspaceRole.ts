import { useContext } from 'react';
import { WorkspaceRoleContext } from '@/context/demo-role-context';

export function useWorkspaceRole() {
  const context = useContext(WorkspaceRoleContext);
  if (!context) {
    throw new Error('useWorkspaceRole must be used within a DemoRoleProvider');
  }
  return context;
}
