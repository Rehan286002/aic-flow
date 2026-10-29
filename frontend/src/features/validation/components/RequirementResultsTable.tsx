import React, { useState, useMemo } from 'react';
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  MinusCircle,
  ChevronDown,
  ChevronRight,
  Search,
  ExternalLink,
  ShieldAlert,
  FileText,
  Building2,
  Flame,
  MapPin,
  Scale,
  Receipt,
  FileCheck,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { ValidationResultRead, ValidationResultStatus, FindingRead } from '../types';

interface RequirementResultsTableProps {
  results: ValidationResultRead[];
  isReadOnly?: boolean;
  onSelectFinding?: (finding: FindingRead) => void;
  onInvestigateContradiction?: (itemCode: string) => void;
}

// Canonical Annexure 2.1 Regulatory Item Metadata
export const ANNEXURE_2_1_ITEMS: Record<
  string,
  {
    itemCode: string;
    ruleCode: string;
    title: string;
    clause: string;
    icon: React.ComponentType<{ className?: string }>;
    expectedAuthority: string;
  }
> = {
  'EOA-SD-01': {
    itemCode: 'EOA-SD-01',
    ruleCode: 'RULE_EOA_01_AFFIDAVIT',
    title: 'Affidavit 2 on ₹100 E-Stamp Paper',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item i',
    icon: Scale,
    expectedAuthority: 'Oath Commissioner / Notary Public',
  },
  'EOA-SD-02': {
    itemCode: 'EOA-SD-02',
    ruleCode: 'RULE_EOA_02_PAYMENT',
    title: 'AICTE Web-Portal Payment Receipt',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item ii & Chapter II',
    icon: Receipt,
    expectedAuthority: 'AICTE Payment Gateway / HDFC Bank Challan',
  },
  'EOA-SD-03': {
    itemCode: 'EOA-SD-03',
    ruleCode: 'RULE_EOA_03_BUILDING',
    title: 'Building Completion / Occupancy Certificate',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item iii & Clause 2.1.2',
    icon: Building2,
    expectedAuthority: 'Competent Municipal / Development Authority',
  },
  'EOA-SD-04': {
    itemCode: 'EOA-SD-04',
    ruleCode: 'RULE_EOA_04_STRUCTURAL',
    title: 'Structural Stability Certificate (>30 Years)',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item iv',
    icon: FileCheck,
    expectedAuthority: 'Registered Structural Engineer',
  },
  'EOA-SD-05': {
    itemCode: 'EOA-SD-05',
    ruleCode: 'RULE_EOA_05_FIRE_NOC',
    title: 'Fire Safety Certificate / NOC',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item v',
    icon: Flame,
    expectedAuthority: 'Competent State Fire Services Directorate',
  },
  'EOA-SD-06': {
    itemCode: 'EOA-SD-06',
    ruleCode: 'RULE_EOA_06_GEO_COORDS',
    title: 'Satellite Map & Main Entrance Geocoordinates',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item vi',
    icon: MapPin,
    expectedAuthority: 'ISRO Bhuvan / Certified Geospatial Map',
  },
  'EOA-SD-07': {
    itemCode: 'EOA-SD-07',
    ruleCode: 'RULE_EOA_07_AUDITED_STMT',
    title: 'Audited Statement of Accounts with UDIN',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item vii',
    icon: FileText,
    expectedAuthority: 'Practicing Chartered Accountant with UDIN',
  },
};

