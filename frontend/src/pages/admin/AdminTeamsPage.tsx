import React from 'react';
import {
  Users,
  Building2,
  UserCheck,
  Briefcase,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export const AdminTeamsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Platform Administration</span>
            <span>/</span>
            <span>Review Teams</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Users className="w-6 h-6 text-primary" />
            Regulatory Review Team Assignments &amp; Rosters
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Team Alpha regional assignments for Western Compliance Directorate &bull; AY 2026-27
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-emerald-400 text-emerald-700 bg-emerald-50 py-1 px-3 self-start sm:self-auto">
          Team Alpha Active
        </Badge>
      </div>

      {/* Review Team Alpha Card */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-foreground">
                  Review Team Alpha (Western Regional Directorate)
                </h2>
                <Badge variant="outline" className="text-[10px] border-emerald-500 text-emerald-700 bg-emerald-50">
                  OPERATIONAL
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Assigned Jurisdiction: Maharashtra &amp; Goa &bull; AY 2026-27 Approval Cycle
              </p>
            </div>
          </div>

          <span className="text-xs font-mono text-muted-foreground">
            Team ID: <span className="font-semibold text-foreground">TEAM-WEST-ALPHA</span>
          </span>
        </div>

        {/* Team Members */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-md border p-4 bg-muted/30 space-y-2">
            <span className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider block">
              Supervisory Team Lead
            </span>
            <div className="flex items-center gap-2.5">
              <UserCheck className="w-4 h-4 text-purple-600" />
              <div>
                <span className="font-bold text-xs text-foreground block">
                  Dr. H. V. Verma
                </span>
                <span className="text-[11px] text-muted-foreground block">
                  Senior Regulatory Lead Auditor &bull; Western Region
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-md border p-4 bg-muted/30 space-y-2">
            <span className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider block">
              Case Reviewing Auditor
            </span>
            <div className="flex items-center gap-2.5">
              <UserCheck className="w-4 h-4 text-blue-600" />
              <div>
                <span className="font-bold text-xs text-foreground block">
                  Vikram Rao
                </span>
                <span className="text-[11px] text-muted-foreground block">
                  Technical Compliance Auditor &bull; Western Region
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Assigned Case Scopes */}
        <div className="space-y-3 pt-2">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
            Assigned Case Docket:
          </span>
          <div className="rounded-md border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3">
              <Building2 className="w-5 h-5 text-primary" />
              <div>
                <span className="font-bold text-foreground block">
                  Apex Institute of Technology
                </span>
                <span className="text-muted-foreground font-mono text-[11px] block">
                  APP-2026-EOA-0023 &bull; AICTE ID: 1-10948201
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="font-mono text-[11px]">AY 2026-27</Badge>
              <Badge variant="outline" className="border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[11px]">
                IN_PROGRESS
              </Badge>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default AdminTeamsPage;
