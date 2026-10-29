import React, { useState } from 'react';
import {
  FileCode,
  Eye,
  Search,
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
} from '@/components/ui/dialog';

interface RegulatoryRuleCatalogItem {
  code: string;
  name: string;
  version: number;
  statutoryClause: string;
  aphCitation: string;
  evaluatorClass: string;
  status: 'ACTIVE' | 'DEPRECATED';
  effectiveFrom: string;
  sourceConnector: string;
  inputsRequired: string[];
  evaluationLogicSummary: string;
}

export const AdminRulesPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRule, setSelectedRule] = useState<RegulatoryRuleCatalogItem | null>(null);

  const rules: RegulatoryRuleCatalogItem[] = [
    {
      code: 'EOA-SD-01',
      name: 'Affidavit 2 Legal Affirmation & Signatory Authority',
      version: 1,
      statutoryClause: 'Annexure 2.1 Item (i): Legal Undertaking',
      aphCitation: 'AICTE APH 2024–2027, p. 142',
      evaluatorClass: 'RuleEvaluatorEOA01',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_AICTE_PORTAL',
      inputsRequired: ['Candidate Affidavit OCR Text', 'Portal Trust Signatory Profile'],
      evaluationLogicSummary:
        'Verifies non-judicial stamp paper >= ₹100, notarization affirmation, and matches signatory against legal chairman/secretary identity in portal snapshot.',
    },
    {
      code: 'EOA-SD-02',
      name: 'Application Processing Fee / Statutory Exemption Verification',
      version: 1,
      statutoryClause: 'Chapter II Section 2.4: Processing Fee Scale',
      aphCitation: 'AICTE APH 2024–2027, p. 48',
      evaluatorClass: 'RuleEvaluatorEOA02',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_AICTE_PORTAL',
      inputsRequired: ['Challan / Transaction Reference', 'Exemption Gazette Order'],
      evaluationLogicSummary:
        'Differentiates application fee exemption from tuition fee waiver. If exemption is claimed, validates against authoritative portal exemption order.',
    },
    {
      code: 'EOA-SD-03',
      name: 'Land Title Ownership & Registration Contiguity',
      version: 1,
      statutoryClause: 'Annexure 2.1 Item (iii): Land Title & Contiguity',
      aphCitation: 'AICTE APH 2024–2027, p. 143',
      evaluatorClass: 'RuleEvaluatorEOA03',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_REVENUE_LAND',
      inputsRequired: ['Registered Sale Deed', 'State Revenue 7/12 Extract'],
      evaluationLogicSummary:
        'Cross-verifies declared parcel acreage against authoritative State Revenue database. Flags any shortfall or boundary contradiction as DEFICIENT.',
    },
    {
      code: 'EOA-SD-04',
      name: 'Building Plan Approval & 30-Year Structural Stability',
      version: 1,
      statutoryClause: 'Annexure 2.1 Item (iv): Building Sanction & Safety',
      aphCitation: 'AICTE APH 2024–2027, p. 144',
      evaluatorClass: 'RuleEvaluatorEOA04',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_MUNICIPAL_BLDG',
      inputsRequired: ['Municipal Sanction Plan', 'Structural Stability Certificate (if >30 yrs)'],
      evaluationLogicSummary:
        'Calculates structure age from completion date (1990 = 36 yrs). If age >= 30, strictly mandates valid Structural Stability Certificate under NBC 2016.',
    },
    {
      code: 'EOA-SD-05',
      name: 'Fire Safety Certificate / NOC Competent Clearance',
      version: 1,
      statutoryClause: 'Annexure 2.1 Item (v): Life Safety & Fire Clearances',
      aphCitation: 'AICTE APH 2024–2027, p. 144',
      evaluatorClass: 'RuleEvaluatorEOA05',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_FIRE_SERVICES',
      inputsRequired: ['Applicant Fire NOC PDF', 'State Fire Directorate Database Record'],
      evaluationLogicSummary:
        'Queries State Fire Directorate registry by NOC number and survey plot. If no active clearance record is found, evaluates to DEFICIENT.',
    },
    {
      code: 'EOA-SD-06',
      name: 'Demarcated Satellite Map & Geocoordinates Overlay',
      version: 1,
      statutoryClause: 'Annexure 2.1 Item (vi): Satellite Site Demarcation',
      aphCitation: 'AICTE APH 2024–2027, p. 145',
      evaluatorClass: 'RuleEvaluatorEOA06',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_BHUVAN_GEOMAP',
      inputsRequired: ['Site Perimeter Coordinates', 'ISRO Bhuvan Satellite Imagery'],
      evaluationLogicSummary:
        'Validates polygon boundary geocoordinates. If satellite imagery is obscured by cloud cover, returns UNABLE_TO_DETERMINE for field inspection.',
    },
    {
      code: 'EOA-SD-07',
      name: 'Audited Financial Balance Sheet with ICAI UDIN',
      version: 1,
      statutoryClause: 'Annexure 2.1 Item (vii): Financial Accountability',
      aphCitation: 'AICTE APH 2024–2027, p. 145',
      evaluatorClass: 'RuleEvaluatorEOA07',
      status: 'ACTIVE',
      effectiveFrom: '2026-01-01',
      sourceConnector: 'SRC_ICAI_UDIN',
      inputsRequired: ['Audited Financial Statements', 'ICAI UDIN Registry API'],
      evaluationLogicSummary:
        'Extracts 18-character UDIN and verifies registration on ICAI portal. If unregistered or invalid, flags as DEFICIENT regulatory breach.',
    },
  ];

  const filteredRules = rules.filter((r) => {
    const q = searchQuery.toLowerCase();
    return (
      r.code.toLowerCase().includes(q) ||
      r.name.toLowerCase().includes(q) ||
      r.evaluatorClass.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Platform Administration</span>
            <span>/</span>
            <span>Regulatory Rules Catalog</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <FileCode className="w-6 h-6 text-primary" />
            AICTE Regulatory Rule Engine Catalog (Version 1)
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Deterministic rule evaluators implementing AICTE Approval Process Handbook (APH 2024–2027) Annexure 2.1
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary py-1 px-3 self-start sm:self-auto">
          7 Active Version 1 Rules Seeded
        </Badge>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
        <Input
          placeholder="Search rules by code, title, or evaluator class..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 text-sm"
        />
      </div>

      {/* Rules Table */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b bg-muted/40 font-semibold text-muted-foreground">
                <th className="py-3 px-4">Rule Code</th>
                <th className="py-3 px-4">Rule Title &amp; Statutory Citation</th>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Evaluator Class</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredRules.map((rule) => (
                <tr key={rule.code} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-foreground whitespace-nowrap">
                    {rule.code}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-foreground text-xs block">
                      {rule.name}
                    </span>
                    <span className="text-[11px] text-muted-foreground block">
                      {rule.aphCitation}
                    </span>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap font-mono">
                    v{rule.version}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px] text-primary font-semibold">
                    {rule.evaluatorClass}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Badge variant="outline" className="border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[10px]">
                      {rule.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-xs px-2"
                      onClick={() => setSelectedRule(rule)}
                    >
                      <Eye className="w-3.5 h-3.5 mr-1" />
                      Inspect Logic
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rule Inspection Modal */}
      <Dialog
        open={Boolean(selectedRule)}
        onOpenChange={(open) => !open && setSelectedRule(null)}
      >
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-primary" />
              {selectedRule?.code}: {selectedRule?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedRule?.statutoryClause} &bull; {selectedRule?.aphCitation}
            </DialogDescription>
          </DialogHeader>

          {selectedRule && (
            <div className="space-y-4 pt-2 text-xs">
              <div className="grid grid-cols-2 gap-3 p-3 rounded bg-muted/40 border font-mono">
                <div>
                  <span className="text-muted-foreground block text-[10px]">EVALUATOR CLASS</span>
                  <span className="font-bold text-foreground">{selectedRule.evaluatorClass}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px]">SOURCE CONNECTOR</span>
                  <span className="font-bold text-foreground">{selectedRule.sourceConnector}</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="font-semibold text-foreground text-[11px] uppercase tracking-wider block">
                  Evaluation Logic Summary:
                </span>
                <p className="text-muted-foreground leading-relaxed bg-muted/20 p-3 rounded border">
                  {selectedRule.evaluationLogicSummary}
                </p>
              </div>

              <div className="space-y-1.5">
                <span className="font-semibold text-foreground text-[11px] uppercase tracking-wider block">
                  Required Inputs &amp; Signals:
                </span>
                <ul className="list-disc pl-5 space-y-1 text-muted-foreground font-mono text-[11px]">
                  {selectedRule.inputsRequired.map((inp, idx) => (
                    <li key={idx}>{inp}</li>
                  ))}
                </ul>
              </div>

              <div className="flex justify-end pt-2 border-t">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedRule(null)}
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
export default AdminRulesPage;
