import { useState } from 'react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { StatusDistributionChart } from '@/components/dashboard/StatusDistributionChart';
import { VerificationDistributionChart } from '@/components/dashboard/VerificationDistributionChart';
import { RecentApplicationsTable } from '@/components/dashboard/RecentApplicationsTable';
import { PendingWorkList } from '@/components/dashboard/PendingWorkList';
import { RecentActivityFeed } from '@/components/dashboard/RecentActivityFeed';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SYNTHETIC_AUDITOR_METRICS } from '@/features/dashboard/fixtures/auditor-dashboard-fixture';
import {
  Download,
  RotateCw,
  PlusCircle,
} from 'lucide-react';
import { toast } from 'sonner';

export default function AuditorDashboardPage() {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      toast.success('Auditor queue refreshed', {
        description: 'Queue synchronized with regulatory verification pipeline.',
      });
    }, 600);
  };

  const handleExport = () => {
    toast.success('Exporting Regulatory Summary', {
      description: 'Generating compliance verification summary report for AY 2026-27 (JSON / PDF).',
    });
  };

  const handleTriageNext = () => {
    toast.info('Triage Next High-Priority Case', {
      description: 'Routing to APP-2026-EOA-0842 (Apex Institute of Technology): Fire Safety NOC Expired.',
    });
  };

  return (
    <div className="space-y-6">
      {/* Page Header with Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Auditor Verification Dashboard
            </h1>
            <Badge variant="outline" className="text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200">
              Active AY 2026-27
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 max-w-3xl leading-relaxed">
            Regulatory evidence queue, document integrity checks, and automated validation triage for Extension of Approval self-disclosure applications.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="h-8 text-xs border-slate-200 text-slate-700 hover:bg-slate-50"
          >
            <RotateCw className={`size-3.5 mr-1.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="h-8 text-xs border-slate-200 text-slate-700 hover:bg-slate-50"
          >
            <Download className="size-3.5 mr-1.5" />
            <span>Export Report</span>
          </Button>

          <Button
            size="sm"
            onClick={handleTriageNext}
            className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium shadow-xs"
          >
            <PlusCircle className="size-3.5 mr-1.5" />
            <span>Triage Next Case</span>
          </Button>
        </div>
      </div>

      {/* Row 1: Top 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {SYNTHETIC_AUDITOR_METRICS.map((metric) => (
          <MetricCard key={metric.id} metric={metric} />
        ))}
      </div>

      {/* Row 2: Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <StatusDistributionChart />
        <VerificationDistributionChart />
      </div>

      {/* Row 3: Applications Table + Triage Queue & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Applications Table (7 cols on lg, 8 on xl) */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">
          <RecentApplicationsTable />
        </div>

        {/* Right Column: Triage Queue & Activity Feed (5 cols on lg, 4 on xl) */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-6">
          <PendingWorkList />
          <RecentActivityFeed />
        </div>
      </div>
    </div>
  );
}
