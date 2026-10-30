import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useDemoRole } from '@/hooks/useDemoRole';
import { formatRoleContextLabel } from '@/types/auth';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { User, Shield, LogOut, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

export function UserMenu() {
  const navigate = useNavigate();
  const auth = useAuth();
  const { currentRoleConfig } = useDemoRole();

  const handleLogout = async () => {
    try {
      await auth.logout();
      toast.success('Signed Out', {
        description: 'You have signed out.',
      });
      navigate('/login', { replace: true });
    } catch {
      toast.error('Sign Out Error', {
        description: 'Your session has been cleared.',
      });
      navigate('/login', { replace: true });
    }
  };

  const handleViewSessionInfo = () => {
    const rolesSummary = auth.roles.map(formatRoleContextLabel).join(' | ');
    toast.info('Your account access', {
      description: `User: ${auth.user?.full_name || 'N/A'} • Available roles: ${rolesSummary || 'Standard'}`,
    });
  };

  const displayName = auth.user?.full_name || currentRoleConfig.userDisplayName;
  const email = auth.user?.email || 'authenticated@aic-flow.internal';
  const roleName = auth.activeContext
    ? formatRoleContextLabel(auth.activeContext)
    : currentRoleConfig.name;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="relative h-9 px-2 gap-2 rounded-lg hover:bg-slate-100 transition-colors focus-visible:ring-1"
          aria-label="User profile menu"
        >
          <Avatar className="size-7 bg-primary text-primary-foreground font-semibold text-xs border border-white shadow-xs">
            <AvatarFallback>{currentRoleConfig.avatarInitials}</AvatarFallback>
          </Avatar>

          <div className="hidden xl:flex flex-col text-left">
            <span className="text-xs font-semibold text-slate-800 leading-none">
              {displayName}
            </span>
            <span className="text-[10px] text-slate-500 leading-tight mt-0.5 truncate max-w-[120px]">
              {roleName}
            </span>
          </div>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-64 p-1.5 shadow-md border-slate-200">
        <DropdownMenuLabel className="font-normal px-2 py-2">
          <div className="flex items-center gap-2.5">
            <Avatar className="size-9 bg-primary text-primary-foreground font-semibold text-sm">
              <AvatarFallback>{currentRoleConfig.avatarInitials}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col space-y-0.5 overflow-hidden">
              <p className="text-xs font-semibold text-slate-900 truncate">
                {displayName}
              </p>
              <p className="text-[11px] text-slate-500 truncate font-mono">
                {email}
              </p>
              <p className="text-[10px] text-slate-400 truncate">
                {currentRoleConfig.organization}
              </p>
            </div>
          </div>
        </DropdownMenuLabel>

        <div className="px-2 py-1.5 bg-slate-50 rounded-md border border-slate-100 my-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-500 font-medium">Status:</span>
            <Badge variant="outline" className="text-[10px] h-4 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200">
              {auth.user?.status || 'Active'}
            </Badge>
          </div>
          <div className="flex items-center justify-between text-[11px] mt-1">
            <span className="text-slate-500 font-medium">Academic Year:</span>
            <span className="font-mono text-slate-700 text-[10px] font-semibold">2026-27</span>
          </div>
        </div>

        <DropdownMenuSeparator />

        <DropdownMenuGroup>
          <DropdownMenuItem onClick={handleViewSessionInfo} className="text-xs py-1.5 cursor-pointer">
            <User className="size-3.5 mr-2 text-slate-500" />
            <span>Profile & Access</span>
          </DropdownMenuItem>

          <DropdownMenuItem
            onClick={() => navigate(currentRoleConfig.defaultPath)}
            className="text-xs py-1.5 cursor-pointer"
          >
            <Shield className="size-3.5 mr-2 text-slate-500" />
            <span>My workspace</span>
          </DropdownMenuItem>
        </DropdownMenuGroup>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={() => window.open('https://www.aicte-india.org', '_blank')}
          className="text-xs py-1.5 cursor-pointer"
        >
          <ExternalLink className="size-3.5 mr-2 text-slate-500" />
          <span>AICTE Official Portal</span>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={handleLogout} className="text-xs py-1.5 text-rose-600 cursor-pointer focus:text-rose-600">
          <LogOut className="size-3.5 mr-2" />
          <span>Sign Out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
