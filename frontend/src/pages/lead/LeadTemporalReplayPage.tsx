import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RotateCcw,
  CheckCircle2,
  GitCompare,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useDemoScenario } from '@/features/demo/demoContext';

interface TemporalRuleDiff {
  code: string;
  title: string;
  sourceConnector: string;
  sourceSnapshotHash: string;
  run1Status: 'SATISFIED' | 'DEFICIENT' | 'UNABLE_TO_DETERMINE';
  run1Observed: string;
  run2Status: 'SATISFIED' | 'DEFICIENT' | 'UNABLE_TO_DETERMINE';
  run2Observed: string;
  isIdempotent: boolean;
  deltaReason: string;
}

export const LeadTemporalReplayPage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, resetDemo } = useDemoScenario();
  const [selectedRuleCode, setSelectedRuleCode] = useState<string>('EOA-SD-04');

  const isRectified = demoState.activeRevisionNumber >= 2;

  // Exact 6 registered synthetic source snapshots pinned across runs
  const pinnedSources = [
    { code: 'SRC_AICTE_PORTAL', hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', status: 'PINNED_MATCH' },
    { code: 'SRC_REVENUE_LAND', hash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4', status: 'PINNED_MATCH' },
    { code: 'SRC_MUNICIPAL_BLDG', hash: '6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090', status: 'PINNED_MATCH' },
    { code: 'SRC_FIRE_SERVICES', hash: 'bcae56e22dd318d189ced5952f1e0df1e15fa52bf658826703f8a4cb75d1d648', status: 'PINNED_MATCH' },
    { code: 'SRC_ICAI_UDIN', hash: '5b922079de9ff9c025d50616999a01fdbe152f281260492cb47065ffef6b86cd', status: 'PINNED_MATCH' },
    { code: 'SRC_BHUVAN_GEOMAP', hash: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069', status: 'PINNED_MATCH' },
  ];

  const ruleDiffs: TemporalRuleDiff[] = [
    {
      code: 'EOA-SD-01',
      title: 'Affidavit 2 (₹100 e-Stamp, Notarized, Signatory Authority)',
      sourceConnector: 'SRC_AICTE_PORTAL',
      sourceSnapshotHash: 'e3b0c442...b855',
      run1Status: 'UNABLE_TO_DETERMINE',
      run1Observed: 'Signatory format ambiguity with portal registration',
      run2Status: 'UNABLE_TO_DETERMINE',
      run2Observed: 'Signatory format ambiguity with portal registration',
      isIdempotent: true,
      deltaReason: 'Source snapshot and document bundle unchanged.',
    },
    {
      code: 'EOA-SD-02',
      title: 'Processing Fee Payment / Exemption Verification',
      sourceConnector: 'SRC_AICTE_PORTAL',
      sourceSnapshotHash: 'e3b0c442...b855',
      run1Status: 'UNABLE_TO_DETERMINE',
      run1Observed: 'Authoritative exemption record unconfirmed in snapshot',
      run2Status: 'UNABLE_TO_DETERMINE',
      run2Observed: 'Authoritative exemption record unconfirmed in snapshot',
      isIdempotent: true,
      deltaReason: 'Source snapshot unchanged.',
    },
    {
      code: 'EOA-SD-03',
      title: 'Land Ownership & Registration Documents',
      sourceConnector: 'SRC_REVENUE_LAND',
      sourceSnapshotHash: '8f434346...7aa4',
      run1Status: 'DEFICIENT',
      run1Observed: '7.20 Acres confirmed in State Revenue registry',
      run2Status: 'DEFICIENT',
      run2Observed: '7.20 Acres confirmed in State Revenue registry',
      isIdempotent: true,
      deltaReason: 'Unchanged 3.30-acre contradiction with State Revenue.',
    },
    {
      code: 'EOA-SD-04',
      title: 'Building Plan Approval & Structural Stability Certificate',
      sourceConnector: 'SRC_MUNICIPAL_BLDG',
      sourceSnapshotHash: '6ca13d52...8090',
      run1Status: 'DEFICIENT',
      run1Observed: 'Structural Stability Certificate missing for > 30 yr structure',
      run2Status: isRectified ? 'SATISFIED' : 'DEFICIENT',
      run2Observed: isRectified
        ? 'Structural Stability Certificate attached: Structural_Stability_Certificate_2026.pdf (Valid through 2031)'
        : 'Structural Stability Certificate missing for > 30 yr structure',
      isIdempotent: !isRectified,
      deltaReason: isRectified
        ? 'Status shifted DEFICIENT -> SATISFIED due to verified replacement evidence in Revision 2.'
        : 'Awaiting replacement document upload.',
    },
    {
      code: 'EOA-SD-05',
      title: 'Fire Safety Certificate / NOC from Competent Authority',
      sourceConnector: 'SRC_FIRE_SERVICES',
      sourceSnapshotHash: 'bcae56e2...d648',
      run1Status: 'DEFICIENT',
      run1Observed: 'No active NOC record found in State Fire Directorate',
      run2Status: 'DEFICIENT',
      run2Observed: 'No active NOC record found in State Fire Directorate',
      isIdempotent: true,
      deltaReason: 'Fire Directorate registry search remains deficient.',
    },
    {
      code: 'EOA-SD-06',
      title: 'Satellite Map with Geocoordinates & Demarcated Site Boundaries',
      sourceConnector: 'SRC_BHUVAN_GEOMAP',
      sourceSnapshotHash: '7f83b165...9069',
      run1Status: 'UNABLE_TO_DETERMINE',
      run1Observed: 'Partial satellite obstruction; boundary confirmation inconclusive',
      run2Status: 'UNABLE_TO_DETERMINE',
      run2Observed: 'Partial satellite obstruction; boundary confirmation inconclusive',
      isIdempotent: true,
      deltaReason: 'Monsoon cloud obstruction identical across snapshot replay.',
    },
    {
      code: 'EOA-SD-07',
      title: 'Audited Financial Statement with ICAI UDIN & Signatures',
      sourceConnector: 'SRC_ICAI_UDIN',
      sourceSnapshotHash: '5b922079...86cd',
      run1Status: 'DEFICIENT',
      run1Observed: 'UDIN not registered in ICAI portal database',
      run2Status: 'DEFICIENT',
      run2Observed: 'UDIN not registered in ICAI portal database',
      isIdempotent: true,
      deltaReason: 'ICAI registry verification result deterministic.',
    },
  ];

  const activeRule = ruleDiffs.find((r) => r.code === selectedRuleCode) || ruleDiffs[3];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Temporal Compliance Replay</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <RotateCcw className="w-6 h-6 text-primary" />
            Temporal Compliance Replay &amp; Evaluation Idempotency
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
            <GitCompare className="w-3.5 h-3.5 mr-1" />
            Case Review Dossier
          </Button>
        </div>
      </div>

      {/* Idempotency & Pinned Source Guarantee Banner */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
            <Database className="w-4 h-4 text-primary" />
            Pinned Synthetic Source Registry Invariant (6 Registered Connectors)
          </h2>
          <Badge variant="outline" className="text-xs font-mono border-emerald-400 text-emerald-700 bg-emerald-50">
            6/6 SNAPSHOTS BIT-IDENTICAL
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Evaluation idempotency is guaranteed: both ValidationRun #1 and ValidationRun #2 evaluate against the exact same cryptographic SHA-256 source snapshots. Any shift in compliance status is solely attributable to newly ingested applicant replacement evidence.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 pt-1 font-mono text-[10px]">
          {pinnedSources.map((s) => (
            <div key={s.code} className="p-2 rounded bg-muted/40 border space-y-0.5">
              <span className="font-bold text-foreground block truncate">{s.code}</span>
              <span className="text-muted-foreground block text-[9px] truncate">{s.hash.slice(0, 12)}...</span>
              <span className="text-emerald-700 block font-semibold text-[9px]">MATCH [SIMULATED]</span>
            </div>
          ))}
        </div>
      </div>

      {/* Side-by-Side Validation Run Diff Table */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs overflow-hidden">
        <div className="p-4 border-b bg-muted/40 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-sm text-foreground">
              Rule-by-Rule Outcome Diff: Run #1 (Initial) vs Run #2 (Rectified)
            </h3>
            <p className="text-xs text-muted-foreground">
              Proves deterministic reproducibility across all 7 statutory rules
            </p>
          </div>
          <Badge
            variant="outline"
            className={
              isRectified
                ? 'border-emerald-500 text-emerald-700 bg-emerald-50 text-xs font-semibold'
                : 'text-xs text-muted-foreground'
            }
          >
            {isRectified ? '1 Rule Status Shift Detected' : 'All Rules Strictly Idempotent'}
          </Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b bg-muted/20 font-semibold text-muted-foreground">
                <th className="py-3 px-4">Rule Code</th>
                <th className="py-3 px-4">Requirement Area</th>
                <th className="py-3 px-4">Run #1 (Rev 1)</th>
                <th className="py-3 px-4">Run #2 (Rev 2)</th>
                <th className="py-3 px-4">Replay Delta</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {ruleDiffs.map((r) => (
                <tr
                  key={r.code}
                  className={`hover:bg-muted/30 transition-colors cursor-pointer ${
                    selectedRuleCode === r.code ? 'bg-primary/5' : ''
                  }`}
                  onClick={() => setSelectedRuleCode(r.code)}
                >
                  <td className="py-3 px-4 font-mono font-bold text-foreground">
                    {r.code}
                  </td>
                  <td className="py-3 px-4 font-medium text-foreground">
                    {r.title}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={
                        r.run1Status === 'DEFICIENT'
                          ? 'border-red-400 text-red-700 bg-red-50 text-[10px]'
                          : 'border-amber-400 text-amber-700 bg-amber-50 text-[10px]'
                      }
                    >
                      {r.run1Status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={
                        r.run2Status === 'SATISFIED'
                          ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-bold text-[10px]'
                          : r.run2Status === 'DEFICIENT'
                          ? 'border-red-400 text-red-700 bg-red-50 text-[10px]'
                          : 'border-amber-400 text-amber-700 bg-amber-50 text-[10px]'
                      }
                    >
                      {r.run2Status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    {r.run1Status !== r.run2Status ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-300">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        DEFICIENT &rarr; SATISFIED
                      </span>
                    ) : (
                      <span className="text-[11px] text-muted-foreground font-mono">
                        IDEMPOTENT (NO SHIFT)
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 text-[11px] px-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedRuleCode(r.code);
                      }}
                    >
                      Compare Details
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Rule Deep Dive Comparison */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-sm bg-muted px-2.5 py-1 rounded border">
              {activeRule.code}
            </span>
            <h3 className="font-bold text-sm text-foreground">
              {activeRule.title}
            </h3>
          </div>
          <span className="text-xs text-muted-foreground font-mono">
            Pinned Source: {activeRule.sourceConnector}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-4 rounded-md border bg-muted/30 space-y-2">
            <div className="flex items-center justify-between font-bold text-foreground font-sans">
              <span>Run #1 Observed Payload (Revision 1):</span>
              <Badge variant="outline" className="text-[10px]">{activeRule.run1Status}</Badge>
            </div>
            <p className="text-muted-foreground leading-relaxed font-sans text-xs">
              {activeRule.run1Observed}
            </p>
          </div>

          <div className="p-4 rounded-md border bg-muted/30 space-y-2">
            <div className="flex items-center justify-between font-bold text-foreground font-sans">
              <span>Run #2 Observed Payload (Revision 2):</span>
              <Badge
                variant="outline"
                className={
                  activeRule.run2Status === 'SATISFIED'
                    ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-bold text-[10px]'
                    : 'text-[10px]'
                }
              >
                {activeRule.run2Status}
              </Badge>
            </div>
            <p className="text-muted-foreground leading-relaxed font-sans text-xs">
              {activeRule.run2Observed}
            </p>
          </div>
        </div>

        <div className="rounded-md border p-3 bg-muted/20 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">Replay Verification Rationale: </span>
          {activeRule.deltaReason}
        </div>
      </div>
    </div>
  );
};
export default LeadTemporalReplayPage;
