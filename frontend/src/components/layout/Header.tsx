import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RoleScopeSelector } from './RoleScopeSelector';
import { NotificationPopover } from './NotificationPopover';
import { UserMenu } from './UserMenu';
import { AppBreadcrumbs } from './Breadcrumbs';

interface HeaderProps {
  onOpenMobileMenu: () => void;
}

export function Header({ onOpenMobileMenu }: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 w-full shrink-0 items-center justify-between border-b border-slate-200/80 bg-white px-4 lg:px-6 shadow-xs select-none">
      {/* Left side: Mobile Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={onOpenMobileMenu}
          className="lg:hidden text-slate-700 border-slate-200"
          aria-label="Open mobile navigation menu"
        >
          <Menu className="size-4" />
        </Button>

        <div className="flex items-center gap-2 lg:hidden">
          <img src="/aic-flow.svg" alt="AIC-Flow Logo" className="size-7 object-contain rounded bg-white p-0.5 border border-slate-200" />
          <span className="font-bold text-sm tracking-tight text-slate-900">AIC-Flow</span>
        </div>

        <div className="hidden sm:block">
          <AppBreadcrumbs />
        </div>
      </div>

      {/* Right side: Indicators, Role Preview, Notifications & User */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Academic Year Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium border border-slate-200/60">
          <span className="size-1.5 rounded-full bg-indigo-600" />
          <span className="font-semibold text-slate-900">AY 2026-27</span>
        </div>

        {/* Workspace Selector */}
        <DemoRoleSelector />

        {/* Notification Bell */}
        <NotificationPopover />

        {/* User Profile Dropdown */}
        <UserMenu />
      </div>
    </header>
  );
}
