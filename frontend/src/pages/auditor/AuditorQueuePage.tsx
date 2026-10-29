import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Inbox,
  Building2,
  CheckCircle2,
  Clock,
  ArrowRight,
  Search,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useDemoScenario } from '@/features/demo/demoContext';

export const AuditorQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, resetDemo } = useDemoScenario();
  const [filterStatus, setFilterStatus] = useState<'ALL' | 'RECTIFIED' | 'PENDING'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const isRectified = demoState.activeRevisionNumber >= 2;

  // Real demonstration case row derived dynamically from demoState
  const cases = [
    {
      id: demoState.applicationId,
      applicationNumber: demoState.applicationNumber,
      institutionName: demoState.institutionName,
      institutionId: demoState.institutionId,
      academicYear: demoState.academicYear,
      activeRevision: `Revision #${demoState.activeRevisionNumber}`,
      reviewTeam: 'Review Team Alpha (Western Region)',
      deficienciesCount: demoState.validationRun.summary?.deficient_count ?? 0,
      satisfiedCount: demoState.validationRun.summary?.satisfied_count ?? 0,
      unableCount: demoState.validationRun.summary?.unable_to_determine_count ?? 0,
      isRectifiedReady: isRectified,
      statusLabel: isRectified ? 'Revision 2 Submitted: Ready for Concurrence' : 'Under Regulatory Review',
      submittedAt: '2026-10-29T08:30:00Z',
    },
  ];

  const filteredCases = cases.filter((c) => {
    if (filterStatus === 'RECTIFIED' && !c.isRectifiedReady) return false;
    if (filterStatus === 'PENDING' && c.isRectifiedReady) return false;
    const q = searchQuery.toLowerCase();
    return (
      c.applicationNumber.toLowerCase().includes(q) ||
      c.institutionName.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Auditor</span>
            <span>/</span>
            <span>Assigned Cases Queue</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Inbox className="w-6 h-6 text-primary" />
            Auditor Case Queue &amp; Verification Triage
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Active Assigned Applications for Academic Year 2026-27 &bull; Review Team Alpha
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={resetDemo}
            className="text-xs text-muted-foreground hover:text-foreground"
            title="Reset demonstration scenario"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Demo
          </Button>
        </div>
      </div>

      {/* Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
            Assigned Cases
          </span>
          <span className="text-2xl font-bold tracking-tight text-foreground mt-1 block">
            1
          </span>
          <span className="text-[11px] text-muted-foreground mt-0.5 block">
            Apex Institute of Tech
          </span>
        </div>

        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
            Active Deficiencies
          </span>
          <span className="text-2xl font-bold tracking-tight text-red-600 mt-1 block">
            {demoState.validationRun.summary?.deficient_count ?? 0}
          </span>
          <span className="text-[11px] text-muted-foreground mt-0.5 block">
            Across 7 Annexure 2.1 items
          </span>
        </div>

        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
            Rectifications Received
          </span>
          <span className="text-2xl font-bold tracking-tight text-emerald-600 mt-1 block">
            {isRectified ? '1' : '0'}
          </span>
          <span className="text-[11px] text-muted-foreground mt-0.5 block">
            {isRectified ? 'Revision #2 ready for review' : 'Awaiting institution response'}
          </span>
        </div>

        <div className="p-4 rounded-lg border bg-card text-card-foreground shadow-xs">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
            Clarifications Open
          </span>
          <span className="text-2xl font-bold tracking-tight text-amber-600 mt-1 block">
            {isRectified ? '0' : '1'}
          </span>
          <span className="text-[11px] text-muted-foreground mt-0.5 block">
            EOA-SD-04 stability cert
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md w-full">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
          <Input
            placeholder="Search by application number or institute name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>

        <div className="flex items-center gap-1.5 self-start sm:self-auto">
          <Button
            size="sm"
            variant={filterStatus === 'ALL' ? 'default' : 'outline'}
            className="text-xs h-8"
            onClick={() => setFilterStatus('ALL')}
          >
            All Cases ({cases.length})
          </Button>
          <Button
            size="sm"
            variant={filterStatus === 'RECTIFIED' ? 'default' : 'outline'}
            className="text-xs h-8"
            onClick={() => setFilterStatus('RECTIFIED')}
          >
            Rectified ({isRectified ? 1 : 0})
          </Button>
          <Button
            size="sm"
            variant={filterStatus === 'PENDING' ? 'default' : 'outline'}
            className="text-xs h-8"
            onClick={() => setFilterStatus('PENDING')}
          >
            Pending Clarification ({isRectified ? 0 : 1})
          </Button>
        </div>
      </div>

      {/* Cases Queue Table */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b bg-muted/50 font-semibold text-muted-foreground">
                <th className="py-3 px-4">Application Details</th>
                <th className="py-3 px-4">Revision</th>
                <th className="py-3 px-4">Deficiency Breakdown</th>
                <th className="py-3 px-4">Status &amp; Alert</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredCases.map((c) => (
                <tr key={c.id} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="flex items-start gap-2.5">
                      <div className="rounded-md bg-primary/10 p-2 text-primary mt-0.5">
                        <Building2 className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="font-mono font-bold text-foreground block text-xs">
                          {c.applicationNumber}
                        </span>
                        <span className="font-medium text-foreground text-xs block">
                          {c.institutionName}
                        </span>
                        <span className="text-muted-foreground text-[11px] block">
                          AY {c.academicYear} &bull; {c.reviewTeam}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={
                        c.isRectifiedReady
                          ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[11px] font-semibold'
                          : 'font-mono text-[11px]'
                      }
                    >
                      {c.activeRevision}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 font-mono text-[11px]">
                      <span className="text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                        {c.satisfiedCount} Sat
                      </span>
                      <span className="text-red-700 font-semibold bg-red-50 px-1.5 py-0.5 rounded border border-red-200">
                        {c.deficienciesCount} Def
                      </span>
                      <span className="text-amber-700 font-semibold bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                        {c.unableCount} Unk
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {c.isRectifiedReady ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 animate-pulse border border-emerald-300">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {c.statusLabel}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-100 text-amber-800 border border-amber-300">
                        <Clock className="w-3.5 h-3.5" />
                        {c.statusLabel}
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <Button
                      size="sm"
                      className="bg-primary hover:bg-primary/90 text-primary-foreground h-8 text-xs font-medium"
                      onClick={() => navigate('/auditor/case-workspace')}
                    >
                      <span>Open Workspace</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default AuditorQueuePage;
