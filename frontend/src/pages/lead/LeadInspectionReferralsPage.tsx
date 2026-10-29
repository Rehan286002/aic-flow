import React, { useState } from 'react';
import {
  ClipboardList,
  Printer,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useDemoScenario } from '@/features/demo/demoContext';

export const LeadInspectionReferralsPage: React.FC = () => {
  const { demoState, generateInspectionReferral, resetDemo } = useDemoScenario();

  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    'State Revenue Land Demarcation & Perimeter Survey',
    'Fire Safety Clearances & Active Pump Installation',
  ]);
  const [startDate, setStartDate] = useState('2026-11-15');
  const [endDate, setEndDate] = useState('2026-11-20');
  const [instructions, setInstructions] = useState(
    'Verify physical boundaries of Survey No. 74/2A to resolve 3.30-acre contradiction with State Revenue records. Inspect working condition of automatic sprinkler riser and verify fire clearance issuance status with local division chief.'
  );
  const [isGenerated, setIsGenerated] = useState(Boolean(demoState.inspectionReferral));

  const toggleScope = (scope: string) => {
    if (selectedScopes.includes(scope)) {
      setSelectedScopes(selectedScopes.filter((s) => s !== scope));
    } else {
      setSelectedScopes([...selectedScopes, scope]);
    }
  };

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedScopes.length === 0 || instructions.trim().length < 10) return;

    generateInspectionReferral(selectedScopes, startDate, endDate, instructions.trim());
    setIsGenerated(true);
  };

  const referral = demoState.inspectionReferral;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Physical Inspection Operations</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <ClipboardList className="w-6 h-6 text-primary" />
            Physical On-Site Inspection Referral Generator
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

          {isGenerated && (
            <Button
              size="sm"
              variant="outline"
              className="text-xs h-8"
              onClick={() => window.print()}
            >
              <Printer className="w-3.5 h-3.5 mr-1" />
              Print Official Memo
            </Button>
          )}
        </div>
      </div>

      {/* Generator Form */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-6">
        <div>
          <h2 className="text-base font-bold tracking-tight text-foreground">
            Configure Inspection Scope &amp; Target Committee Window
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Issued under AICTE Approval Process Handbook (APH 2024–2027) Chapter II for physical ground verification by designated expert committee members.
          </p>
        </div>

        <form onSubmit={handleGenerate} className="space-y-6">
          {/* Scope Checkboxes */}
          <div className="space-y-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              1. Designated Inspection Scopes (Select at least one)
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {[
                'State Revenue Land Demarcation & Perimeter Survey',
                'Fire Safety Clearances & Active Pump Installation',
                'Building Stability & Structural Engineering Inspection',
                'Satellite Boundary Geocoordinate Ground Ground-Truthing',
                'Laboratory Equipment & Instructional Area Verification',
                'Computer Centre & Digital Infrastructure Auditing',
              ].map((scope) => {
                const isChecked = selectedScopes.includes(scope);
                return (
                  <div
                    key={scope}
                    onClick={() => toggleScope(scope)}
                    className={`border rounded-lg p-3 cursor-pointer transition-colors flex items-center gap-2.5 ${
                      isChecked
                        ? 'border-purple-400 bg-purple-50/40 text-purple-950 font-medium'
                        : 'border-border hover:bg-muted/40 text-muted-foreground'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="accent-purple-600 rounded"
                    />
                    <span className="text-xs">{scope}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Date Window */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
                Target Start Date
              </label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="text-xs font-mono"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
                Target Completion Date
              </label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="text-xs font-mono"
              />
            </div>
          </div>

          {/* Instructions */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              Special Instructions for Expert Inspection Committee
            </label>
            <Textarea
              rows={3}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              className="text-xs font-sans leading-relaxed"
            />
          </div>

          <div className="flex justify-end pt-2 border-t">
            <Button
              type="submit"
              disabled={selectedScopes.length === 0 || instructions.trim().length < 10}
              className="text-xs h-8 bg-purple-700 hover:bg-purple-800 text-white"
            >
              <ClipboardList className="w-3.5 h-3.5 mr-1" />
              Generate Official Inspection Referral Memo
            </Button>
          </div>
        </form>
      </div>

      {/* Official Memo Preview (Print-Ready) */}
      {(isGenerated || referral) && (
        <div className="rounded-lg border bg-white text-slate-900 shadow-sm p-8 space-y-6 font-serif print:border-none print:shadow-none">
          {/* Memo Header */}
          <div className="border-b-2 border-slate-900 pb-4 text-center space-y-1">
            <span className="text-xs uppercase tracking-widest font-sans font-bold text-slate-600 block">
              All India Council for Technical Education
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-950 font-sans">
              EXPERT COMMITTEE PHYSICAL INSPECTION REFERRAL MEMO
            </h2>
            <div className="flex justify-between items-center text-xs font-mono text-slate-600 pt-2 font-sans">
              <span>Ref No: {referral?.referenceNumber || 'INSP-REF-2026-4482'}</span>
              <span>Date: {new Date().toLocaleDateString()}</span>
            </div>
          </div>

          {/* Memo Details */}
          <div className="space-y-4 text-xs font-sans">
            <div className="grid grid-cols-2 gap-4 border p-3 rounded bg-slate-50">
              <div>
                <span className="text-slate-500 block text-[10px] uppercase">Institution</span>
                <span className="font-bold text-slate-900">{demoState.institutionName}</span>
                <span className="text-slate-600 block text-[11px]">AICTE ID: {demoState.institutionId}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase">Filing Reference</span>
                <span className="font-bold text-slate-900">{demoState.applicationNumber}</span>
                <span className="text-slate-600 block text-[11px]">Academic Year: {demoState.academicYear}</span>
              </div>
            </div>

            <div className="space-y-2">
              <span className="font-bold uppercase tracking-wider text-[11px] text-slate-700 block">
                Designated Verification Mandates:
              </span>
              <ul className="list-disc pl-5 space-y-1 text-slate-800 text-xs">
                {(referral?.scope || selectedScopes).map((s) => (
                  <li key={s} className="font-medium">{s}</li>
                ))}
              </ul>
            </div>

            <div className="space-y-1 border-t pt-3">
              <span className="font-bold uppercase tracking-wider text-[11px] text-slate-700 block">
                Target Physical Inspection Period:
              </span>
              <p className="text-slate-800 font-mono text-xs">
                {referral?.targetStartDate || startDate} through {referral?.targetEndDate || endDate}
              </p>
            </div>

            <div className="space-y-1 border-t pt-3">
              <span className="font-bold uppercase tracking-wider text-[11px] text-slate-700 block">
                Special Directives:
              </span>
              <p className="text-slate-800 italic text-xs leading-relaxed">
                &ldquo;{referral?.instructions || instructions}&rdquo;
              </p>
            </div>

            <div className="pt-8 flex justify-between items-end border-t text-xs">
              <div>
                <div className="flex items-center gap-1.5 text-emerald-800 font-mono text-[11px]">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Digitally Anchored in Regulatory Ledger</span>
                </div>
                <span className="text-slate-500 text-[10px]">Verification Engine Batch 3 &bull; SHA-256 Provenance</span>
              </div>
              <div className="text-right space-y-1">
                <div className="font-serif italic text-sm font-semibold">Dr. H. V. Verma</div>
                <span className="text-slate-700 font-bold block text-[11px]">Lead Regulatory Auditor</span>
                <span className="text-slate-500 block text-[10px]">Western Regional Compliance Directorate</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default LeadInspectionReferralsPage;
