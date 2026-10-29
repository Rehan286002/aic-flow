import { useLocation, Link } from 'react-router-dom';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { useWorkspaceRole } from '@/hooks/useWorkspaceRole';

const PATH_TITLES: Record<string, string> = {
  institution: 'Institution Portal',
  auditor: 'Auditor Workspace',
  lead: 'Lead Auditor Oversight',
  admin: 'Administration',
  overview: 'Overview',
  dashboard: 'Verification Dashboard',
  queue: 'Assigned Queue',
  'case-workspace': 'Case Workspace',
  'evidence-explorer': 'Evidence Explorer',
  'source-verification': 'Source Verification',
  'finding-review': 'Finding Review',
  activity: 'Case Activity',
  reports: 'Reports & Proofs',
  assist: 'AIC Assist',
  applications: 'Applications',
  new: 'New Application',
  documents: 'Document Center',
  rectification: 'Rectification',
  'escalated-queue': 'Escalated Queue',
  'case-review': 'Lead Case Review',
  recommendations: 'Recommendations',
  'inspection-referrals': 'Inspection Referrals',
  'temporal-replay': 'Temporal Replay',
  'audit-history': 'Audit History',
  users: 'Users & Roles',
  teams: 'Review Teams',
  rules: 'Rule Configuration',
  connectors: 'Issuer Connectors',
  health: 'System Health',
  logs: 'Operational Logs',
  settings: 'Settings',
};

export function AppBreadcrumbs() {
  const location = useLocation();
  const { currentRoleConfig } = useDemoRole();
  const pathnames = location.pathname.split('/').filter(Boolean);

  if (pathnames.length === 0) {
    return null;
  }

  return (
    <Breadcrumb aria-label="Application Breadcrumb" className="text-xs">
      <BreadcrumbList className="gap-1.5 text-muted-foreground">
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link
              to={currentRoleConfig.defaultPath}
              className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              <img src="/aic-flow.svg" alt="Logo" className="size-3.5 object-contain" />
              <span>AIC-Flow</span>
            </Link>
          </BreadcrumbLink>
        </BreadcrumbItem>

        {pathnames.map((segment, index) => {
          const isLast = index === pathnames.length - 1;
          const href = `/${pathnames.slice(0, index + 1).join('/')}`;
          const title = PATH_TITLES[segment] || segment.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

          return (
            <span key={href} className="inline-flex items-center gap-1.5">
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage className="font-medium text-foreground">
                    {title}
                  </BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link
                      to={href}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {title}
                    </Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </span>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
