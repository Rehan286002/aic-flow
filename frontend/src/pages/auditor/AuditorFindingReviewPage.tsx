import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  Building2,
  Filter,
  Search,
  RefreshCw,
  ArrowLeft,
  SlidersHorizontal,
  Lock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { FindingActionModal } from '@/features/validation/components/FindingActionModal';
import { validationApi } from '@/features/validation/api';
import type { FindingRead, FindingSeverity } from '@/features/validation/types';

const APEX_INSTITUTION_ID = '605839a3-9c20-4ec6-b9f9-765a4b732ad0';
const APEX_APPLICATION_ID = '082c25e6-a94c-454f-897b-7d307819abcd';
const APEX_REFERENCE_RUN_ID = '5822d8f2-dcd4-4fd3-8794-cb84ef23e54f';

export const AuditorFindingReviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [findings, setFindings] = useState<FindingRead[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Finding Action Modal
  const [selectedFinding, setSelectedFinding] = useState<FindingRead | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const loadFindings = useCallback(async () => {
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const data = await validationApi.listFindings(APEX_INSTITUTION_ID, APEX_APPLICATION_ID, {
        validation_run_id: APEX_REFERENCE_RUN_ID,
      });
      setFindings(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve findings from backend.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadFindings();
  }, [loadFindings]);

  const handleOpenTriage = (finding: FindingRead) => {
    setSelectedFinding(finding);
    setIsModalOpen(true);
  };

  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      const matchesSeverity = severityFilter === 'ALL' || f.severity === severityFilter;
      const matchesStatus = statusFilter === 'ALL' || f.status === statusFilter;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        f.title.toLowerCase().includes(q) ||
        f.category.toLowerCase().includes(q) ||
        (f.internal_reason || '').toLowerCase().includes(q);
      return matchesSeverity && matchesStatus && matchesSearch;
    });
  }, [findings, severityFilter, statusFilter, searchQuery]);

  const getSeverityBadge = (severity: FindingSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <Badge variant="destructive" className="text-[10px] uppercase font-bold">Critical</Badge>;
      case 'HIGH':
        return <Badge className="bg-orange-500 text-white text-[10px] uppercase font-bold">High</Badge>;
      case 'MEDIUM':
        return <Badge variant="secondary" className="bg-amber-500/15 text-amber-700 dark:text-amber-300 text-[10px] uppercase">Medium</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px] uppercase">{severity}</Badge>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <span>Auditor Console</span>
            <span>&bull;</span>
            <span>Case Workspace</span>
            <span>&bull;</span>
            <span className="font-semibold text-foreground">Finding Review & Triage</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <ShieldAlert className="h-6 w-6 text-primary" />
            Compliance Finding Triage Center
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => void loadFindings()}
            disabled={isLoading}
            className="text-xs h-8 gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh Findings
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate('/auditor/case-workspace')}
            className="text-xs h-8 gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Case Workspace
          </Button>
        </div>
      </div>

      {/* Case Context Pill */}
      <div className="p-4 rounded-lg bg-card border border-border shadow-2xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-primary/10 text-primary">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Apex Institute of Technology</h3>
            <p className="text-muted-foreground font-mono text-xs">
              AICTE ID: 1-10948201 &bull; Application: APP-2026-EOA-0023 (Rev #1)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            Total Findings: {findings.length}
          </Badge>
          <Badge variant="secondary" className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 text-xs flex items-center gap-1">
            <Lock className="h-3 w-3" />
            Reference Run (Read-Only Mode)
          </Badge>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-card p-4 rounded-lg border border-border shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search findings by title, category, or rationale..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-sm"
            />
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" />
            <span>Showing {filteredFindings.length} of {findings.length} findings</span>
          </div>
        </div>

        {/* Severity & Status Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/60 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-muted-foreground font-medium mr-1">Severity:</span>
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
              <Button
                key={sev}
                size="xs"
                variant={severityFilter === sev ? 'default' : 'outline'}
                onClick={() => setSeverityFilter(sev)}
                className="text-xs h-7 px-2"
              >
                {sev}
              </Button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <Filter className="h-3.5 w-3.5 text-muted-foreground mr-1" />
            <span className="text-muted-foreground font-medium">Status:</span>
            {['ALL', 'OPEN', 'CLARIFICATION_REQUESTED', 'RESOLVED', 'ESCALATED'].map((st) => (
              <Button
                key={st}
                size="xs"
                variant={statusFilter === st ? 'default' : 'outline'}
                onClick={() => setStatusFilter(st)}
                className="text-xs h-7 px-2"
              >
                {st === 'ALL' ? 'All' : st.replace(/_/g, ' ')}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 rounded-lg bg-muted/40 animate-pulse border border-border/50" />
            ))}
          </div>
        ) : errorMsg ? (
          <div className="p-6 text-center text-red-600 dark:text-red-400 border border-red-500/30 rounded-lg bg-red-500/10 text-xs">
            {errorMsg}
          </div>
        ) : filteredFindings.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground border border-dashed rounded-lg bg-muted/20 text-xs">
            No findings match the current filter selection.
          </div>
        ) : (
          filteredFindings.map((finding) => (
            <div
              key={finding.finding_id}
              className="p-4 rounded-lg bg-card border border-border shadow-2xs hover:border-border/80 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 min-w-0 flex-1 text-xs">
                <div className="flex items-center gap-2 flex-wrap">
                  {getSeverityBadge(finding.severity)}
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {finding.category}
                  </Badge>
                  <Badge variant="secondary" className="font-semibold text-[10px]">
                    Status: {finding.status}
                  </Badge>
                  <span className="text-[11px] text-muted-foreground font-mono">
                    ID: {finding.finding_id.substring(0, 8)}...
                  </span>
                </div>

                <h3 className="font-semibold text-sm text-foreground">{finding.title}</h3>

                {finding.internal_reason && (
                  <p className="text-muted-foreground text-xs leading-relaxed line-clamp-2">
                    <span className="font-medium text-foreground">Internal Reason:</span>{' '}
                    {finding.internal_reason}
                  </p>
                )}

                {finding.evidence && finding.evidence.length > 0 && (
                  <div className="text-[11px] text-primary font-medium">
                    &bull; {finding.evidence.length} linked evidence record(s) attached
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleOpenTriage(finding)}
                  className="text-xs h-8"
                >
                  Inspect Audit Evidence
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal for inspection */}
      <FindingActionModal
        finding={selectedFinding}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        isReadOnly={true}
      />
    </div>
  );
};
