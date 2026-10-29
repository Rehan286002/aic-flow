import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  Award,
  RotateCcw,
  Building2,
  FileSearch,
  ClipboardList,
  AlertOctagon,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useDemoScenario } from '@/features/demo/demoContext';

export const LeadOverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, resetDemo } = useDemoScenario();

  const escalatedCount = demoState.findings.filter((f) => f.status === 'ESCALATED').length;
  const resolvedCount = demoState.findings.filter((f) => f.status === 'RESOLVED').length;
  const isRectified = demoState.activeRevisionNumber >= 2;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Supervisory Oversight Console</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-primary" />
            Lead Auditor Supervisory Operations
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Western Regional Compliance Directorate &bull; AY 2026-27 Approval Process
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={resetDemo}
            className="text-xs text-muted-foreground hover:text-foreground h-8"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Scenario
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate('/lead/case-review')}
            className="text-xs h-8"
          >
            <FileSearch className="w-3.5 h-3.5 mr-1 text-primary" />
            Case Review Dossier
          </Button>

          <Button
            size="sm"
            onClick={() => navigate('/lead/recommendations')}
            className="text-xs h-8 bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            <Award className="w-3.5 h-3.5 mr-1" />
            Supervisory Disposition
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Assigned Cases
            </span>
            <Building2 className="w-4 h-4 text-primary" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-foreground">1</div>
          <span className="text-[11px] text-muted-foreground block mt-0.5">
            Apex Institute of Technology
          </span>
        </div>

        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Escalated Findings
            </span>
            <AlertOctagon className="w-4 h-4 text-purple-600" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-purple-700">
            {escalatedCount}
          </div>
          <span className="text-[11px] text-muted-foreground block mt-0.5">
            Requiring supervisory decision
          </span>
        </div>

        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Rectified / Resolved
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-700">
            {resolvedCount}
          </div>
          <span className="text-[11px] text-muted-foreground block mt-0.5">
            EOA-SD-04 Stability Cert
          </span>
        </div>

        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Active Revision
            </span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-foreground">
            #{demoState.activeRevisionNumber}
          </div>
          <span className="text-[11px] text-muted-foreground block mt-0.5">
            {isRectified ? 'Revision 2 (Rectified)' : 'Revision 1 (Initial)'}
          </span>
        </div>
      </div>

      {/* Supervisory Operations Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Escalated Items Card */}
        <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold tracking-tight text-foreground flex items-center gap-2">
              <AlertOctagon className="w-5 h-5 text-purple-600" />
              Escalated Finding Triage
            </h2>
            <Badge
              variant="outline"
              className={
                escalatedCount > 0
                  ? 'border-purple-300 text-purple-700 bg-purple-50 font-semibold'
                  : 'text-muted-foreground'
              }
            >
              {escalatedCount} Items Pending
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Auditors escalate findings when registry contradictions exceed automated resolution thresholds or require higher-level regulatory disposition.
          </p>

          <div className="rounded-md border p-3.5 bg-muted/40 space-y-2 text-xs">
            <div className="flex items-center justify-between font-semibold">
              <span>FIND-DEMO-03 &bull; Land Area Contradiction</span>
              <Badge variant="outline" className="text-[10px] border-red-300 text-red-700">HIGH</Badge>
            </div>
            <p className="text-muted-foreground text-[11px]">
              Declared 10.50 acres vs State Revenue registry confirmed 7.20 acres (SRC_REVENUE_LAND). Auditor recommends on-site physical demarcation survey.
            </p>
          </div>

          <div className="pt-2 flex justify-end">
            <Button
              size="sm"
              variant="outline"
              className="text-xs h-8"
              onClick={() => navigate('/lead/escalated-queue')}
            >
              Open Escalated Queue
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </div>

        {/* Supervisory Workflow Status Card */}
        <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold tracking-tight text-foreground flex items-center gap-2">
              <Award className="w-5 h-5 text-primary" />
              Regulatory Review Disposition
            </h2>
            <Badge
              variant="outline"
              className={
                demoState.leadDisposition
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold'
                  : 'border-amber-300 text-amber-700 bg-amber-50'
              }
            >
              {demoState.leadDisposition ? 'Disposition Recorded' : 'Disposition Pending'}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Lead Auditor formulates internal workflow recommendations: proceeding to next stage, holding for evidence, or referring for formal inspection.
          </p>

          {demoState.leadDisposition ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3.5 space-y-1 text-xs">
              <span className="font-bold text-emerald-900 block">
                Official Disposition: {demoState.leadDisposition.disposition}
              </span>
              <p className="text-emerald-800 text-[11px] italic">
                &ldquo;{demoState.leadDisposition.rationale}&rdquo;
              </p>
              <span className="text-[10px] text-emerald-700 block pt-1">
                Recorded by: {demoState.leadDisposition.leadAuditorName} at{' '}
                {new Date(demoState.leadDisposition.recordedAt || '').toLocaleString()}
              </span>
            </div>
          ) : (
            <div className="rounded-md border p-3.5 bg-muted/40 space-y-1 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground block">
                Pending Final Lead Review
              </span>
              <p className="text-[11px]">
                Review the cross-evaluator comparison between Revision 1 and Revision 2 before recording official disposition.
              </p>
            </div>
          )}

          <div className="pt-2 flex justify-between items-center">
            <Button
              size="sm"
              variant="ghost"
              className="text-xs h-8 text-primary"
              onClick={() => navigate('/lead/inspection-referrals')}
            >
              <ClipboardList className="w-3.5 h-3.5 mr-1" />
              Inspection Referrals
            </Button>
            <Button
              size="sm"
              className="text-xs h-8 bg-primary text-primary-foreground"
              onClick={() => navigate('/lead/recommendations')}
            >
              Review &amp; Record Disposition
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </div>
      </div>

      {/* Regional Compliance Benchmark Widget */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-600" />
            Western Region Regulatory Verification Benchmarks (AY 2026-27)
          </h2>
          <span className="text-xs text-muted-foreground">Central Bureau Baseline</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
          <div className="border rounded-md p-3 space-y-1">
            <span className="text-muted-foreground text-[11px]">Automated Match Rate</span>
            <div className="text-lg font-bold text-foreground font-mono">82.4%</div>
            <p className="text-[10px] text-emerald-700">State Revenue &amp; Municipal DBs</p>
          </div>
          <div className="border rounded-md p-3 space-y-1">
            <span className="text-muted-foreground text-[11px]">Average Rectification Window</span>
            <div className="text-lg font-bold text-foreground font-mono">4.2 Days</div>
            <p className="text-[10px] text-muted-foreground">Within 15-day statutory limit</p>
          </div>
          <div className="border rounded-md p-3 space-y-1">
            <span className="text-muted-foreground text-[11px]">Physical Referral Rate</span>
            <div className="text-lg font-bold text-foreground font-mono">6.8%</div>
            <p className="text-[10px] text-muted-foreground">Land &amp; structural discrepancies</p>
          </div>
        </div>
      </div>
    </div>
  );
};
export default LeadOverviewPage;
