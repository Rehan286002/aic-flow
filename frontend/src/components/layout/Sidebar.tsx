import { NavLink } from 'react-router-dom';
import { useWorkspaceRole } from '@/hooks/useWorkspaceRole';
import { ROLE_NAVIGATION } from '@/config/navigation';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  onCloseMobile?: () => void;
  isMobileSheet?: boolean;
}

export function Sidebar({ onCloseMobile, isMobileSheet = false }: SidebarProps) {
  const { currentRole, currentRoleConfig, sidebarCollapsed, toggleSidebar } = useDemoRole();
  const navItems = ROLE_NAVIGATION[currentRole] || [];

  const isCollapsed = !isMobileSheet && sidebarCollapsed;

  return (
    <aside
      className={`h-full flex flex-col justify-between bg-[#17233B] text-[#F8FAFC] transition-all duration-300 select-none ${
        isCollapsed ? 'w-[72px]' : 'w-64'
      }`}
    >
      {/* Top Header / Branding */}
      <div>
        <div className="h-16 flex items-center px-4 border-b border-[#1E2D49]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-white p-1 shadow-md shadow-indigo-950/40 overflow-hidden border border-white/20">
              <img src="/aic-flow.svg" alt="AIC-Flow Logo" className="size-full object-contain" />
            </div>

            {!isCollapsed && (
              <div className="flex flex-col truncate">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-base tracking-tight text-white leading-tight">
                    AIC-Flow
                  </span>
                  <span className="text-[9px] font-bold uppercase tracking-wider bg-indigo-500/30 text-indigo-200 px-1 rounded">
                    v1.0
                  </span>
                </div>
                <span className="text-[11px] text-[#B7C3D6] truncate leading-tight mt-0.5">
                  AICTE Regulatory Engine
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Workspace Identification Label */}
        {!isCollapsed ? (
          <div className="px-4 pt-4 pb-2">
            <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-[#B7C3D6] px-2 py-1 bg-[#1E2D49]/60 rounded border border-[#1E2D49]">
              <span className="truncate">{currentRoleConfig.label}</span>
              <span className="size-1.5 rounded-full bg-emerald-400 shrink-0" />
            </div>
          </div>
        ) : (
          <div className="pt-3 pb-2 flex justify-center">
            <div className="size-2 rounded-full bg-emerald-400" title={currentRoleConfig.label} />
          </div>
        )}

        {/* Navigation List */}
        <nav className="px-2 py-2 space-y-1 overflow-y-auto max-h-[calc(100vh-210px)]" aria-label="Role Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;

            const linkContent = (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium transition-all group relative ${
                    isActive
                      ? 'bg-[#293B5D] text-white font-semibold shadow-xs'
                      : 'text-[#B7C3D6] hover:bg-[#1E2D49] hover:text-[#F8FAFC]'
                  } ${isCollapsed ? 'justify-center px-0' : ''}`
                }
              >
                {({ isActive }) => (
                  <>
                    {/* Active route left bar indicator */}
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-md bg-indigo-500" />
                    )}

                    <Icon
                      className={`size-4.5 shrink-0 transition-transform ${
                        isActive
                          ? 'text-indigo-400 scale-105'
                          : 'text-[#B7C3D6] group-hover:text-white'
                      }`}
                    />

                    {!isCollapsed && (
                      <div className="flex flex-1 items-center justify-between truncate">
                        <span className="truncate">{item.title}</span>
                        {item.badge && (
                          <Badge
                            variant={item.badgeVariant || 'secondary'}
                            className={`h-4.5 px-1.5 text-[10px] font-bold ${
                              item.badgeVariant === 'destructive'
                                ? 'bg-rose-500 text-white'
                                : 'bg-[#1E2D49] text-[#B7C3D6] border-0'
                            }`}
                          >
                            {item.badge}
                          </Badge>
                        )}
                      </div>
                    )}
                  </>
                )}
              </NavLink>
            );

            if (isCollapsed) {
              return (
                <Tooltip key={item.path} delayDuration={150}>
                  <TooltipTrigger asChild>
                    <div>{linkContent}</div>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="bg-[#17233B] text-white border-[#1E2D49] text-xs p-2.5">
                    <div className="font-semibold text-white flex items-center gap-2">
                      <span>{item.title}</span>
                      {item.badge && (
                        <span className="text-[10px] bg-indigo-500 px-1 rounded text-white font-bold">
                          {item.badge}
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-[#B7C3D6] text-[11px] mt-0.5 max-w-[200px]">
                        {item.description}
                      </p>
                    )}
                  </TooltipContent>
                </Tooltip>
              );
            }

            return linkContent;
          })}
        </nav>
      </div>

      {/* Footer & Collapse Toggle */}
      <div className="border-t border-[#1E2D49] p-3">
        {!isCollapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-[#B7C3D6] px-1">
              <span className="flex items-center gap-1">
                <Sparkles className="size-3 text-indigo-400" />
                <span>Academic Year 2026-27</span>
              </span>
              <span className="font-mono text-[10px] text-slate-400">AICTE</span>
            </div>

            {!isMobileSheet && (
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                className="w-full justify-start text-xs text-[#B7C3D6] hover:bg-[#1E2D49] hover:text-white h-8 px-2"
                aria-label="Collapse sidebar navigation"
              >
                <ChevronLeft className="size-4 mr-2" />
                <span>Collapse Navigation</span>
              </Button>
            )}
          </div>
        ) : (
          !isMobileSheet && (
            <Tooltip delayDuration={150}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={toggleSidebar}
                  className="w-full flex justify-center text-[#B7C3D6] hover:bg-[#1E2D49] hover:text-white h-8"
                  aria-label="Expand sidebar navigation"
                >
                  <ChevronRight className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" className="bg-[#17233B] text-white border-[#1E2D49] text-xs">
                Expand Navigation
              </TooltipContent>
            </Tooltip>
          )
        )}
      </div>
    </aside>
  );
}
