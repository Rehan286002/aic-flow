import type { ReactNode } from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { Role } from '@/types/roles';
import UnauthorizedPage from '@/pages/common/UnauthorizedPage';
import { WifiOff, RefreshCw, LogIn, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

interface ProtectedRouteProps {
  requiredRole?: string;
  requiredWorkspace?: Role;
  children?: ReactNode;
}

export function ProtectedRoute({
  requiredRole,
  requiredWorkspace,
  children,
}: ProtectedRouteProps) {
  const auth = useAuth();
  const location = useLocation();

  // 1. Loading state while checking session via /api/v1/auth/me
  if (auth.status === 'loading') {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-slate-50 p-4">
        <div className="flex flex-col items-center space-y-3">
          <div className="relative">
            <div className="size-12 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="size-2 rounded-full bg-primary animate-pulse" />
            </div>
          </div>
          <div className="text-center">
            <h3 className="text-sm font-semibold text-slate-800">AIC-Flow Platform</h3>
            <p className="text-xs text-slate-500 mt-0.5">Validating regulatory session credentials...</p>
          </div>
        </div>
      </div>
    );
  }

  // 2. Network error or server failure: do NOT simulate unauthenticated or create fake session
  if (auth.status === 'error') {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-md shadow-lg border-slate-200">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto size-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mb-3">
              {auth.isNetworkError ? (
                <WifiOff className="size-6 text-amber-600" />
              ) : (
                <AlertTriangle className="size-6 text-amber-600" />
              )}
            </div>
            <CardTitle className="text-lg font-bold text-slate-900">
              {auth.isNetworkError ? 'Connection Unavailable' : 'Authentication Service Error'}
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-1">
              {auth.isNetworkError
                ? 'Unable to communicate with the approval workflow backend service.'
                : 'The approval workflow platform returned an unexpected error response.'}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3 pt-2 text-xs text-slate-600">
            <div className="rounded-md bg-slate-100 p-3 font-mono text-[11px] text-slate-700 break-words border border-slate-200">
              {auth.errorMessage || 'Unknown service failure. Check backend service status.'}
            </div>
            <p className="leading-relaxed">
              Regulatory integrity rules require active approval workflow against the authority database.
              Cached or unverified access is strictly disallowed.
            </p>
          </CardContent>

          <CardFooter className="flex flex-col sm:flex-row gap-2 pt-2">
            <Button
              onClick={() => auth.refreshSession()}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold h-9"
            >
              <RefreshCw className="size-3.5 mr-1.5" />
              Retry Connection
            </Button>
            <Button
              variant="outline"
              asChild
              className="w-full sm:w-auto text-xs h-9 border-slate-200 text-slate-700 hover:bg-slate-100"
            >
              <a href="/login">
                <LogIn className="size-3.5 mr-1.5" />
                Sign In
              </a>
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // 3. Unauthenticated: Redirect to login with return state
  if (auth.status === 'unauthenticated' || !auth.user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 4. Authenticated: Validate required role or workspace scope
  if (requiredRole && !auth.hasRole(requiredRole)) {
    return <UnauthorizedPage />;
  }

  if (requiredWorkspace && !auth.hasWorkspace(requiredWorkspace)) {
    return <UnauthorizedPage />;
  }

  // 5. Authorized
  return children ? <>{children}</> : <Outlet />;
}
