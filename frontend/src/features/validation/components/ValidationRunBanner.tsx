import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  XCircle,
  Cpu,
  Clock,
  Database,
  Layers,
  Lock,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { ValidationRunRead } from '../types';

interface ValidationRunBannerProps {
  run: ValidationRunRead;
  isReferenceRun?: boolean;
}

export const ValidationRunBanner: React.FC<ValidationRunBannerProps> = ({
  run,
  isReferenceRun = false,
}) => {
  // Dynamically compute metrics directly from the actual results array or summary
  const totalResults = run.results?.length ?? run.summary?.total_results ?? 0;
  const satisfiedCount =
    run.summary?.satisfied_count ??
    run.results?.filter((r) => r.result_status === 'SATISFIED').length ??
    0;
  const deficientCount =
    run.summary?.deficient_count ??
    run.results?.filter((r) => r.result_status === 'DEFICIENT').length ??
    0;
  const unableCount =
    run.summary?.unable_to_determine_count ??
    run.results?.filter((r) => r.result_status === 'UNABLE_TO_DETERMINE').length ??
    0;
  const notApplicableCount =
    run.summary?.not_applicable_count ??
    run.results?.filter((r) => r.result_status === 'NOT_APPLICABLE').length ??
    0;

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'N/A';
    try {
      return new Date(isoString).toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        dateStyle: 'medium',
        timeStyle: 'medium',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="bg-card text-card-foreground rounded-lg border border-border shadow-xs p-5 space-y-4">
      {/* Top Bar: Status, Engine Version, and Reference Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={
              run.status === 'COMPLETED'
                ? 'default'
                : run.status === 'RUNNING'
                ? 'secondary'
                : 'destructive'
            }
            className="px-2.5 py-1 text-xs font-semibold uppercase tracking-wider"
          >
            Run Status: {run.status}
          </Badge>

          <Badge variant="outline" className="flex items-center gap-1.5 px-2.5 py-1 text-xs">
            <Cpu className="h-3.5 w-3.5 text-primary" />
            <span>Engine: {run.engine_version || '1.0.0-phase6-batch3'}</span>
          </Badge>

          <Badge variant="outline" className="flex items-center gap-1.5 px-2.5 py-1 text-xs">
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
            <span>Run Type: {run.run_type}</span>
          </Badge>

          {isReferenceRun && (
            <Badge
              variant="secondary"
              className="flex items-center gap-1.5 bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 px-2.5 py-1 text-xs font-medium"
            >
              <Lock className="h-3 w-3" />
              <span>Reference Run (Read-Only Baseline)</span>
            </Badge>
          )}
        </div>

        {/* Timestamps */}
        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5" title="Deterministic evaluation cutoff timestamp">
            <Clock className="h-3.5 w-3.5" />
            <span>Evaluated As-Of: {formatDate(run.evaluation_as_of)} IST</span>
          </div>
          {run.completed_at && (
            <div className="flex items-center gap-1.5">
              <span>Completed: {formatDate(run.completed_at)} IST</span>
            </div>
          )}
        </div>
      </div>

      {/* Pinned Versions & Provenance Bar */}
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/60 text-xs">
        <span className="text-muted-foreground font-medium">Deterministic Snapshot Pinning:</span>
        <Badge variant="outline" className="bg-muted/40 font-mono text-[11px]">
          7 Active Rule Versions Pinned
        </Badge>
        <Badge variant="outline" className="bg-muted/40 font-mono text-[11px] flex items-center gap-1">
          <Database className="h-3 w-3 text-primary" />
          <span>6 Sources Pinned [SIMULATED]</span>
        </Badge>
        <span className="text-muted-foreground/80 italic text-[11px]">
          (SRC_AICTE_PORTAL, SRC_REVENUE_LAND, SRC_MUNICIPAL_BLDG, SRC_FIRE_SERVICES, SRC_ICAI_UDIN, SRC_BHUVAN_GEOMAP)
        </span>
      </div>

      {/* Dynamic Summary Metric Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
        <div className="flex items-center justify-between p-2.5 rounded-md bg-muted/40 border border-border/50">
          <span className="text-xs text-muted-foreground font-medium">Total Rules</span>
          <span className="text-base font-semibold">{totalResults}</span>
        </div>

        <div className="flex items-center justify-between p-2.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-xs font-medium">Satisfied</span>
          </div>
          <span className="text-base font-bold">{satisfiedCount}</span>
        </div>

        <div className="flex items-center justify-between p-2.5 rounded-md bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
          <div className="flex items-center gap-1.5">
            <XCircle className="h-4 w-4" />
            <span className="text-xs font-medium">Deficient</span>
          </div>
          <span className="text-base font-bold">{deficientCount}</span>
        </div>

        <div className="flex items-center justify-between p-2.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400">
          <div className="flex items-center gap-1.5">
            <HelpCircle className="h-4 w-4" />
            <span className="text-xs font-medium">Unable to Det.</span>
          </div>
          <span className="text-base font-bold">{unableCount}</span>
        </div>

        <div className="flex items-center justify-between p-2.5 rounded-md bg-slate-500/10 border border-slate-500/20 text-slate-600 dark:text-slate-400">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs font-medium">Not Applicable</span>
          </div>
          <span className="text-base font-bold">{notApplicableCount}</span>
        </div>
      </div>
    </div>
  );
};

