import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { ROLES } from '@/types/roles';
import { ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Lock,
  Mail,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  WifiOff,
} from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<
    'unauthorized' | 'inactive' | 'network' | 'server' | null
  >(null);

  // If already authenticated, redirect to destination or default workspace
  useEffect(() => {
    if (auth.status === 'authenticated' && auth.user) {
      const from = (location.state as { from?: { pathname: string } })?.from
        ?.pathname;
      const targetPath =
        from && from !== '/login'
          ? from
          : auth.activeWorkspace
            ? ROLES[auth.activeWorkspace].defaultPath
            : '/workflow';
      navigate(targetPath, { replace: true });
    }
  }, [auth.status, auth.user, auth.activeWorkspace, location.state, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!email.trim() || !password) {
      setErrorMessage('Please enter both email address and password.');
      setErrorType('unauthorized');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setErrorType(null);

    try {
      await auth.login(email.trim(), password);
      // Navigation will be handled by useEffect upon auth.status transition
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setErrorType('unauthorized');
          setErrorMessage(err.detail || 'Invalid email address or password.');
        } else if (err.status === 403) {
          setErrorType('inactive');
          setErrorMessage(
            err.detail || 'Your account is inactive. Contact platform administration.'
          );
        } else if (err.isNetworkError) {
          setErrorType('network');
          setErrorMessage(
            'Unable to reach authentication service. Verify backend is running.'
          );
        } else {
          setErrorType('server');
          setErrorMessage(
            err.detail || 'An unexpected AIC-Flow service error occurred.'
          );
        }
      } else {
        setErrorType('network');
        setErrorMessage('Network connection failure. Please check your network.');
      }
    } finally {
      // Security Requirement: Never retain password in state after attempt completes
      setPassword('');
      setIsSubmitting(false);
    }
  };



  return (
    <div className="min-h-screen w-full flex flex-col justify-center items-center bg-gradient-to-b from-slate-100 via-slate-50 to-slate-100 p-4 sm:p-6">
      {/* Platform Header */}
      <div className="flex flex-col items-center mb-6 text-center max-w-md">
        <div className="size-20 rounded-2xl bg-white flex items-center justify-center shadow-lg shadow-slate-200/80 mb-3 p-2 border border-slate-200/90">
          <img src="/aic-flow.svg" alt="AIC-Flow Platform Logo" className="size-full object-contain" />
        </div>
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-200/80 text-slate-700 text-[11px] font-semibold tracking-wide uppercase mb-1.5">
          <span>AICTE Approval Workflow & Compliance</span>
          <span className="size-1 rounded-full bg-slate-400" />
          <span>AY 2026-27</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          AIC-Flow Platform
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          AICTE approval workflow automation, compliance monitoring, document evidence
          management and operational alerts.
        </p>
      </div>

      {/* Main Login Card */}
      <Card className="w-full max-w-md shadow-xl border-slate-200/90 bg-white/95 backdrop-blur-xs">
        <CardHeader className="space-y-1 pb-4">
          <CardTitle className="text-lg font-bold text-slate-900">
            Sign In to Workspace
          </CardTitle>
          <CardDescription className="text-xs text-slate-500">
            Enter your institutional or regulatory credentials to continue.
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {/* Error Banners */}
            {errorMessage && (
              <div
                className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 transition-all ${
                  errorType === 'network'
                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                    : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}
                role="alert"
              >
                {errorType === 'network' ? (
                  <WifiOff className="size-4 shrink-0 mt-0.5 text-amber-600" />
                ) : (
                  <AlertCircle className="size-4 shrink-0 mt-0.5 text-rose-600" />
                )}
                <div className="space-y-0.5">
                  <p className="font-semibold">
                    {errorType === 'unauthorized' && 'Authentication Failed'}
                    {errorType === 'inactive' && 'Account Inactive'}
                    {errorType === 'network' && 'Connection Unavailable'}
                    {errorType === 'server' && 'Verification Service Error'}
                  </p>
                  <p className="text-[11px] leading-relaxed">{errorMessage}</p>
                </div>
              </div>
            )}

            {/* Email Field */}
            <div className="space-y-1.5">
              <Label htmlFor="login-email" className="text-xs font-semibold text-slate-700">
                Email
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400 pointer-events-none" />
                <Input
                  id="login-email"
                  type="email"
                  placeholder="name@aic-flow.internal"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  className="pl-9 h-10 text-xs bg-slate-50/50 border-slate-200 focus-visible:bg-white"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="login-password" className="text-xs font-semibold text-slate-700">
                  Password
                </Label>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400 pointer-events-none" />
                <Input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  className="pl-9 pr-10 h-10 text-xs bg-slate-50/50 border-slate-200 focus-visible:bg-white font-mono"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-hidden"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-3 pt-2">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-10 text-xs font-semibold bg-primary hover:bg-primary/95 text-primary-foreground shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 mr-2 animate-spin" />
                  Authenticating...
                </>
              ) : (
                'Sign In to Workspace'
              )}
            </Button>
          </CardFooter>
        </form>


      </Card>

      {/* Footer Info */}
      <div className="mt-8 text-center text-xs text-slate-400 space-y-1">
        <p>AICTE Approval Workflow and Compliance Platform</p>
        <p className="text-[11px] font-mono">Secure access for authorised users</p>
      </div>
    </div>
  );
}
