import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  FileText,
  Calendar,
  Users,
  Compass,
  Printer,
  RefreshCw,
  AlertCircle,
  Database,
  ArrowRight,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ValidationRunBanner } from '@/features/validation/components/ValidationRunBanner';
import { RequirementResultsTable } from '@/features/validation/components/RequirementResultsTable';
import { EvidenceContradictionMatrix } from '@/features/validation/components/EvidenceContradictionMatrix';
import { FindingActionModal } from '@/features/validation/components/FindingActionModal';
import { validationApi } from '@/features/validation/api';
import { useDemoScenario } from '@/features/demo/demoContext';
import type { ValidationRunRead, FindingRead, FindingStatus } from '@/features/validation/types';

// Canonical Apex Institute identifiers
const APEX_INSTITUTION_ID = '605839a3-9c20-4ec6-b9f9-765a4b732ad0';
const APEX_APPLICATION_ID = '082c25e6-a94c-454f-897b-7d307819abcd';
const APEX_REFERENCE_RUN_ID = '5822d8f2-dcd4-4fd3-8794-cb84ef23e54f';

export const AuditorCaseWorkspacePage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, updateFindingStatus, resetDemo } = useDemoScenario();
  const [activeMode, setActiveMode] = useState<'REFERENCE_RUN' | 'INTERACTIVE_DEMO'>('REFERENCE_RUN');
  const [runData, setRunData] = useState<ValidationRunRead | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Finding action modal state
  const [selectedFinding, setSelectedFinding] = useState<FindingRead | null>(null);
  const [selectedContradictionCode, setSelectedContradictionCode] = useState<string | undefined>();
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  // Load the live persistent validation run from the real backend API
  const loadValidationRun = useCallback(async () => {
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
      const msg = err instanceof Error ? err.message : 'Failed to retrieve validation run from backend.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadValidationRun();
  }, [loadValidationRun]);

  const handleSelectFinding = (finding: FindingRead) => {
    setSelectedFinding(finding);
    setIsModalOpen(true);
  };

  const handleInvestigateContradiction = (itemCode: string) => {
    setSelectedContradictionCode(itemCode);
    const element = document.getElementById('contradiction-matrix-section');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    } else {
      navigate(`/auditor/evidence-explorer?item=${encodeURIComponent(itemCode)}`);
    }
  };

  const handleFindingStatusUpdate = async (
    findingId: string,
    targetStatus: FindingStatus,
    rationale: string
  ) => {
    // Reference run is strictly read-only per Section 1.1 safeguard
    if (activeMode === 'REFERENCE_RUN') {
      alert('The Apex reference run is an immutable baseline. Switch to Interactive Demo Scenario to record review actions.');
      return;
    }

    // In demo mode, persist to demoStore
    updateFindingStatus(findingId, targetStatus, rationale, 'Auditor (Review Team Alpha)');
  };

  const activeRunToRender = activeMode === 'INTERACTIVE_DEMO' ? demoState.validationRun : runData;
  const isActualLoading = activeMode === 'REFERENCE_RUN' && isLoading;

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <span>Auditor Console</span>
            <span>&bull;</span>
            <span>Assigned Cases</span>
            <span>&bull;</span>
            <span className="font-mono text-foreground font-semibold">APP-2026-EOA-0023</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Building2 className="h-6 w-6 text-primary" />
            Apex Institute of Technology: Case Workspace
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {activeMode === 'INTERACTIVE_DEMO' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={resetDemo}
              className="text-xs h-8 gap-1 text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Demo
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={() => void loadValidationRun()}
            disabled={isActualLoading}
            className="text-xs h-8 gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isActualLoading ? 'animate-spin' : ''}`} />
            Refresh Data
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => window.print()}
            className="text-xs h-8 gap-1.5"
          >
            <Printer className="h-3.5 w-3.5" />
            Print Dossier
          </Button>

          <Button
            size="sm"
            onClick={() => navigate('/auditor/evidence-explorer')}
            className="text-xs h-8 gap-1.5"
          >
            <Compass className="h-3.5 w-3.5" />
            Contradiction Explorer
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Case Overview Metadata Card */}
      <div className="bg-card text-card-foreground rounded-lg border border-border shadow-2xs p-5 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div className="space-y-1">
          <span className="text-muted-foreground uppercase tracking-wider font-semibold text-[10px]">
            Permanent AICTE ID
          </span>
          <div className="font-semibold text-sm font-mono text-foreground">
            1-10948201
          </div>
          <p className="text-[11px] text-muted-foreground">Apex Institute of Technology</p>
        </div>

        <div className="space-y-1">
          <span className="text-muted-foreground uppercase tracking-wider font-semibold text-[10px]">
            Application Revision
          </span>
          <div className="font-semibold text-sm flex items-center gap-1.5 font-mono">
            <FileText className="h-4 w-4 text-muted-foreground" />
            {activeMode === 'INTERACTIVE_DEMO' ? `Revision #${demoState.activeRevisionNumber}` : 'Revision #1'}
          </div>
          <p className="text-[11px] text-muted-foreground">
            {activeMode === 'INTERACTIVE_DEMO' && demoState.activeRevisionNumber >= 2
              ? 'Revision #2 Submitted & Re-evaluated'
              : 'Initial Self-Disclosure Bundle'}
          </p>
        </div>

        <div className="space-y-1">
          <span className="text-muted-foreground uppercase tracking-wider font-semibold text-[10px]">
            Academic Year
          </span>
          <div className="font-semibold text-sm flex items-center gap-1.5">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            AY 2026-27
          </div>
          <p className="text-[11px] text-muted-foreground">Statutory Filing Active</p>
        </div>

        <div className="space-y-1">
          <span className="text-muted-foreground uppercase tracking-wider font-semibold text-[10px]">
            Review Assignment
          </span>
          <div className="font-semibold text-sm flex items-center gap-1.5">
            <Users className="h-4 w-4 text-muted-foreground" />
            Review Team Alpha
          </div>
          <Badge variant="secondary" className="text-[10px] bg-primary/10 text-primary border-primary/20">
            {activeMode === 'INTERACTIVE_DEMO' && demoState.activeRevisionNumber >= 2
              ? 'Revision 2 Ready for Concurrence'
              : 'Case Status: Under Auditor Review'}
          </Badge>
        </div>
      </div>

      {/* Data Source Selector Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg bg-muted/40 border border-border text-xs">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-primary" />
          <span className="font-medium">Active Evaluation Dataset:</span>
          <Badge
            variant={activeMode === 'REFERENCE_RUN' ? 'default' : 'outline'}
            onClick={() => setActiveMode('REFERENCE_RUN')}
            className="cursor-pointer text-xs"
          >
            Live Backend Run (Database Baseline)
          </Badge>
          <Badge
            variant={activeMode === 'INTERACTIVE_DEMO' ? 'default' : 'outline'}
            onClick={() => setActiveMode('INTERACTIVE_DEMO')}
            className="cursor-pointer text-xs"
          >
            Interactive Evaluation Scenario
          </Badge>
        </div>

        <span className="text-muted-foreground text-[11px]">
          {activeMode === 'REFERENCE_RUN'
            ? 'Connected live to PostgreSQL ValidationRun 5822d8f2... (Read-Only Baseline)'
            : 'Interactive demonstration state active; status modifications enabled in demo store'}
        </span>
      </div>

      {/* Error Alert */}
      {errorMsg && activeMode === 'REFERENCE_RUN' && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-3">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Unable to load validation run from backend</p>
            <p className="text-xs mt-0.5">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Skeleton Loading State */}
      {isActualLoading && (
        <div className="space-y-4">
          <div className="h-48 rounded-lg bg-muted/50 animate-pulse" />
          <div className="h-96 rounded-lg bg-muted/50 animate-pulse" />
        </div>
      )}

      {/* Main Validation Workspace Content */}
      {!isActualLoading && activeRunToRender && (
        <div className="space-y-6">
          {/* Validation Run Overview Banner */}
          <ValidationRunBanner
            run={activeRunToRender}
            isReferenceRun={activeMode === 'REFERENCE_RUN'}
          />

          {/* Detailed 7 Requirements Results & Findings */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold tracking-tight text-foreground">
                  Annexure 2.1 Regulatory Rule Results
                </h2>
                <p className="text-xs text-muted-foreground">
                  Evaluated across the 7 mandatory self-disclosure compliance areas against AICTE Approval Process Handbook (APH 2024–2027).
                </p>
              </div>
            </div>

            <RequirementResultsTable
              results={activeRunToRender.results}
              onSelectFinding={handleSelectFinding}
              onInvestigateContradiction={handleInvestigateContradiction}
            />
          </div>

          {/* Independent Multi-Source Evidence Contradiction Matrix */}
          <div id="contradiction-matrix-section" className="space-y-3 pt-6 border-t border-border">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
                <Database className="w-5 h-5 text-primary" />
                Multi-Source Evidence Contradiction Matrix
              </h2>
              <p className="text-xs text-muted-foreground">
                Cross-triangulation comparing applicant self-disclosure declarations against OCR extractions and authoritative external registry signals.
              </p>
            </div>

            <EvidenceContradictionMatrix
              selectedItemCode={selectedContradictionCode}
              onSelectItemCode={setSelectedContradictionCode}
              isReadOnly={activeMode === 'REFERENCE_RUN'}
            />
          </div>
        </div>
      )}

      {/* Finding Action / Triage Modal */}
      <FindingActionModal
        finding={selectedFinding}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedFinding(null);
        }}
        onSubmitStatusUpdate={handleFindingStatusUpdate}
        isReadOnly={activeMode === 'REFERENCE_RUN'}
      />
    </div>
  );
};
export default AuditorCaseWorkspacePage;
