import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { Role } from '@/types/roles';
import { ROLES } from '@/types/roles';
import {
  roleCodeToWorkspace,
  getRoleContextKey,
  formatRoleContextLabel,
} from '@/types/auth';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  UserCheck,
  ShieldAlert,
  Building2,
  UserCog,
  Info,
  Lock,
  CalendarDays,
  Landmark,
} from 'lucide-react';
import { toast } from 'sonner';

const ROLE_ICONS: Record<Role, React.ComponentType<{ className?: string }>> = {
  institution: Building2,
  auditor: UserCheck,
  regional: CalendarDays,
  committee: Landmark,
  lead: ShieldAlert,
  admin: UserCog,
};

export function DemoRoleSelector() {
  const navigate = useNavigate();
  const auth = useAuth();

  const activeContext = auth.activeContext;
  const activeWorkspace = auth.activeWorkspace || 'auditor';
  const CurrentIcon = ROLE_ICONS[activeWorkspace] || UserCheck;

  // Single assigned role scenario: render locked badge (no dropdown)
  if (auth.roles.length <= 1) {
    const contextLabel = activeContext
      ? formatRoleContextLabel(activeContext)
      : ROLES[activeWorkspace]?.name || 'Standard Access';

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200/80 rounded-lg py-1 px-2.5">
            <CurrentIcon className="size-3.5 text-primary" />
            <span className="text-xs font-semibold text-slate-800">
              {contextLabel}
            </span>
            <Lock className="size-3 text-slate-400 ml-0.5" />
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="end" className="max-w-xs text-xs p-3">
          <p className="font-medium text-white mb-1">Assigned Scope</p>
          <p className="text-slate-300 leading-relaxed text-[11px]">
            Your account is assigned to this single regulatory role and scope.
          </p>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Multi-context scenario: render dropdown of verified backend contexts
  const handleContextChange = (contextKey: string) => {
    const target = auth.roles.find((r) => getRoleContextKey(r) === contextKey);
    if (target) {
      auth.switchContext(target);
      const ws = roleCodeToWorkspace(target.role_code);
      if (ws && ROLES[ws]) {
        const destination = target.role_code === 'REGULATORY_POLICY_PUBLISHER'
          ? '/admin/policy/route-simulator'
          : ROLES[ws].defaultPath;
        navigate(destination);
        toast.info(`Switched Scope: ${formatRoleContextLabel(target)}`, {
          description: ROLES[ws].label,
        });
      }
    }
  };

  const currentKey = activeContext ? getRoleContextKey(activeContext) : '';

  return (
    <div className="flex items-center gap-1.5">
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200/80 rounded-lg p-1 pl-2">
            <span className="text-[11px] font-medium tracking-tight text-slate-500 uppercase flex items-center gap-1 select-none">
              <CurrentIcon className="size-3.5 text-primary" />
              <span className="hidden sm:inline">Scope:</span>
            </span>

            <Select value={currentKey} onValueChange={handleContextChange}>
              <SelectTrigger
                className="h-7 text-xs font-semibold bg-white border-slate-200 shadow-none px-2 text-slate-900 min-w-[140px] sm:min-w-[160px]"
                aria-label="Select active role scope"
              >
                <SelectValue placeholder="Select active scope" />
              </SelectTrigger>

              <SelectContent align="end" className="text-xs">
                {auth.roles.map((rc) => {
                  const ws = roleCodeToWorkspace(rc.role_code) || 'auditor';
                  const Icon = ROLE_ICONS[ws] || UserCheck;
                  const label = formatRoleContextLabel(rc);
                  const key = getRoleContextKey(rc);

                  return (
                    <SelectItem key={key} value={key} className="text-xs py-2 cursor-pointer">
                      <div className="flex items-center gap-2">
                        <Icon className="size-3.5 text-muted-foreground" />
                        <div>
                          <div className="font-medium text-foreground">{label}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {rc.role_code}
                          </div>
                        </div>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>

            <span className="text-slate-400 hover:text-slate-600 transition-colors p-0.5 cursor-help">
              <Info className="size-3" />
            </span>
          </div>
        </TooltipTrigger>

        <TooltipContent side="bottom" align="end" className="max-w-xs text-xs p-3">
          <p className="font-medium text-white mb-1">Switch Role Scope</p>
          <p className="text-slate-300 leading-relaxed text-[11px]">
            Switch between authorized regulatory contexts and assigned institutions or review teams.
          </p>
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
