import React, { useState, useMemo } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Info,
  Database,
  Search,
  Filter,
  FileText,
  UserCheck,
  Eye,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { ContradictionRow, ContradictionStatus } from '../types';

interface EvidenceContradictionMatrixProps {
  rows?: ContradictionRow[];
  selectedItemCode?: string;
  onSelectItemCode?: (code: string) => void;
  isReadOnly?: boolean;
}

// Canonical Demonstration Baseline for Apex Institute of Technology (APP-2026-EOA-0023)
export const DEFAULT_CONTRADICTION_ROWS: ContradictionRow[] = [
  {
    item_code: 'EOA-SD-01',
    requirement_title: 'Affidavit 2 on ₹100 E-Stamp Paper',
    field_name: 'e_stamp_duty_amount',
    declared_value: '₹100 (Declared on Affidavit 2)',
    ocr_extracted_value: 'Text inconclusive / Seal unparsed',
    ocr_confidence: 0.42,
    ocr_bounding_box: { page: 1, x: 120, y: 80, width: 240, height: 45 },
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'e-Stamp Paper IN-DL98234 recorded; duty value ₹100 confirmed',
    source_registry_code: 'SRC_REVENUE_LAND',
    source_provenance: 'SIMULATED',
    source_payload_hash: 'a1b2c3d4e5f6...7890',
    contradiction_status: 'UNVERIFIED',
    evaluation_outcome: 'UNABLE_TO_DETERMINE',
  },
  {
    item_code: 'EOA-SD-02',
    requirement_title: 'AICTE Web-Portal Payment Receipt',
    field_name: 'application_processing_fee',
    declared_value: 'Exemption Declared under Chapter II',
    ocr_extracted_value: 'No receipt document uploaded in bundle',
    ocr_confidence: null,
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'No explicit processing fee exemption or payment record in portal snapshot',
    source_registry_code: 'SRC_AICTE_PORTAL',
    source_provenance: 'SIMULATED',
    source_payload_hash: '9f8e7d6c5b4a...1234',
    contradiction_status: 'CONTRADICTION',
    evaluation_outcome: 'UNABLE_TO_DETERMINE',
  },
  {
    item_code: 'EOA-SD-03',
    requirement_title: 'Building Completion / Occupancy Certificate',
    field_name: 'completion_certificate_issue_date',
    declared_value: '1990-05-15 (Completion Date)',
    ocr_extracted_value: 'Document missing from bundle upload',
    ocr_confidence: null,
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'Sanction order dated 15-May-1990 recorded in municipal records',
    source_registry_code: 'SRC_MUNICIPAL_BLDG',
    source_provenance: 'SIMULATED',
    source_payload_hash: '3c4d5e6f7a8b...5678',
    contradiction_status: 'CONTRADICTION',
    evaluation_outcome: 'DEFICIENT',
  },
  {
    item_code: 'EOA-SD-04',
    requirement_title: 'Structural Stability Certificate (>30 Years)',
    field_name: 'structural_stability_certificate',
    declared_value: 'Building age 36 years (Completion: 1990-05-15)',
    ocr_extracted_value: 'No structural certificate found in application files',
    ocr_confidence: null,
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'Building exceeds 30-year threshold; requires Registered Engineer stability audit',
    source_registry_code: 'SRC_MUNICIPAL_BLDG',
    source_provenance: 'SIMULATED',
    source_payload_hash: '3c4d5e6f7a8b...5678',
    contradiction_status: 'CONTRADICTION',
    evaluation_outcome: 'DEFICIENT',
  },
  {
    item_code: 'EOA-SD-05',
    requirement_title: 'Fire Safety Certificate / NOC',
    field_name: 'fire_safety_noc_status',
    declared_value: 'Valid NOC Claimed on Self-Disclosure',
    ocr_extracted_value: 'Document missing from application upload',
    ocr_confidence: null,
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'No active NOC record found for campus address in Fire Directorate registry',
    source_registry_code: 'SRC_FIRE_SERVICES',
    source_provenance: 'SIMULATED',
    source_payload_hash: '8a9b0c1d2e3f...9012',
    contradiction_status: 'ABSENT_IN_SOURCE',
    evaluation_outcome: 'DEFICIENT',
  },
  {
    item_code: 'EOA-SD-06',
    requirement_title: 'Satellite Map & Entrance Geocoordinates',
    field_name: 'main_entrance_coordinates',
    declared_value: 'Lat 28.6139° N, Lon 77.2090° E',
    ocr_extracted_value: 'Map image uploaded; OCR coordinate digits unparsed',
    ocr_confidence: 0.35,
    ocr_bounding_box: { page: 1, x: 80, y: 350, width: 300, height: 60 },
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'Cadastral GIS parcel boundary verified at 28.6142° N, 77.2088° E',
    source_registry_code: 'SRC_BHUVAN_GEOMAP',
    source_provenance: 'SIMULATED',
    source_payload_hash: '4e5f6a7b8c9d...3456',
    contradiction_status: 'UNVERIFIED',
    evaluation_outcome: 'UNABLE_TO_DETERMINE',
  },
  {
    item_code: 'EOA-SD-07',
    requirement_title: 'Audited Statement of Accounts with UDIN',
    field_name: 'ca_udin_reference',
    declared_value: 'FY 2024-25 Accounts Audited',
    ocr_extracted_value: 'Financial statement missing from application upload',
    ocr_confidence: null,
    auditor_reviewed_value: null,
    auditor_review_status: 'UNREVIEWED',
    source_registry_value: 'No UDIN record matching FY 2024-25 filed for institution trust',
    source_registry_code: 'SRC_ICAI_UDIN',
    source_provenance: 'SIMULATED',
    source_payload_hash: '7b8c9d0e1f2a...7890',
    contradiction_status: 'CONTRADICTION',
    evaluation_outcome: 'DEFICIENT',
  },
];

