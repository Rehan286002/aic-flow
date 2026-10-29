import React, { useState, useId } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Lock, ShieldAlert, CheckCircle2, AlertTriangle } from 'lucide-react';
import type { FindingRead, FindingStatus } from '../types';
import { PERMITTED_FINDING_TRANSITIONS } from '../types';
export { PERMITTED_FINDING_TRANSITIONS };

interface FindingActionModalProps {
  finding: FindingRead | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmitStatusUpdate?: (findingId: string, targetStatus: FindingStatus, rationale: string) => Promise<void>;
  isReadOnly?: boolean;
}

export const FindingActionModal: React.FC<FindingActionModalProps> = ({
  finding,
  isOpen,
  onClose,
  onSubmitStatusUpdate,
  isReadOnly = false,
}) => {
  const [targetStatus, setTargetStatus] = useState<FindingStatus | ''>('');
  const [rationale, setRationale] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const statusSelectId = useId();
  const rationaleId = useId();

  if (!finding) return null;

  const permittedTransitions = PERMITTED_FINDING_TRANSITIONS[finding.status] || [];
  const nonWsLength = rationale.replace(/\s+/g, '').length;
  const isRationaleValid = nonWsLength >= 5;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isReadOnly) return;
    if (!targetStatus || !isRationaleValid) {
      setErrorMsg('A valid target status and at least 5 non-whitespace characters of rationale are required.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      if (onSubmitStatusUpdate) {
        await onSubmitStatusUpdate(finding.finding_id, targetStatus as FindingStatus, rationale.trim());
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update finding status.';
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="font-mono text-[10px]">
              {finding.category}
            </Badge>
            <Badge
              variant={
                finding.severity === 'CRITICAL'
                  ? 'destructive'
                  : finding.severity === 'HIGH'
                  ? 'default'
                  : 'secondary'
              }
              className="text-[10px] font-bold uppercase"
            >
              {finding.severity}
            </Badge>
            <Badge variant="outline" className="text-[10px] font-semibold">
              Current Status: {finding.status}
            </Badge>
          </div>
          <DialogTitle className="text-base font-semibold leading-snug mt-1">
            {finding.title}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Authoritative auditor triage and formal status transition recorded in the compliance audit ledger.
          </DialogDescription>
        </DialogHeader>

        {/* Read-Only Reference Run Safeguard Banner */}
        {isReadOnly ? (
          <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-800 dark:text-amber-300">
            <Lock className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Apex Reference Run (Read-Only Baseline)</p>
              <p className="text-[11px] text-amber-700 dark:text-amber-400 mt-0.5">
                The historical validation run for Apex Institute is an immutable regulatory record. Status mutations
                are disabled for this reference dataset. Use the interactive evaluation scenario to demonstrate live
                triage actions.
              </p>
            </div>
          </div>
        ) : null}

        {/* Finding Internal Reason & Historical Rationale */}
        <div className="space-y-2 text-xs">
          <Label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Current Regulatory Observation & Audit Reason
          </Label>
          <div className="p-3 rounded-md bg-muted/40 border border-border/60 text-foreground font-mono text-[11px] whitespace-pre-wrap max-h-40 overflow-y-auto">
            {finding.internal_reason || 'No internal reason recorded.'}
          </div>
        </div>

        {/* Attached Evidence Items */}
        {finding.evidence && finding.evidence.length > 0 && (
          <div className="space-y-1.5 text-xs">
            <Label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              <ShieldAlert className="h-3 w-3 text-primary" /> Attached Evidence Records ({finding.evidence.length})
            </Label>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {finding.evidence.map((ev) => (
                <div
                  key={ev.finding_evidence_id}
                  className="p-2 rounded bg-card border border-border/60 text-[11px] flex items-center justify-between"
                >
                  <span className="font-mono text-muted-foreground">{ev.evidence_type}</span>
                  <span className="truncate max-w-64 font-medium">{ev.evidence_summary || ev.evidence_reference}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(ev.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Triage Form (Active only when NOT read-only) */}
        {!isReadOnly && (
          <form onSubmit={handleSubmit} className="space-y-3 pt-2 border-t border-border/60">
            {errorMsg && (
              <div className="p-2.5 rounded bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor={statusSelectId} className="text-xs font-semibold">
                Target Review Status <span className="text-destructive">*</span>
              </Label>
              {permittedTransitions.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">
                  This finding is in terminal status ({finding.status}) and cannot be transitioned.
                </p>
              ) : (
                <Select
                  value={targetStatus}
                  onValueChange={(val) => setTargetStatus(val as FindingStatus)}
                >
                  <SelectTrigger id={statusSelectId} className="text-xs h-9">
                    <SelectValue placeholder="Select permitted status transition..." />
                  </SelectTrigger>
                  <SelectContent>
                    {permittedTransitions.map((st) => (
                      <SelectItem key={st} value={st} className="text-xs">
                        {st.replace(/_/g, ' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor={rationaleId} className="text-xs font-semibold">
                  Auditor Review Rationale <span className="text-destructive">*</span>
                </Label>
                <span
                  className={`text-[11px] font-mono ${
                    isRationaleValid ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-muted-foreground'
                  }`}
                >
                  Non-whitespace: {nonWsLength} / 5 required
                </span>
              </div>
              <Textarea
                id={rationaleId}
                placeholder="Enter formal justification for this status change (minimum 5 non-whitespace characters)..."
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                rows={3}
                className="text-xs"
              />
            </div>

            <DialogFooter className="pt-2 gap-2">
              <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={!targetStatus || !isRationaleValid || isSubmitting}
                className="gap-1.5"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {isSubmitting ? 'Recording Action...' : 'Record Audit Decision'}
              </Button>
            </DialogFooter>
          </form>
        )}

        {isReadOnly && (
          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              Close Inspection View
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};
