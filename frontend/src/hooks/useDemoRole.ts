import { useContext } from 'react';
import { DemoRoleContext } from '@/context/demo-role-context';

export function useDemoRole() {
  const context = useContext(DemoRoleContext);
  if (!context) {
    throw new Error('useDemoRole must be used within a DemoRoleProvider');
  }
  return context;
}
