import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileSearch,
  Clock,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  GitCompare,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useDemoScenario } from '@/features/demo/demoContext';

export const LeadCaseReviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, resetDemo } = useDemoScenario();

  const isRectified = demoState.activeRevisionNumber >= 2;

  // Static baseline comparisons for the 7 Annexure 2.1 items
  const comparisons = [
    {
      code: 'EOA-SD-01',
      title: 'Affidavit 2 (Notarized ₹100 Stamp)',
      rev1Status: 'UNABLE_TO_DETERMINE',
      rev2Status: 'UNABLE_TO_DETERMINE',
      delta: 'UNCHANGED',
      notes: 'Signatory authority format ambiguity remains under review.',
    },
    {
      code: 'EOA-SD-02',
      title: 'Application Processing Fee / Exemption',
      rev1Status: 'UNABLE_TO_DETERMINE',
      rev2Status: 'UNABLE_TO_DETERMINE',
      delta: 'UNCHANGED',
      notes: 'Authoritative exemption record unconfirmed in snapshot.',
    },
    {
      code: 'EOA-SD-03',
      title: 'Land Ownership & State Revenue Registration',
      rev1Status: 'DEFICIENT',
      rev2Status: 'DEFICIENT',
      delta: 'UNCHANGED',
      notes: 'Declared 10.50 acres vs State Revenue registry 7.20 acres.',
    },
    {
      code: 'EOA-SD-04',
      title: 'Structural Stability Certificate (> 30 Years)',
      rev1Status: 'DEFICIENT',
      rev2Status: isRectified ? 'SATISFIED' : 'DEFICIENT',
      delta: isRectified ? 'RESOLVED' : 'UNCHANGED',
      notes: isRectified
        ? 'Rectified in Revision 2: Valid certificate uploaded (NBC 2016 compliant through 2031).'
        : 'Missing structural stability certificate for building constructed in 1990.',
    },
    {
      code: 'EOA-SD-05',
      title: 'Fire Safety NOC (Competent Authority)',
      rev1Status: 'DEFICIENT',
      rev2Status: 'DEFICIENT',
      delta: 'UNCHANGED',
      notes: 'No active NOC record found in State Fire Services Directorate.',
    },
    {
      code: 'EOA-SD-06',
      title: 'Satellite Demarcation Map (Bhuvan)',
      rev1Status: 'UNABLE_TO_DETERMINE',
      rev2Status: 'UNABLE_TO_DETERMINE',
      delta: 'UNCHANGED',
      notes: 'Cloud cover obscurity; boundary inspection recommended.',
    },
    {
      code: 'EOA-SD-07',
      title: 'Audited Balance Sheet & ICAI UDIN',
      rev1Status: 'DEFICIENT',
      rev2Status: 'DEFICIENT',
      delta: 'UNCHANGED',
      notes: 'UDIN 24056781ABCD1234 not registered in ICAI portal database.',
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Case Review Dossier</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <FileSearch className="w-6 h-6 text-primary" />
            Supervisory Cross-Evaluator Case Review
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
            className="text-xs h-8 bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={() => navigate('/lead/recommendations')}
          >
            Record Formal Disposition
            <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </div>
      </div>

      {/* Split Pane: Timeline (Left) & Cross-Revision Diff (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Pane: Audit History Timeline (5 cols) */}
        <div className="lg:col-span-5 rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <h2 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              Chronological Audit Trail
            </h2>
            <Badge variant="outline" className="text-[10px] font-mono">
              {demoState.auditLedger.length} Events
            </Badge>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
            {demoState.auditLedger.map((evt) => (
              <div key={evt.sequenceNo} className="relative space-y-1">
                <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-primary border-2 border-background" />
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-foreground font-mono">
                    #{evt.sequenceNo} &bull; {evt.action}
                  </span>
                  <span className="text-muted-foreground text-[10px]">
                    {new Date(evt.occurredAt).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {evt.details}
                </p>
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground pt-0.5">
                  <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                  <span className="truncate max-w-[200px]" title={evt.currentHash}>
                    Hash: {evt.currentHash.slice(0, 16)}...
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Pane: Cross-Evaluator Revision Comparison (7 cols) */}
        <div className="lg:col-span-7 rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <h2 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-primary" />
              Revision #1 vs Revision #2 Evaluation Outcome Matrix
            </h2>
            <Badge
              variant="outline"
              className={
                isRectified
                  ? 'border-emerald-400 text-emerald-700 bg-emerald-50 text-[10px] font-semibold'
                  : 'text-[10px] text-muted-foreground'
              }
            >
              {isRectified ? '1 Deficiency Resolved in Rev #2' : 'Baseline Rev #1 Active'}
            </Badge>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b bg-muted/40 font-semibold text-muted-foreground">
                  <th className="py-2.5 px-3">Item</th>
                  <th className="py-2.5 px-3">Revision #1</th>
                  <th className="py-2.5 px-3">Revision #2</th>
                  <th className="py-2.5 px-3">Status Diff</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {comparisons.map((c) => (
                  <tr key={c.code} className="hover:bg-muted/30 transition-colors">
                    <td className="py-2.5 px-3">
                      <span className="font-mono font-bold text-foreground block">
                        {c.code}
                      </span>
                      <span className="text-[11px] text-muted-foreground truncate max-w-[160px] block">
                        {c.title}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <Badge
                        variant="outline"
                        className={
                          c.rev1Status === 'DEFICIENT'
                            ? 'border-red-400 text-red-700 bg-red-50 text-[10px]'
                            : 'border-amber-400 text-amber-700 bg-amber-50 text-[10px]'
                        }
                      >
                        {c.rev1Status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <Badge
                        variant="outline"
                        className={
                          c.rev2Status === 'SATISFIED'
                            ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-bold text-[10px]'
                            : c.rev2Status === 'DEFICIENT'
                            ? 'border-red-400 text-red-700 bg-red-50 text-[10px]'
                            : 'border-amber-400 text-amber-700 bg-amber-50 text-[10px]'
                        }
                      >
                        {c.rev2Status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {c.delta === 'RESOLVED' ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-300">
                          <CheckCircle2 className="w-3 h-3" />
                          RESOLVED
                        </span>
                      ) : (
                        <span className="text-[11px] text-muted-foreground font-mono">
                          UNCHANGED
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-md border p-3 bg-muted/30 text-xs text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground block mb-0.5">
              Supervisory Review Observation:
            </span>
            Requirement <span className="font-mono font-semibold text-foreground">EOA-SD-04</span> has been successfully resolved through valid replacement documentation. However, <span className="font-mono font-semibold text-foreground">EOA-SD-03</span> (Land Area Discrepancy) and <span className="font-mono font-semibold text-foreground">EOA-SD-05</span> (Fire NOC) remain deficient. Proceed to Supervisory Disposition to decide whether to hold or refer for physical inspection.
          </div>
        </div>
      </div>
    </div>
  );
};
export default LeadCaseReviewPage;
