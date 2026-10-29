import React from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Compass,
  Building2,
  ArrowLeft,
  Layers,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  EvidenceContradictionMatrix,
  DEFAULT_CONTRADICTION_ROWS,
} from '@/features/validation/components/EvidenceContradictionMatrix';

export const AuditorEvidenceExplorerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const activeItem = searchParams.get('item') || undefined;

  const handleSelectTab = (itemCode?: string) => {
    if (itemCode) {
      setSearchParams({ item: itemCode });
    } else {
      setSearchParams({});
    }
  };

  const requirementTabs = [
    { code: undefined, label: 'All Requirements (7)' },
    { code: 'EOA-SD-01', label: 'EOA-SD-01: Affidavit 2' },
    { code: 'EOA-SD-02', label: 'EOA-SD-02: Payment Receipt' },
    { code: 'EOA-SD-03', label: 'EOA-SD-03: Building Completion' },
    { code: 'EOA-SD-04', label: 'EOA-SD-04: Structural Stability' },
    { code: 'EOA-SD-05', label: 'EOA-SD-05: Fire Safety NOC' },
    { code: 'EOA-SD-06', label: 'EOA-SD-06: Satellite Map' },
    { code: 'EOA-SD-07', label: 'EOA-SD-07: Audited Accounts' },
  ];

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
            <span className="font-semibold text-foreground">Evidence Contradiction Explorer</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Compass className="h-6 w-6 text-primary" />
            4-Tier Evidence Contradiction Explorer
          </h1>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={() => navigate('/auditor/case-workspace')}
          className="text-xs h-8 gap-1.5"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Case Workspace
        </Button>
      </div>

      {/* Case Context Banner */}
      <div className="p-4 rounded-lg bg-card border border-border shadow-2xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-primary/10 text-primary">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Apex Institute of Technology</h3>
            <p className="text-muted-foreground font-mono text-xs">
              AICTE ID: 1-10948201 &bull; App: APP-2026-EOA-0023 (AY 2026-27, Rev #1)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1 font-mono text-[11px]">
            <Database className="h-3 w-3 text-primary" />
            6 Pinned Connectors [SIMULATED]
          </Badge>
          <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 text-[11px] font-semibold">
            Status: Read-Only Reference Run
          </Badge>
        </div>
      </div>

      {/* Requirement Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-border/80 pb-2">
        {requirementTabs.map((t) => (
          <Button
            key={t.code || 'ALL'}
            size="xs"
            variant={activeItem === t.code ? 'default' : 'outline'}
            onClick={() => handleSelectTab(t.code)}
            className="text-xs h-7 px-2.5"
          >
            {t.label}
          </Button>
        ))}
      </div>

      {/* 4-Tier Architecture Explanation Card */}
      <div className="p-4 rounded-lg bg-muted/30 border border-border/60 text-xs space-y-2">
        <div className="flex items-center gap-2 text-foreground font-semibold">
          <Layers className="h-4 w-4 text-primary" />
          <span>Four-Tier Evidentiary Cross-Verification Architecture</span>
        </div>
        <p className="text-muted-foreground text-[11px] leading-relaxed">
          The regulatory rule engine evaluates institutional compliance by strictly triangulating data across 4 distinct evidence tiers:
          applicant declarations, machine-extracted OCR text with confidence metrics, human auditor field reviews, and authoritative external government registry snapshots.
          Discrepancies automatically flag regulatory findings for auditor triage.
        </p>
      </div>

      {/* Main Contradiction Matrix */}
      <EvidenceContradictionMatrix
        rows={DEFAULT_CONTRADICTION_ROWS}
        selectedItemCode={activeItem}
        onSelectItemCode={(code) => handleSelectTab(code)}
        isReadOnly={true}
      />
    </div>
  );
};