export const RequirementResultsTable: React.FC<RequirementResultsTableProps> = ({
  results,
  isReadOnly = false,
  onSelectFinding,
  onInvestigateContradiction,
}) => {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getStatusBadge = (status: ValidationResultStatus) => {
    switch (status) {
      case 'SATISFIED':
        return (
          <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 flex items-center gap-1 font-semibold">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            SATISFIED
          </Badge>
        );
      case 'DEFICIENT':
        return (
          <Badge className="bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30 flex items-center gap-1 font-semibold">
            <XCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
            DEFICIENT
          </Badge>
        );
      case 'UNABLE_TO_DETERMINE':
        return (
          <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 flex items-center gap-1 font-semibold">
            <HelpCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
            UNABLE TO DETERMINE
          </Badge>
        );
      case 'NOT_APPLICABLE':
        return (
          <Badge variant="outline" className="text-muted-foreground flex items-center gap-1 font-semibold">
            <MinusCircle className="h-3.5 w-3.5" />
            NOT APPLICABLE
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <Badge variant="destructive" className="text-[10px] uppercase font-bold">Critical</Badge>;
      case 'HIGH':
        return <Badge className="bg-orange-500 text-white text-[10px] uppercase font-bold">High</Badge>;
      case 'MEDIUM':
        return <Badge variant="secondary" className="bg-amber-500/15 text-amber-700 dark:text-amber-300 text-[10px] uppercase">Medium</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px] uppercase">{severity}</Badge>;
    }
  };

  // Helper to resolve metadata for a result
  const resolveItemMeta = (result: ValidationResultRead, index: number) => {
    // Attempt match via finding title or fallback to index order (EOA-SD-01 through 07)
    const findingTitle = result.findings?.[0]?.title || '';
    const codeMatch = findingTitle.match(/EOA-SD-0[1-7]/);
    const itemCode = codeMatch ? codeMatch[0] : Object.keys(ANNEXURE_2_1_ITEMS)[index] || `EOA-SD-0${index + 1}`;
    return ANNEXURE_2_1_ITEMS[itemCode] || {
      itemCode,
      ruleCode: `RULE_${itemCode}`,
      title: `Annexure 2.1 Checklist Item ${index + 1}`,
      clause: 'AICTE APH 2024–2027 Annexure 2.1',
      icon: FileText,
      expectedAuthority: 'Competent Statutory Authority',
    };
  };

  const filteredResults = useMemo(() => {
    return results.filter((r, idx) => {
      const meta = resolveItemMeta(r, idx);
      const matchesStatus = statusFilter === 'ALL' || r.result_status === statusFilter;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        meta.title.toLowerCase().includes(q) ||
        meta.itemCode.toLowerCase().includes(q) ||
        r.explanation.toLowerCase().includes(q) ||
        r.findings.some((f) => f.title.toLowerCase().includes(q) || (f.internal_reason || '').toLowerCase().includes(q));
      return matchesStatus && matchesSearch;
    });
  }, [results, statusFilter, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Controls Bar: Search & Status Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search requirement title, clause or explanation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-muted-foreground mr-1">Filter Status:</span>
          {['ALL', 'DEFICIENT', 'UNABLE_TO_DETERMINE', 'SATISFIED', 'NOT_APPLICABLE'].map((st) => (
            <Button
              key={st}
              size="xs"
              variant={statusFilter === st ? 'default' : 'outline'}
              onClick={() => setStatusFilter(st)}
              className="text-xs h-7 px-2.5"
            >
              {st === 'ALL' ? 'All (7)' : st.replace(/_/g, ' ')}
            </Button>
          ))}
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-3">
        {filteredResults.length === 0 ? (
          <div className="p-8 text-center border border-dashed rounded-lg bg-muted/20 text-muted-foreground text-sm">
            No regulatory validation results match the selected filter criteria.
          </div>
        ) : (
          filteredResults.map((result, idx) => {
            const meta = resolveItemMeta(result, idx);
            const isExpanded = !!expandedIds[result.validation_result_id];
            const Icon = meta.icon;

            return (
              <div
                key={result.validation_result_id}
                className="bg-card text-card-foreground rounded-lg border border-border transition-all overflow-hidden shadow-2xs hover:border-border/80"
              >
                {/* Header Row */}
                <div
                  onClick={() => toggleExpand(result.validation_result_id)}
                  className="p-4 flex items-center justify-between gap-3 cursor-pointer select-none hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <button
                      type="button"
                      className="p-1 rounded text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </button>

                    <div className="p-2 rounded-md bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground">
                          {meta.itemCode}
                        </span>
                        <h4 className="text-sm font-semibold truncate">{meta.title}</h4>
                      </div>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {meta.clause} &bull; Expected Authority: {meta.expectedAuthority}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {getStatusBadge(result.result_status)}
                  </div>
                </div>

                {/* Expanded Details Pane */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-1 border-t border-border/60 bg-muted/10 space-y-4">
                    {/* Explanation Banner */}
                    <div className="p-3.5 rounded-md bg-muted/40 border border-border/60 text-xs space-y-1">
                      <span className="font-semibold text-foreground uppercase tracking-wider text-[10px] text-muted-foreground">
                        Deterministic Evaluator Explanation
                      </span>
                      <p className="text-sm text-foreground leading-relaxed">{result.explanation}</p>
                    </div>

                    {/* Expected vs Observed Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-md bg-card border border-border/60 space-y-1.5">
                        <span className="font-semibold text-muted-foreground text-[11px] uppercase tracking-wider">
                          Statutory Expected Value
                        </span>
                        <pre className="font-mono text-[11px] p-2 rounded bg-muted/50 overflow-x-auto text-foreground whitespace-pre-wrap">
                          {JSON.stringify(result.expected_value, null, 2)}
                        </pre>
                      </div>

                      <div className="p-3 rounded-md bg-card border border-border/60 space-y-1.5">
                        <span className="font-semibold text-muted-foreground text-[11px] uppercase tracking-wider">
                          Observed Evidence Value
                        </span>
                        <pre className="font-mono text-[11px] p-2 rounded bg-muted/50 overflow-x-auto text-foreground whitespace-pre-wrap">
                          {JSON.stringify(result.observed_value, null, 2)}
                        </pre>
                      </div>
                    </div>

                    {/* Attached Regulatory Findings */}
                    {result.findings && result.findings.length > 0 && (
                      <div className="space-y-2 pt-2 border-t border-border/40">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                            <ShieldAlert className="h-3.5 w-3.5 text-primary" />
                            Attached Regulatory Findings ({result.findings.length})
                          </span>

                          {onInvestigateContradiction && (
                            <Button
                              size="xs"
                              variant="outline"
                              onClick={(e) => {
                                e.stopPropagation();
                                onInvestigateContradiction(meta.itemCode);
                              }}
                              className="text-xs h-7 gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Investigate Contradiction
                            </Button>
                          )}
                        </div>

                        <div className="space-y-2">
                          {result.findings.map((f) => (
                            <div
                              key={f.finding_id}
                              className="p-3 rounded-md bg-card border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
                            >
                              <div className="space-y-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  {getSeverityBadge(f.severity)}
                                  <Badge variant="outline" className="font-mono text-[10px]">
                                    {f.category}
                                  </Badge>
                                  <Badge variant="secondary" className="text-[10px] font-semibold">
                                    Status: {f.status}
                                  </Badge>
                                  <span className="font-medium text-foreground">{f.title}</span>
                                </div>
                                {f.internal_reason && (
                                  <p className="text-muted-foreground text-[11px] line-clamp-2">
                                    <span className="font-medium text-foreground/80">Auditor Reason:</span>{' '}
                                    {f.internal_reason}
                                  </p>
                                )}
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                {onSelectFinding && (
                                  <Button
                                    size="xs"
                                    variant={isReadOnly ? 'outline' : 'default'}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      onSelectFinding(f);
                                    }}
                                    className="h-7 text-xs"
                                  >
                                    {isReadOnly ? 'Inspect Audit Evidence' : 'Triage Finding'}
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

