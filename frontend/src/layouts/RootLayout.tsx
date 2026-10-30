import { WorkspaceRoleProvider } from '@/context/WorkspaceRoleContext';
import { AppShell } from '@/components/layout/AppShell';

export function RootLayout() {
  return (
    <WorkspaceRoleProvider>
      <AppShell />
    </WorkspaceRoleProvider>
  );
}
