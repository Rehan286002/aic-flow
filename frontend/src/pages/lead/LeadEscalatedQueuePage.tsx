import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  CheckCircle2,
  XCircle,
  FileSearch,
  ClipboardList,
  Search,
  ShieldAlert,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { useDemoScenario } from '@/features/demo/demoContext';
import type { FindingRead, FindingStatus } from '@/features/validation/types';

export const LeadEscalatedQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, updateFindingStatus, resetDemo } = useDemoScenario();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFinding, setSelectedFinding] = useState<FindingRead | null>(null);
  const [actionType, setActionType] = useState<'ACCEPT' | 'DISMISS' | null>(null);
  const [leadRationale, setLeadRationale] = useState('');

  // Find findings that are escalated or critical/high discrepancies
  const findings = demoState.findings;

  const filteredFindings = findings.filter((f) => {
    const q = searchQuery.toLowerCase();
    return (
      f.title.toLowerCase().includes(q) ||
      f.finding_id.toLowerCase().includes(q) ||
      (f.internal_reason && f.internal_reason.toLowerCase().includes(q))
    );
  });

  const handleOpenAction = (finding: FindingRead, type: 'ACCEPT' | 'DISMISS') => {
    setSelectedFinding(finding);
    setActionType(type);
    setLeadRationale('');
  };

  const handleConfirmAction = () => {
    if (!selectedFinding || !actionType || leadRationale.trim().length < 5) return;

    const targetStatus: FindingStatus = actionType === 'ACCEPT' ? 'ACCEPTED' : 'DISMISSED';
    updateFindingStatus(
      selectedFinding.finding_id,
      targetStatus,
      leadRationale.trim(),
      'Lead Auditor (Dr. H. V. Verma)'
    );

    setSelectedFinding(null);
    setActionType(null);
    setLeadRationale('');
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Escalated Findings Queue</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <AlertOctagon className="w-6 h-6 text-purple-600" />
            Supervisory Triage &amp; Escalation Queue
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Application: <span className="font-semibold text-foreground">{demoState.applicationNumber}</span> &bull; {demoState.institutionName}
          </p>
        </div>

        <div className="flex items-center gap-2">
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
            className="text-xs h-8"
            onClick={() => navigate('/lead/case-review')}
          >
            <FileSearch className="w-3.5 h-3.5 mr-1" />
            Case Review Dossier
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
          <Input
            placeholder="Search findings by ID, title, or reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldAlert className="w-4 h-4 text-purple-600" />
          <span>Showing {filteredFindings.length} Regulatory Findings</span>
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {filteredFindings.map((finding) => (
          <div
            key={finding.finding_id}
            className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 transition-colors hover:border-primary/40 space-y-3"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3">
              <div className="flex items-center gap-2.5">
                <span className="font-mono font-bold text-xs text-foreground bg-muted px-2 py-0.5 rounded border">
                  {finding.finding_id}
                </span>
                <h3 className="font-semibold text-sm text-foreground">
                  {finding.title}
                </h3>
              </div>

              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={
                    finding.severity === 'CRITICAL'
                      ? 'border-red-500 text-red-700 bg-red-50 font-semibold text-[10px]'
                      : finding.severity === 'HIGH'
                      ? 'border-amber-500 text-amber-700 bg-amber-50 font-semibold text-[10px]'
                      : 'border-muted text-muted-foreground text-[10px]'
                  }
                >
                  {finding.severity}
                </Badge>

                <Badge
                  variant="outline"
                  className={
                    finding.status === 'RESOLVED'
                      ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[10px]'
                      : finding.status === 'ESCALATED'
                      ? 'border-purple-500 text-purple-700 bg-purple-50 font-mono text-[10px]'
                      : finding.status === 'ACCEPTED'
                      ? 'border-blue-500 text-blue-700 bg-blue-50 font-mono text-[10px]'
                      : 'font-mono text-[10px]'
                  }
                >
                  {finding.status}
                </Badge>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-line">
              {finding.internal_reason || 'No internal reason recorded.'}
            </p>

            <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t text-xs">
              <span className="text-[11px] text-muted-foreground">
                Category: <span className="font-mono text-foreground">{finding.category}</span>
              </span>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                  onClick={() => handleOpenAction(finding, 'ACCEPT')}
                  disabled={finding.status === 'ACCEPTED' || finding.status === 'RESOLVED'}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                  Accept Finding
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs text-slate-700 border-slate-300 hover:bg-slate-50"
                  onClick={() => handleOpenAction(finding, 'DISMISS')}
                  disabled={finding.status === 'DISMISSED' || finding.status === 'RESOLVED'}
                >
                  <XCircle className="w-3.5 h-3.5 mr-1 text-slate-500" />
                  Dismiss with Note
                </Button>

                <Button
                  size="sm"
                  variant="default"
                  className="h-7 text-xs bg-purple-700 hover:bg-purple-800 text-white"
                  onClick={() => navigate('/lead/inspection-referrals')}
                >
                  <ClipboardList className="w-3.5 h-3.5 mr-1" />
                  Refer for Physical Inspection
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Confirmation Modal */}
      <Dialog
        open={Boolean(selectedFinding && actionType)}
        onOpenChange={(open) => !open && setSelectedFinding(null)}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {actionType === 'ACCEPT' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : (
                <XCircle className="w-5 h-5 text-slate-600" />
              )}
              {actionType === 'ACCEPT' ? 'Accept Regulatory Finding' : 'Dismiss Regulatory Finding'}
            </DialogTitle>
            <DialogDescription>
              {selectedFinding?.finding_id}: {selectedFinding?.title}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
                Supervisory Lead Rationale (Minimum 5 characters)
              </label>
              <Textarea
                rows={3}
                placeholder="Enter justification for supervisory disposition..."
                value={leadRationale}
                onChange={(e) => setLeadRationale(e.target.value)}
                className="text-xs font-sans"
              />
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedFinding(null)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={leadRationale.trim().length < 5}
                onClick={handleConfirmAction}
                className={
                  actionType === 'ACCEPT'
                    ? 'bg-emerald-700 hover:bg-emerald-800 text-white'
                    : 'bg-slate-700 hover:bg-slate-800 text-white'
                }
              >
                Confirm {actionType === 'ACCEPT' ? 'Acceptance' : 'Dismissal'}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
export default LeadEscalatedQueuePage;