export const EvidenceContradictionMatrix: React.FC<EvidenceContradictionMatrixProps> = ({
  rows = DEFAULT_CONTRADICTION_ROWS,
  selectedItemCode,
  onSelectItemCode,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const getStatusChip = (status: ContradictionStatus) => {
    switch (status) {
      case 'MATCH':
        return (
          <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 gap-1 text-[11px] font-semibold">
            <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            MATCH
          </Badge>
        );
      case 'CONTRADICTION':
        return (
          <Badge className="bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30 gap-1 text-[11px] font-semibold">
            <AlertCircle className="h-3 w-3 text-red-600 dark:text-red-400" />
            CONTRADICTION
          </Badge>
        );
      case 'ABSENT_IN_SOURCE':
        return (
          <Badge variant="outline" className="text-muted-foreground gap-1 text-[11px]">
            <Info className="h-3 w-3" />
            ABSENT IN SOURCE
          </Badge>
        );
      case 'UNVERIFIED':
        return (
          <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 gap-1 text-[11px] font-semibold">
            <HelpCircle className="h-3 w-3 text-amber-600 dark:text-amber-400" />
            UNVERIFIED
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredRows = useMemo(() => {
    return rows.filter((r) => {
      const matchesItem = !selectedItemCode || r.item_code === selectedItemCode;
      const matchesStatus = statusFilter === 'ALL' || r.contradiction_status === statusFilter;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        r.requirement_title.toLowerCase().includes(q) ||
        r.item_code.toLowerCase().includes(q) ||
        r.declared_value.toLowerCase().includes(q) ||
        r.ocr_extracted_value.toLowerCase().includes(q) ||
        (r.source_registry_value || '').toLowerCase().includes(q);
      return matchesItem && matchesStatus && matchesSearch;
    });
  }, [rows, selectedItemCode, statusFilter, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Matrix Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search contradiction rows by field or value..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Status:</span>
          {['ALL', 'CONTRADICTION', 'UNVERIFIED', 'MATCH', 'ABSENT_IN_SOURCE'].map((st) => (
            <Button
              key={st}
              size="xs"
              variant={statusFilter === st ? 'default' : 'outline'}
              onClick={() => setStatusFilter(st)}
              className="text-xs h-7 px-2"
            >
              {st === 'ALL' ? 'All' : st.replace(/_/g, ' ')}
            </Button>
          ))}
        </div>
      </div>

      {/* 4-Column Matrix Table */}
      <div className="bg-card text-card-foreground rounded-lg border border-border shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/60 text-muted-foreground font-semibold uppercase tracking-wider text-[11px]">
                <th className="p-3 w-44">Requirement & Field</th>
                <th className="p-3 w-60">1. Applicant Declaration</th>
                <th className="p-3 w-60">2. Candidate OCR</th>
                <th className="p-3 w-48">3. Human Review</th>
                <th className="p-3 min-w-64">4. External Registry Source [SIMULATED]</th>
                <th className="p-3 w-32 text-right">Alignment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-muted-foreground">
                    No contradiction rows match the active filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr
                    key={row.item_code}
                    className={`hover:bg-muted/30 transition-colors ${
                      row.contradiction_status === 'CONTRADICTION' ? 'bg-red-500/5 dark:bg-red-950/10' : ''
                    }`}
                  >
                    {/* Column 0: Requirement & Field */}
                    <td className="p-3 align-top space-y-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-semibold px-1.5 py-0.5 rounded bg-muted text-[10px]">
                          {row.item_code}
                        </span>
                        {onSelectItemCode && (
                          <button
                            type="button"
                            onClick={() => onSelectItemCode(row.item_code)}
                            className="text-primary hover:underline text-[11px] font-medium"
                          >
                            Drill Down
                          </button>
                        )}
                      </div>
                      <p className="font-semibold text-foreground leading-tight text-xs">{row.requirement_title}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">{row.field_name}</p>
                    </td>

                    {/* Column 1: Self-Disclosure Declaration */}
                    <td className="p-3 align-top space-y-1">
                      <div className="p-2 rounded bg-muted/40 border border-border/50 text-foreground font-medium">
                        {row.declared_value}
                      </div>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <FileText className="h-3 w-3" /> Form Revision #1
                      </span>
                    </td>

                    {/* Column 2: Document Intelligence (OCR) */}
                    <td className="p-3 align-top space-y-1">
                      <div className="p-2 rounded bg-muted/40 border border-border/50 text-foreground">
                        {row.ocr_extracted_value}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                        {row.ocr_confidence !== null ? (
                          <span className="font-mono text-primary font-medium">
                            Conf: {(row.ocr_confidence * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground">No candidate text</span>
                        )}
                        {row.ocr_bounding_box ? (
                          <span className="flex items-center gap-0.5 text-muted-foreground font-mono">
                            <Eye className="h-3 w-3" /> Page 1 bbox
                          </span>
                        ) : null}
                      </div>
                    </td>

                    {/* Column 3: Auditor Field Review */}
                    <td className="p-3 align-top space-y-1">
                      <div className="p-2 rounded bg-muted/40 border border-border/50 text-muted-foreground">
                        {row.auditor_reviewed_value || 'No auditor override'}
                      </div>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          row.auditor_review_status === 'ACCEPTED'
                            ? 'text-emerald-600 border-emerald-500/40'
                            : row.auditor_review_status === 'CORRECTED'
                            ? 'text-primary border-primary/40'
                            : 'text-muted-foreground'
                        }`}
                      >
                        <UserCheck className="h-2.5 w-2.5 mr-1" />
                        {row.auditor_review_status}
                      </Badge>
                    </td>

                    {/* Column 4: External Source Registry Snapshot */}
                    <td className="p-3 align-top space-y-1.5">
                      <div className="p-2 rounded bg-muted/40 border border-border/50 text-foreground text-xs leading-relaxed">
                        {row.source_registry_value}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap text-[10px]">
                        <Badge variant="outline" className="font-mono text-[10px] bg-primary/5 text-primary border-primary/20">
                          <Database className="h-3 w-3 mr-1" />
                          {row.source_registry_code}
                        </Badge>
                        <span className="text-muted-foreground font-mono truncate max-w-40" title={row.source_payload_hash || ''}>
                          SHA: {row.source_payload_hash}
                        </span>
                      </div>
                    </td>

                    {/* Alignment Chip */}
                    <td className="p-3 align-top text-right">
                      {getStatusChip(row.contradiction_status)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
