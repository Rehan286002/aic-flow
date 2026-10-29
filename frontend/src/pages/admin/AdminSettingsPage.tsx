import React from 'react';
import {
  Sliders,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export const AdminSettingsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Platform Administration</span>
            <span>/</span>
            <span>System Parameters</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Sliders className="w-6 h-6 text-primary" />
            AICTE Regulatory Parameters &amp; Engine Configuration
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Statutory thresholds and operational constraints governing automated evaluation rules
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary py-1 px-3 self-start sm:self-auto">
          AICTE APH 2024–2027 Spec
        </Badge>
      </div>

      {/* Settings Grid */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-6">
        <div>
          <h2 className="text-base font-bold tracking-tight text-foreground">
            Statutory Regulatory Thresholds
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Parameters configured per AICTE Approval Process Handbook (APH 2024–2027) statutory norms.
          </p>
        </div>

        <div className="divide-y divide-border text-xs">
          {/* Active Academic Year */}
          <div className="py-3.5 flex items-center justify-between">
            <div>
              <span className="font-bold text-foreground block">
                Active Regulatory Approval Cycle
              </span>
              <span className="text-muted-foreground text-[11px]">
                Target academic cycle for Extension of Approval (EoA) self-disclosure
              </span>
            </div>
            <Badge variant="outline" className="font-mono text-xs font-bold">
              2026-27
            </Badge>
          </div>

          {/* Building Age Cutoff */}
          <div className="py-3.5 flex items-center justify-between">
            <div>
              <span className="font-bold text-foreground block">
                Structural Stability Mandatory Cutoff
              </span>
              <span className="text-muted-foreground text-[11px]">
                Buildings constructed $\ge$ threshold mandate registered structural engineer certificate
              </span>
            </div>
            <Badge variant="outline" className="font-mono text-xs font-bold border-purple-400 text-purple-700 bg-purple-50">
              30 Years
            </Badge>
          </div>

          {/* Affidavit Stamp Value */}
          <div className="py-3.5 flex items-center justify-between">
            <div>
              <span className="font-bold text-foreground block">
                Affidavit 2 Minimum Stamp Paper Value
              </span>
              <span className="text-muted-foreground text-[11px]">
                Minimum statutory denomination for notarized non-judicial / e-stamp legal undertaking
              </span>
            </div>
            <Badge variant="outline" className="font-mono text-xs font-bold">
              ₹100
            </Badge>
          </div>

          {/* Max File Upload Stream */}
          <div className="py-3.5 flex items-center justify-between">
            <div>
              <span className="font-bold text-foreground block">
                ClamAV Antivirus Maximum File Stream
              </span>
              <span className="text-muted-foreground text-[11px]">
                Upload ceiling per documentary evidence bundle PDF
              </span>
            </div>
            <Badge variant="outline" className="font-mono text-xs font-bold">
              25 MB
            </Badge>
          </div>

          {/* Auditor Review Rationale Min Length */}
          <div className="py-3.5 flex items-center justify-between">
            <div>
              <span className="font-bold text-foreground block">
                Minimum Non-Whitespace Auditor Rationale
              </span>
              <span className="text-muted-foreground text-[11px]">
                Enforced by finding state machine to prevent empty or whitespace-only review triage
              </span>
            </div>
            <Badge variant="outline" className="font-mono text-xs font-bold border-emerald-500 text-emerald-700 bg-emerald-50">
              5 Characters
            </Badge>
          </div>

          {/* External Source Connector Mode */}
          <div className="py-3.5 flex items-center justify-between">
            <div>
              <span className="font-bold text-foreground block">
                Source Connector Operating Mode
              </span>
              <span className="text-muted-foreground text-[11px]">
                Synthetic mock registries providing reproducible offline demonstration signals
              </span>
            </div>
            <Badge variant="outline" className="font-mono text-xs font-bold border-amber-400 text-amber-700 bg-amber-50">
              SIMULATED (MOCK)
            </Badge>
          </div>
        </div>
      </div>
    </div>
  );
};
export default AdminSettingsPage;
