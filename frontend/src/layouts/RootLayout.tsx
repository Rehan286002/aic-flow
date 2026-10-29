import { DemoRoleProvider } from '@/context/DemoRoleContext';
import { AppShell } from '@/components/layout/AppShell';

export function RootLayout() {
  return (
    <DemoRoleProvider>
      <AppShell />
    </DemoRoleProvider>
  );
}
