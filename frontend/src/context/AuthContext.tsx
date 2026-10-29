import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import type { UserProfile, RoleContext, AuthStatus } from '@/types/auth';
import {
  roleCodeToWorkspace,
  getRoleContextKey,
} from '@/types/auth';
import type { Role } from '@/types/roles';
import { api, ApiError } from '@/lib/api';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [roles, setRoles] = useState<RoleContext[]>([]);
  const [activeContext, setActiveContext] = useState<RoleContext | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isNetworkError, setIsNetworkError] = useState(false);

  const fetchSession = useCallback(async () => {
    try {
      const data = await api.auth.me();
      setUser(data.user);
      // Preserve all backend role contexts verbatim (never deduplicate by role_code)
      setRoles(data.roles);

      if (data.roles.length > 0) {
        // Select first valid context or preserve previous if still valid
        setActiveContext((prev) => {
          if (prev && data.roles.some((r) => getRoleContextKey(r) === getRoleContextKey(prev))) {
            return prev;
          }
          return data.roles[0];
        });
      } else {
        setActiveContext(null);
      }

      setStatus('authenticated');
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          // Normal unauthenticated state (not logged in or session expired)
          setUser(null);
          setRoles([]);
          setActiveContext(null);
          setStatus('unauthenticated');
        } else if (error.isNetworkError) {
          // Backend offline or network failure: do NOT mark unauthenticated
          setStatus('error');
          setIsNetworkError(true);
          setErrorMessage(error.message);
        } else {
          // Server error or unexpected status
          setStatus('error');
          setIsNetworkError(false);
          setErrorMessage(error.detail || error.message);
        }
      } else {
        setStatus('error');
        setIsNetworkError(true);
        setErrorMessage('Failed to connect to verification services.');
      }
    }
  }, []);

  const refreshSession = useCallback(async () => {
    setStatus('loading');
    setErrorMessage(null);
    setIsNetworkError(false);
    await fetchSession();
  }, [fetchSession]);

  useEffect(() => {
    void fetchSession();
  }, [fetchSession]);

  const login = useCallback(
    async (email: string, password: string): Promise<void> => {
      setErrorMessage(null);
      setIsNetworkError(false);

      try {
        await api.auth.login(email, password);
        // After successful login, restore full user profile and role contexts
        const data = await api.auth.me();
        setUser(data.user);
        setRoles(data.roles);

        if (data.roles.length > 0) {
          setActiveContext(data.roles[0]);
        } else {
          setActiveContext(null);
        }

        setStatus('authenticated');
      } catch (error) {
        if (error instanceof ApiError) {
          setIsNetworkError(error.isNetworkError);
          setErrorMessage(error.detail || error.message);
        } else {
          setIsNetworkError(true);
          setErrorMessage('Unable to reach authentication server.');
        }
        throw error;
      }
    },
    []
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await api.auth.logout();
    } catch (error) {
      console.warn('Logout notification to backend failed:', error);
    } finally {
      // Always clear client-side session state
      setUser(null);
      setRoles([]);
      setActiveContext(null);
      setStatus('unauthenticated');
      setErrorMessage(null);
      setIsNetworkError(false);
    }
  }, []);

  const switchContext = useCallback(
    (targetContext: RoleContext) => {
      // Strict safety: Only allow switching to a context actually present in backend-returned roles
      const targetKey = getRoleContextKey(targetContext);
      const match = roles.find((r) => getRoleContextKey(r) === targetKey);
      if (match) {
        setActiveContext(match);
      } else {
        console.error('Attempted to switch to unauthorized role context:', targetContext);
      }
    },
    [roles]
  );

  const activeWorkspace: Role | null = useMemo(() => {
    if (!activeContext) return null;
    return roleCodeToWorkspace(activeContext.role_code);
  }, [activeContext]);

  const hasRole = useCallback(
    (roleCode: string): boolean => {
      return roles.some((r) => r.role_code === roleCode);
    },
    [roles]
  );

  const hasWorkspace = useCallback(
    (workspace: Role): boolean => {
      return roles.some((r) => roleCodeToWorkspace(r.role_code) === workspace);
    },
    [roles]
  );

  const value = useMemo(
    () => ({
      status,
      user,
      roles,
      activeContext,
      activeWorkspace,
      errorMessage,
      isNetworkError,
      login,
      logout,
      refreshSession,
      switchContext,
      hasRole,
      hasWorkspace,
    }),
    [
      status,
      user,
      roles,
      activeContext,
      activeWorkspace,
      errorMessage,
      isNetworkError,
      login,
      logout,
      refreshSession,
      switchContext,
      hasRole,
      hasWorkspace,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
