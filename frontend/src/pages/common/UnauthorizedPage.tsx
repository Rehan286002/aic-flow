import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { ROLES } from '@/types/roles';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldAlert, ArrowLeft, LogOut } from 'lucide-react';

export default function UnauthorizedPage() {
  const navigate = useNavigate();
  const auth = useAuth();

  const handleReturnToWorkspace = () => {
    if (auth.activeWorkspace && ROLES[auth.activeWorkspace]) {
      navigate(ROLES[auth.activeWorkspace].defaultPath, { replace: true });
    } else {
      navigate('/login', { replace: true });
    }
  };

  const handleLogout = async () => {
    await auth.logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md shadow-lg border-slate-200">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto size-12 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mb-3">
            <ShieldAlert className="size-6 text-rose-600" />
          </div>
          <CardTitle className="text-xl font-bold text-slate-900 tracking-tight">
            Access Restricted
          </CardTitle>
          <CardDescription className="text-sm text-slate-500 mt-1">
            Your authenticated role scope does not authorize access to this regulatory workspace.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 pt-2">
          <div className="rounded-lg bg-slate-100/80 p-3.5 border border-slate-200/80 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Signed in as:</span>
              <span className="font-semibold text-slate-900">{auth.user?.full_name || 'Authenticated User'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Email:</span>
              <span className="font-mono text-slate-700">{auth.user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Assigned Scopes:</span>
              <span className="font-medium text-slate-800">
                {auth.roles.map((r) => r.role_code).join(', ') || 'None'}
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed text-center">
            Under AICTE verification governance, regulatory portals enforce strict multi-tenant isolation.
            If you require access to this section, contact your designated Lead Auditor or Platform Administrator.
          </p>
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row gap-2 pt-2">
          <Button
            onClick={handleReturnToWorkspace}
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold h-9"
          >
            <ArrowLeft className="size-3.5 mr-1.5" />
            Return to Authorized Workspace
          </Button>
          <Button
            variant="outline"
            onClick={handleLogout}
            className="w-full sm:w-auto text-xs h-9 border-slate-200 text-slate-700 hover:bg-slate-100"
          >
            <LogOut className="size-3.5 mr-1.5" />
            Sign Out
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
