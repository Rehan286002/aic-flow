import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Building2,
  Printer,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  AlertTriangle,
  Scale,
  Building,
  Flame,
  MapPin,
  Receipt,
  FileCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { validationApi } from '@/features/validation/api';
import type { ValidationRunRead, ValidationResultStatus } from '@/features/validation/types';
import { InstitutionWorkflowProgress } from '@/components/institution/InstitutionWorkflowProgress';

const APEX_INSTITUTION_ID = '605839a3-9c20-4ec6-b9f9-765a4b732ad0';
const APEX_APPLICATION_ID = '082c25e6-a94c-454f-897b-7d307819abcd';
const APEX_REFERENCE_RUN_ID = '5822d8f2-dcd4-4fd3-8794-cb84ef23e54f';

// Applicant-facing guidance mapping (strictly sanitized, no internal auditor notes)
const APPLICANT_GUIDANCE: Record<
  string,
  {
    title: string;
    clause: string;
    guidance: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  'EOA-SD-01': {
    title: 'Affidavit 2 on ₹100 E-Stamp Paper',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item i',
    guidance:
      'Ensure the uploaded Affidavit 2 is on non-judicial e-stamp paper of value ₹100 and clearly sworn before an Oath Commissioner or Notary Public with legible text and seal.',
    icon: Scale,
  },
  'EOA-SD-02': {
    title: 'AICTE Web-Portal Payment Receipt',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item ii & Chapter II',
    guidance:
      'If claiming fee exemption under Chapter II, submit an authoritative statutory exemption order, or upload the official payment gateway transaction challan.',
    icon: Receipt,
  },
  'EOA-SD-03': {
    title: 'Building Completion / Occupancy Certificate',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item iii & Clause 2.1.2',
    guidance:
      'Upload the sanctioned building completion or occupancy certificate issued by the competent municipal corporation or urban development authority.',
    icon: Building,
  },
  'EOA-SD-04': {
    title: 'Structural Stability Certificate (>30 Years)',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item iv',
    guidance:
      'Because the declared building completion date (15-May-1990) exceeds 30 years, submit a valid Structural Stability Certificate issued by a registered structural engineer.',
    icon: FileCheck,
  },
  'EOA-SD-05': {
    title: 'Fire Safety Certificate / NOC',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item v',
    guidance:
      'Submit a valid Fire Safety Certificate or No Objection Certificate (NOC) issued by the competent state fire services authority having jurisdiction.',
    icon: Flame,
  },
  'EOA-SD-06': {
    title: 'Satellite Map & Entrance Geocoordinates',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item vi',
    guidance:
      'Provide a clear satellite map showing the geographical location and exact latitude and longitude coordinates of the main institutional campus entrance.',
    icon: MapPin,
  },
  'EOA-SD-07': {
    title: 'Audited Statement of Accounts with UDIN',
    clause: 'AICTE APH 2024–2027 Annexure 2.1 Item vii',
    guidance:
      'Submit the complete audited statement of accounts for the previous financial year, signed by a practicing Chartered Accountant with a valid unique document identification number (UDIN).',
    icon: FileText,
  },
};

