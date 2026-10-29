import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Award,
  ShieldAlert,
  CheckCircle2,
  ClipboardList,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useDemoScenario } from '@/features/demo/demoContext';

type DispositionType = 'PROCEED' | 'HOLD' | 'INSPECTION' | 'RETURN';

export const LeadRecommendationsPage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, recordLeadDisposition, resetDemo } = useDemoScenario();

  const [selectedDisposition, setSelectedDisposition] = useState<DispositionType>(
    demoState.leadDisposition?.disposition || 'INSPECTION'
  );
  const [rationale, setRationale] = useState<string>(
    demoState.leadDisposition?.rationale ||
      'Due to unresolved land registry variance on Survey No. 74/2A (10.50 declared vs 7.20 registered in State Revenue) and absence of Fire Directorate clearance, an on-site physical inspection committee is required to verify actual campus ground boundaries and life safety installations prior to committee decision.'
  );
  const [hasAffirmed, setHasAffirmed] = useState<boolean>(Boolean(demoState.leadDisposition));
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const isAlreadyRecorded = Boolean(demoState.leadDisposition);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDisposition || rationale.trim().length < 10 || !hasAffirmed) return;

    setIsSubmitting(true);
    setTimeout(() => {
      recordLeadDisposition(
        selectedDisposition,
        rationale.trim(),
        'Dr. H. V. Verma (Lead Auditor)'
      );
      setIsSubmitting(false);
    }, 500);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Supervisory Review Disposition</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Award className="w-6 h-6 text-primary" />
            Supervisory Case Disposition &amp; Recommendations
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
        </div>
      </div>

      {/* Statutory Boundary Notice Banner */}
      <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-xs text-foreground leading-relaxed flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-bold text-xs uppercase tracking-wide block">
            Statutory AICTE Advisory Boundary Notice
          </span>
          <p className="text-muted-foreground">
            AIC-Flow generates evidence triangulation signals, discrepancy indices, and document verification hashes. Recommendations recorded here represent internal supervisory workflow dispositions and do not constitute a statutory regulatory decision. Final statutory approval authority rests exclusively with the competent statutory committees of the All India Council for Technical Education.
          </p>
        </div>
      </div>

      {/* Disposition Form */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-6">
        <div>
          <h2 className="text-base font-bold tracking-tight text-foreground">
            Formulate Supervisory Recommendation
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Based on the multi-evaluator review of Revision 1 and Revision 2 findings, select the internal disposition for the regional committee docket.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Radio Options */}
          <div className="space-y-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              1. Select Internal Workflow Disposition
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Option: INSPECTION */}
              <div
                onClick={() => !isAlreadyRecorded && setSelectedDisposition('INSPECTION')}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  selectedDisposition === 'INSPECTION'
                    ? 'border-purple-500 bg-purple-50/50 shadow-xs'
                    : 'border-border hover:bg-muted/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-foreground">
                    Refer for Physical On-Site Inspection
                  </span>
                  <input
                    type="radio"
                    name="disposition"
                    checked={selectedDisposition === 'INSPECTION'}
                    onChange={() => setSelectedDisposition('INSPECTION')}
                    disabled={isAlreadyRecorded}
                    className="accent-purple-600"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Substantial land or fire safety discrepancy requires physical expert verification on site.
                </p>
              </div>

              {/* Option: HOLD */}
              <div
                onClick={() => !isAlreadyRecorded && setSelectedDisposition('HOLD')}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  selectedDisposition === 'HOLD'
                    ? 'border-amber-500 bg-amber-50/50 shadow-xs'
                    : 'border-border hover:bg-muted/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-foreground">
                    Hold for Supplemental Evidence
                  </span>
                  <input
                    type="radio"
                    name="disposition"
                    checked={selectedDisposition === 'HOLD'}
                    onChange={() => setSelectedDisposition('HOLD')}
                    disabled={isAlreadyRecorded}
                    className="accent-amber-600"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Request certified municipal extracts or audited financial affirmations before deciding.
                </p>
              </div>

              {/* Option: PROCEED */}
              <div
                onClick={() => !isAlreadyRecorded && setSelectedDisposition('PROCEED')}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  selectedDisposition === 'PROCEED'
                    ? 'border-emerald-500 bg-emerald-50/50 shadow-xs'
                    : 'border-border hover:bg-muted/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-foreground">
                    Proceed to Regional Committee
                  </span>
                  <input
                    type="radio"
                    name="disposition"
                    checked={selectedDisposition === 'PROCEED'}
                    onChange={() => setSelectedDisposition('PROCEED')}
                    disabled={isAlreadyRecorded}
                    className="accent-emerald-600"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  All critical statutory items are satisfied or fall within approved discretionary limits.
                </p>
              </div>

              {/* Option: RETURN */}
              <div
                onClick={() => !isAlreadyRecorded && setSelectedDisposition('RETURN')}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  selectedDisposition === 'RETURN'
                    ? 'border-slate-500 bg-slate-50 shadow-xs'
                    : 'border-border hover:bg-muted/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-foreground">
                    Return to Reviewing Auditor
                  </span>
                  <input
                    type="radio"
                    name="disposition"
                    checked={selectedDisposition === 'RETURN'}
                    onChange={() => setSelectedDisposition('RETURN')}
                    disabled={isAlreadyRecorded}
                    className="accent-slate-600"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Re-evaluate candidate text or query portal snapshot connectors for updated records.
                </p>
              </div>
            </div>
          </div>

          {/* Supervisory Rationale */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              2. Supervisory Rationale &amp; Findings Justification (Required, min 10 chars)
            </label>
            <Textarea
              rows={4}
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              disabled={isAlreadyRecorded}
              className="text-xs font-sans leading-relaxed"
              placeholder="State the regulatory basis, clause reference, and reasons supporting this disposition..."
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{rationale.trim().length} / 10 minimum characters</span>
              <span>All dispositions are signed with cryptographic hash anchoring</span>
            </div>
          </div>

          {/* Affirmation Checkbox */}
          <div className="flex items-start gap-2.5 pt-2 border-t">
            <input
              type="checkbox"
              id="affirm"
              checked={hasAffirmed}
              onChange={(e) => setHasAffirmed(e.target.checked)}
              disabled={isAlreadyRecorded}
              className="mt-1 accent-primary"
            />
            <label htmlFor="affirm" className="text-xs text-foreground leading-normal cursor-pointer select-none">
              I affirm that this supervisory review is formulated strictly in conformity with AICTE Approval Process Handbook (APH 2024–2027) statutory norms, and all audit actions are permanently recorded to the regulatory ledger.
            </label>
          </div>

          {/* Form Actions */}
          <div className="pt-2 flex items-center justify-between border-t">
            {isAlreadyRecorded ? (
              <div className="flex items-center gap-2 text-xs text-emerald-700 font-semibold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Disposition Recorded &bull; Immutable Ledger Hash Anchored
              </div>
            ) : (
              <span className="text-xs text-muted-foreground">
                Action requires lead auditor role credentials
              </span>
            )}

            <div className="flex items-center gap-2">
              {selectedDisposition === 'INSPECTION' && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs h-8 text-purple-700 border-purple-300 hover:bg-purple-50"
                  onClick={() => navigate('/lead/inspection-referrals')}
                >
                  <ClipboardList className="w-3.5 h-3.5 mr-1" />
                  Inspection Referral Generator
                </Button>
              )}

              {!isAlreadyRecorded && (
                <Button
                  type="submit"
                  disabled={!selectedDisposition || rationale.trim().length < 10 || !hasAffirmed || isSubmitting}
                  className="text-xs h-8 bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  {isSubmitting ? 'Recording...' : 'Record Official Disposition'}
                </Button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
export default LeadRecommendationsPage;
