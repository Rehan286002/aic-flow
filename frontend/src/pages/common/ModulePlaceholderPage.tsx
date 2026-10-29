import { useLocation, useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useWorkspaceRole } from '@/hooks/useWorkspaceRole';
import {
  Compass,
  ArrowLeft,
} from 'lucide-react';

interface ModuleConfig {
  title: string;
  specSection: string;
  description: string;
  plannedFeatures: string[];
}

const MODULE_SPECS: Record<string, ModuleConfig> = {
  // Auditor routes
  '/auditor/queue': {
    title: 'Assigned Auditor Queue',
    specSection: 'Section 6.2 — Auditor Workflows & Case Intake',
    description: 'Prioritized queue of active Extension of Approval applications assigned to the logged-in regulatory auditor.',
    plannedFeatures: [
      'Multi-parameter filtering by risk score and deficiency count',
      'One-click case claim and triage',
      'Annexure 2.1 rule checklist quick-look preview',
    ],
  },
  '/auditor/case-workspace': {
    title: 'Case Workspace',
    specSection: 'Section 6.3 — Auditor Investigation & Case File',
    description: 'Primary case adjudication interface with institutional profile, application revision history, and checklist adjudication.',
    plannedFeatures: [
      'Active application envelope & revision tracker',
      'Direct checklist evaluation for the 7 Annexure 2.1 rules',
      'Internal auditor observation log (restricted from applicant)',
    ],
  },
  '/auditor/evidence-explorer': {
    title: 'Evidence Contradiction Explorer',
    specSection: 'Section 6.4 — Evidence Viewer & Contradiction Graph',
    description: 'Signature 3-panel investigation workspace connecting PDF documents, PaddleOCR bounding boxes, simulated issuer records, and the @xyflow/react graph.',
    plannedFeatures: [
      'Left panel: Prioritized findings list with rule discrepancy filters',
      'Center panel: High-resolution PDF viewer with visual OCR bounding boxes',
      'Right panel: Submitted value vs extracted document value vs simulated issuer record',
      'Interactive @xyflow/react relationship graph tracing document to rule version',
    ],
  },
  '/auditor/source-verification': {
    title: 'Source Verification Gateway',
    specSection: 'Section 6.5 — Simulated External Connectors',
    description: 'Direct interface for inspecting simulated external issuer reconciliations (DigiLocker, State Land Registry, Bank Challans, and State GIS).',
    plannedFeatures: [
      'Issuer connector latency, fresh timestamps, and sync state',
      'Direct payload viewer for simulated responses',
      'Manual connector query trigger for edge-case reconciliation',
    ],
  },
  '/auditor/finding-review': {
    title: 'Finding Review & Adjudication',
    specSection: 'Section 6.6 — Regulatory Finding Lifecycle',
    description: 'Comprehensive review list of all automated rule contradiction flags across assigned applications.',
    plannedFeatures: [
      'Formal actions: Accept Flag, Dismiss Flag, Request Rectification, Escalate to Lead',
      'Mandatory auditor rationale entry before flag modification',
      'Audit trail registration into local SQLite/Postgres ledger',
    ],
  },
  '/auditor/activity': {
    title: 'Case Activity & Audit Trail',
    specSection: 'Section 6.7 — Audit Event Logging & Traceability',
    description: 'Chronological immutable log of all verification events, rule triggers, and human decisions.',
    plannedFeatures: [
      'Filterable event log by actor, application ID, and timestamp',
      'Detailed event payload inspection',
      'Exportable CSV audit trail',
    ],
  },
  '/auditor/reports': {
    title: 'Validation Reports & Certificates',
    specSection: 'Section 6.8 — Report Generation & Export',
    description: 'Generate standardized AICTE regulatory verification summaries and ICPL proof manifests.',
    plannedFeatures: [
      'JSON regulatory validation report generation',
      'PDF printable executive summary download',
      'Merkle root hash certificate verification',
    ],
  },
  '/auditor/assist': {
    title: 'AIC Assist — Regulatory Intelligence',
    specSection: 'Section 6.9 — Cited Handbook Retrieval Assistant',
    description: 'AICTE Approval Process Handbook question-answering assistant with verbatim citations and page references.',
    plannedFeatures: [
      'Retrieval-only regulatory cited assistant (no hallucinated policies)',
      'Handbook clause and page citations',
      'Non-executing decision support boundary',
    ],
  },

  // Institution routes
  '/institution/applications': {
    title: 'Institutional Applications',
    specSection: 'Section 6.1 — Applicant Self-Disclosure Management',
    description: 'History and active submissions of Extension of Approval self-disclosure applications.',
    plannedFeatures: [
      'Revision tracking (Rev-00, Rev-01) for resubmissions',
      'Downloadable submission receipts',
      'Checklist completion progress indicators',
    ],
  },
  '/institution/applications/new': {
    title: 'New Application Disclosure',
    specSection: 'Section 6.1 — Application Wizard & Self-Disclosure',
    description: 'AY 2026-27 self-disclosure creation wizard for Extension of Approval (EoA).',
    plannedFeatures: [
      'Institution details and programme category selection',
      'Annexure 2.1 preliminary applicability questionnaire',
      'Draft saving and pre-validation checks',
    ],
  },
  '/institution/documents': {
    title: 'Document Center',
    specSection: 'Section 6.1 — Secure Document Upload & Quarantine',
    description: 'Secure document management repository for uploading mandatory Annexure 2.1 evidence.',
    plannedFeatures: [
      'Drag-and-drop secure upload with client-side SHA-256 calculation',
      'Format and file size validation (PDF, &lt; 20MB)',
      'Instant OCR and field extraction processing status',
      'Immutable document versioning',
    ],
  },
  '/institution/rectification': {
    title: 'Rectification & Resubmission Portal',
    specSection: 'Section 6.1 — Deficiency Rectification Workflow',
    description: 'Applicant interface for responding to auditor deficiency notices and uploading corrected documents.',
    plannedFeatures: [
      'Formal deficiency notices dispatched by regulatory auditors',
      'Targeted replacement upload (creates immutable Rev-02)',
      'Rectification deadline countdown timer',
    ],
  },
  '/institution/activity': {
    title: 'Application Audit Trail',
    specSection: 'Section 6.1 — Applicant Status & Timeline',
    description: 'Real-time status updates and event timeline for submitted regulatory applications.',
    plannedFeatures: [
      'Milestone progression tracker',
      'Formal notice notifications',
      'Submission acknowledgment timestamps',
    ],
  },
  '/institution/reports': {
    title: 'Applicant Reports & Summaries',
    specSection: 'Section 6.1 — Submission Summary Documents',
    description: 'Exportable self-disclosure acknowledgment sheets and compliance reports.',
    plannedFeatures: [
      'Submitted self-disclosure summary (PDF)',
      'Payment receipt acknowledgment',
    ],
  },
  '/institution/assist': {
    title: 'AIC Assist for Applicants',
    specSection: 'Section 6.9 — Approval Handbook Guidance',
    description: 'Handbook guidance on Annexure 2.1 requirements, documentation norms, and affidavit formats.',
    plannedFeatures: [
      'Direct search of Approval Process Handbook 2026-27',
      'Clarifications on building age calculations and fire NOC norms',
    ],
  },

  // Lead routes
  '/lead/escalated-queue': {
    title: 'Escalated Triage Queue',
    specSection: 'Section 6.10 — Lead Auditor Oversight',
    description: 'Priority queue of cases referred by primary auditors for supervisory exemption review.',
    plannedFeatures: [
      'Detailed auditor referral notes and rule references',
      'Waiver decision interface (Approve Waiver / Require Re-audit / Referral for Inspection)',
    ],
  },
  '/lead/case-review': {
    title: 'Lead Case Review',
    specSection: 'Section 6.10 — Supervisory Adjudication Workspace',
    description: 'Supervisory review of complex regulatory contradictions and policy exceptions.',
    plannedFeatures: [
      'Side-by-side comparison of auditor recommendations and evidence documents',
      'Statutory waiver notes authoring',
    ],
  },
  '/lead/recommendations': {
    title: 'Statutory Approval Recommendations',
    specSection: 'Section 6.11 — Final Regulatory Recommendation Pipeline',
    description: 'Compilation of recommendations for transmission to the AICTE Competent Approval Bureau.',
    plannedFeatures: [
      'Drafting formal recommendations (Recommended / Recommended with Conditions / Not Recommended)',
      'Digital signature authorization preview',
    ],
  },
  '/lead/inspection-referrals': {
    title: 'On-Site Inspection Referrals',
    specSection: 'Section 6.12 — Expert Visit Committee (EVC) Referrals',
    description: 'Refer high-risk institutions with unresolved discrepancies for physical inspection.',
    plannedFeatures: [
      'Inspection mandate generator with highlighted evidence coordinates',
      'EVC committee assignment',
    ],
  },
  '/lead/temporal-replay': {
    title: 'Temporal Compliance Replay',
    specSection: 'Section 6.13 — Historical Audit Replay Engine',
    description: 'Replay historical regulatory evaluations against pinned rule versions and historical source data.',
    plannedFeatures: [
      'Historical validation run vs current rule set comparison',
      'Pinned source record replay (preventing silent current-data corruption)',
      'Side-by-side discrepancy delta viewer',
    ],
  },
  '/lead/audit-history': {
    title: 'Audit History & Merkle Verification',
    specSection: 'Section 6.14 — Cryptographic Proof & Ledger',
    description: 'Verification of immutable ICPL hash chains and Merkle root proofs.',
    plannedFeatures: [
      'Merkle tree root visualizer',
      'SHA-256 chain verification check',
      'Tamper-evident regulatory export manifest',
    ],
  },

  // Admin routes
  '/admin/users': {
    title: 'Users & Role Management',
    specSection: 'Section 6.15 — User Administration & RBAC',
    description: 'Administration of institution accounts, regulatory auditors, lead supervisors, and review teams.',
    plannedFeatures: [
      'Role assignment: Institution User, Auditor, Lead Auditor, Admin',
      'Account lockout and password policy management',
    ],
  },
  '/admin/teams': {
    title: 'Review Teams & Regional Squads',
    specSection: 'Section 6.15 — Audit Team Allocation',
    description: 'Configuration of regional verification squads and case assignment rules.',
    plannedFeatures: [
      'Regional allocation (Region West, North, South, East, Central)',
      'Workload balancing and case dispatch rules',
    ],
  },
  '/admin/rules': {
    title: 'Regulatory Rule Configuration',
    specSection: 'Section 6.16 — Versioned Rule Engine Management',
    description: 'Versioned management of the 7 Annexure 2.1 regulatory rule definitions and thresholds.',
    plannedFeatures: [
      'Building age threshold editor (e.g. 30-year rule EOA-SD-04)',
      'GPS coordinate tolerance configuration (e.g. 25m tolerance EOA-SD-06)',
      'Rule version pinning and activation for AY 2026-27',
    ],
  },
  '/admin/connectors': {
    title: 'External Issuer Connectors',
    specSection: 'Section 6.17 — Connector Administration',
    description: 'Configuration of simulated sandbox endpoints and authentication keys for external verification.',
    plannedFeatures: [
      'DigiLocker, State Land Registry, State GIS, and Bank UTR endpoints',
      'Simulated failure injection for testing auditor resilience',
    ],
  },
  '/admin/health': {
    title: 'System Health & Metrics',
    specSection: 'Section 6.18 — Observability & Telemetry',
    description: 'Operational health monitoring of FastAPI backend, Celery workers, and PostgreSQL database.',
    plannedFeatures: [
      'Worker queue depth and OCR processing latency',
      'Database connection pool metrics',
    ],
  },
  '/admin/logs': {
    title: 'Operational Security Logs',
    specSection: 'Section 6.18 — Security Audit Logs',
    description: 'Centralized security event logs, access attempts, and system exception traces.',
    plannedFeatures: [
      'Log stream with severity filter (INFO, WARN, ERROR, SECURITY)',
      'Exportable audit log archive',
    ],
  },
  '/admin/settings': {
    title: 'Platform Settings',
    specSection: 'Section 6.18 — Configuration & Boundaries',
    description: 'Global system configuration, environment parameters, and regulatory policy controls.',
    plannedFeatures: [
      'Academic year active cycle selector (AY 2026-27)',
      'Regulatory sandbox and connector policy toggles',
    ],
  },
};