export const InstitutionReportsPage: React.FC = () => {
  const navigate = useNavigate();
  const [runData, setRunData] = useState<ValidationRunRead | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const data = await validationApi.getValidationRun(
        APEX_INSTITUTION_ID,
        APEX_APPLICATION_ID,
        APEX_REFERENCE_RUN_ID
      );
      setRunData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve compliance statement.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  const getStatusBadge = (status: ValidationResultStatus) => {
    switch (status) {
      case 'SATISFIED':
        return (
          <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 gap-1 font-semibold">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            SATISFIED
          </Badge>
        );
      case 'DEFICIENT':
        return (
          <Badge className="bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30 gap-1 font-semibold">
            <XCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
            ACTION REQUIRED
          </Badge>
        );
      case 'UNABLE_TO_DETERMINE':
        return (
          <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 gap-1 font-semibold">
            <HelpCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
            CLARIFICATION NEEDED
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const satisfiedCount = runData?.results.filter((r) => r.result_status === 'SATISFIED').length || 0;
  const deficientCount = runData?.results.filter((r) => r.result_status === 'DEFICIENT').length || 0;
  const unableCount = runData?.results.filter((r) => r.result_status === 'UNABLE_TO_DETERMINE').length || 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <span>Institution Portal</span>
            <span>&bull;</span>
            <span>Self-Disclosure Applications</span>
            <span>&bull;</span>
            <span className="font-semibold text-foreground">Compliance Summary Report</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <FileText className="h-6 w-6 text-primary" />
            Regulatory Compliance & Deficiency Notice
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => void loadReport()}
            disabled={isLoading}
            className="text-xs h-8 gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => window.print()}
            className="text-xs h-8 gap-1.5"
          >
            <Printer className="h-3.5 w-3.5" />
            Print Report
          </Button>

          <Button
            size="sm"
            onClick={() => navigate('/institution/rectification')}
            className="text-xs h-8 gap-1.5 bg-primary text-primary-foreground font-semibold"
          >
            Rectification Center
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Lifecycle Progress Stepper */}
      <InstitutionWorkflowProgress />

      {/* Institution Context Card */}
      <div className="p-5 rounded-lg bg-card border border-border shadow-2xs grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
        <div>
          <span className="text-muted-foreground font-medium text-[10px] uppercase">Institution</span>
          <p className="font-bold text-sm text-foreground flex items-center gap-1.5 mt-0.5">
            <Building2 className="h-4 w-4 text-primary" /> Apex Institute of Technology
          </p>
          <p className="text-muted-foreground font-mono text-xs">Permanent ID: 1-10948201</p>
        </div>

        <div>
          <span className="text-muted-foreground font-medium text-[10px] uppercase">Application Reference</span>
          <p className="font-semibold text-sm text-foreground mt-0.5">APP-2026-EOA-0023 (Rev #1)</p>
          <p className="text-muted-foreground text-xs">Academic Year 2026-27 &bull; Extension of Approval</p>
        </div>

        <div>
          <span className="text-muted-foreground font-medium text-[10px] uppercase">Overall Evaluation Status</span>
          <div className="mt-1">
            <Badge variant="destructive" className="font-bold text-xs uppercase px-2.5 py-1">
              Deficiencies Identified: Rectification Required
            </Badge>
          </div>
        </div>
      </div>

      {/* Metric Breakdown Cards */}
      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase">Compliant Requirements</p>
            <p className="text-xl font-bold mt-0.5">{satisfiedCount}</p>
          </div>
          <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
        </div>

        <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-300 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase">Action Required</p>
            <p className="text-xl font-bold mt-0.5">{deficientCount}</p>
          </div>
          <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
        </div>

        <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase">Clarification Needed</p>
            <p className="text-xl font-bold mt-0.5">{unableCount}</p>
          </div>
          <HelpCircle className="h-6 w-6 text-amber-600 dark:text-amber-400" />
        </div>
      </div>

      {/* Notice Banner */}
      <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
        <div>
          <p className="font-semibold text-sm">Regulatory Notice to Applicant Institution</p>
          <p className="text-xs text-amber-700 dark:text-amber-400 mt-1 leading-relaxed">
            Please review the requirement checklist below. Deficiencies marked with{' '}
            <strong className="font-bold">ACTION REQUIRED</strong> or{' '}
            <strong className="font-bold">CLARIFICATION NEEDED</strong> must be addressed by submitting revised
            declarations or replacement supporting documents through the Rectification Center prior to formal AICTE
            committee scrutiny.
          </p>
        </div>
      </div>

      {/* Sanitized Requirement Checklist */}
      <div className="space-y-3">
        <h3 className="font-semibold text-sm text-foreground">
          Annexure 2.1: Itemized Self-Disclosure Compliance Status
        </h3>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-lg bg-muted/40 animate-pulse border border-border/50" />
            ))}
          </div>
        ) : errorMsg ? (
          <div className="p-6 text-center text-red-600 border border-red-500/30 rounded-lg bg-red-500/10 text-xs">
            {errorMsg}
          </div>
        ) : (
          runData?.results.map((result, idx) => {
            const itemCode = `EOA-SD-0${idx + 1}`;
            const meta = APPLICANT_GUIDANCE[itemCode] || {
              title: `Annexure 2.1 Item ${idx + 1}`,
              clause: 'AICTE APH 2024–2027',
              guidance: result.explanation,
              icon: FileText,
            };
            const Icon = meta.icon;

            return (
              <div
                key={result.validation_result_id}
                className="p-4 rounded-lg bg-card border border-border shadow-2xs space-y-2 text-xs"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold px-1.5 py-0.5 rounded bg-muted">
                          {itemCode}
                        </span>
                        <h4 className="font-semibold text-foreground text-sm">{meta.title}</h4>
                      </div>
                      <p className="text-[11px] text-muted-foreground">{meta.clause}</p>
                    </div>
                  </div>

                  <div>{getStatusBadge(result.result_status)}</div>
                </div>

                {/* Sanitized Applicant Guidance */}
                <div className="p-3 rounded-md bg-muted/30 border border-border/50 text-foreground leading-relaxed text-xs">
                  <span className="font-semibold text-muted-foreground text-[10px] uppercase block mb-0.5">
                    Regulatory Finding & Action Required:
                  </span>
                  <p>{result.explanation}</p>
                  <p className="text-muted-foreground mt-1 text-[11px]">{meta.guidance}</p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

