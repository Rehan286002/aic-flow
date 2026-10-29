import { createContext } from 'react';
import type { UserProfile, RoleContext, AuthStatus } from '@/types/auth';
import type { Role } from '@/types/roles';

export interface AuthContextType {
  status: AuthStatus;
  user: UserProfile | null;
  roles: RoleContext[];
  activeContext: RoleContext | null;
  activeWorkspace: Role | null;
  errorMessage: string | null;
  isNetworkError: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  switchContext: (context: RoleContext) => void;
  hasRole: (roleCode: string) => boolean;
  hasWorkspace: (workspace: Role) => boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
