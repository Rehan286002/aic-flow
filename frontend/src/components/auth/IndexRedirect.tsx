import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { ROLES } from '@/types/roles';
import { roleCodeToWorkspace } from '@/types/auth';

export function IndexRedirect() {
  const auth = useAuth();

  if (auth.status === 'loading') {
    return null;
  }

  if (auth.status === 'unauthenticated' || !auth.user) {
    return <Navigate to="/login" replace />;
  }

  if (auth.activeWorkspace && ROLES[auth.activeWorkspace]) {
    return <Navigate to={ROLES[auth.activeWorkspace].defaultPath} replace />;
  }

  if (auth.roles.length > 0) {
    const ws = roleCodeToWorkspace(auth.roles[0].role_code);
    if (ws && ROLES[ws]) {
      return <Navigate to={ROLES[ws].defaultPath} replace />;
    }
  }

  return <Navigate to="/login" replace />;
}