export default function ModulePlaceholderPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentRoleConfig } = useDemoRole();

  const moduleConfig = MODULE_SPECS[location.pathname] || {
    title: location.pathname.split('/').pop()?.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || 'Module',
    specSection: 'AIC-Flow Prototype Specification v2',
    description: 'This feature is defined in the specification and scheduled for upcoming development milestones.',
    plannedFeatures: [
      'Enterprise role-based workflow integration',
      'Reconciliation with PostgreSQL schema v4',
      'Audit trail registration',
    ],
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {moduleConfig.title}
            </h1>
            <Badge variant="outline" className="text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200">
              Scheduled Milestone
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500">
            {currentRoleConfig.name} Scope • {moduleConfig.specSection}
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/auditor/dashboard')}
          className="h-8 text-xs border-slate-200 text-slate-700"
        >
          <ArrowLeft className="size-3.5 mr-1.5" />
          <span>Auditor Dashboard</span>
        </Button>
      </div>

      {/* Specification Card */}
      <Card className="bg-white border-slate-200/90 shadow-2xs">
        <CardHeader className="p-5 sm:p-6 pb-3">
          <div className="flex items-start gap-4">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Compass className="size-6" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">
                Specification Architecture: {moduleConfig.title}
              </CardTitle>
              <CardDescription className="text-xs text-slate-600 mt-1 leading-relaxed">
                {moduleConfig.description}
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5 sm:p-6 pt-2 space-y-4">
          <div className="rounded-lg bg-slate-50 border border-slate-200/80 p-4 space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-700 block">
              Planned Functional Capabilities (Per Specification v2):
            </span>
            <ul className="space-y-2 text-xs text-slate-600">
              {moduleConfig.plannedFeatures.map((feat, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="size-1.5 rounded-full bg-indigo-600 shrink-0 mt-1.5" />
                  <span>{feat}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
            <span>Reference Document: docs/reference/AIC_Verify_Prototype_Specification_v2.pdf</span>
            <span className="font-mono text-indigo-600 font-medium">AY 2026-27</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
