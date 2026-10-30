import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  BookOpen,
  Building2,
  CalendarClock,
  CalendarDays,
  ClipboardCheck,
  Clock3,
  Download,
  FileText,
  Gavel,
  Landmark,
  RefreshCw,
  Search,
  Workflow,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { DocumentUploadModal } from '@/components/documents/DocumentUploadModal';
import { documentsApi } from '@/features/documents/api';
import type { ApplicationRequirementItem } from '@/types/application';
import type { DocumentUploadResponse } from '@/types/document';
import { Badge } from '@/components/ui/badge';
import { countWorkflowCasesDueWithinSevenDays, filterWorkflowCases, workflowApplicationLinkPath, type WorkflowCaseQuickFilter } from '@/features/workflow/filters';
import { useAuth } from '@/hooks/useAuth';
import {
  workflowApi,
  type ComplianceObligation,
  type WorkflowCase,
  type WorkflowDetail,
  type WorkflowNotification,
  type DocumentValidityRecord,
} from '@/features/workflow/api';

type Workspace = 'institution' | 'auditor' | 'regional' | 'committee' | 'lead' | 'admin';

const LABELS: Record<string, string> = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  INTAKE_REVIEW: 'Initial checks',
  SCRUTINY: 'Application review',
  CLARIFICATION_REQUESTED: 'Clarification requested',
  RESUBMITTED: 'Updated application submitted',
  EVC_COORDINATION: 'Visit coordination',
  EVC_SCHEDULED: 'EVC scheduled',
  EVC_COMPLETED: 'EVC completed',
  COMMITTEE_PROCEEDINGS: 'Committee review',
  AWAITING_AUTHORITY: 'Awaiting decision',
  APPROVED: 'Approved',
  APPROVED_WITH_CONDITIONS: 'Approved with conditions',
  REJECTED: 'Rejected',
  ON_HOLD: 'On hold',
  OBLIGATION_TRACKING: 'Conditions follow-up',
  APPLICATION_STATUS_UPDATED: 'Application status updated',
  COMPLIANCE_REMINDER: 'Compliance reminder',
  DOCUMENT_EXPIRY_REMINDER: 'Document expiry reminder',
  DOCUMENT_VALIDITY_SUBMITTED: 'Document validity submitted',
  DOCUMENT_VALIDITY_REVIEWED: 'Document validity reviewed',
  OBLIGATION_CREATED: 'New approval condition',
  OBLIGATION_EVIDENCE_SUBMITTED: 'Condition evidence submitted',
  OBLIGATION_EVIDENCE_UNDER_REVIEW: 'Condition evidence under review',
  OBLIGATION_EVIDENCE_VERIFIED: 'Condition evidence verified',
  OBLIGATION_EVIDENCE_RETURNED: 'Condition evidence needs correction',
  OBLIGATION_COMPLETED: 'Condition completed',
  CLOSED: 'Closed',
  OPEN: 'Open',
  EVIDENCE_SUBMITTED: 'Evidence submitted',
  UNDER_VERIFICATION: 'Under verification',
  RETURNED: 'Returned',
  VERIFIED: 'Verified',
  APPLICATION_STATUS_UPDATED: 'Application status updated',
  COMPLIANCE_REMINDER: 'Compliance reminder',
  DOCUMENT_EXPIRY_REMINDER: 'Document expiry reminder',
  DOCUMENT_VALIDITY_SUBMITTED: 'Document validity submitted',
  DOCUMENT_VALIDITY_REVIEWED: 'Document validity reviewed',
  OBLIGATION_CREATED: 'New approval condition',
  OBLIGATION_EVIDENCE_SUBMITTED: 'Condition evidence submitted',
  OBLIGATION_EVIDENCE_UNDER_REVIEW: 'Condition evidence under review',
  OBLIGATION_EVIDENCE_VERIFIED: 'Condition evidence verified',
  OBLIGATION_EVIDENCE_RETURNED: 'Condition evidence needs correction',
  OBLIGATION_COMPLETED: 'Condition completed',
};

const ACTION_LABELS: Record<string, string> = {
  SUBMITTED: 'Submit application',
  INTAKE_REVIEW: 'Start initial checks',
  SCRUTINY: 'Start application review',
  CLARIFICATION_REQUESTED: 'Request clarification',
  RESUBMITTED: 'Submit updated application',
  AWAITING_AUTHORITY: 'Send for decision',
  CLOSED: 'Close application',
};

const actionLabel = (stage: string) => ACTION_LABELS[stage] || label(stage);

const label = (value?: string | null) => value ? (LABELS[value] || value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (part) => part.toUpperCase())) : '—';
const date = (value?: string | null) => value ? new Date(value).toLocaleDateString() : 'Not set';
const isOverdue = (value?: string | null) => Boolean(value && new Date(value).getTime() < Date.now());
const isClosedStage = (stage: string) => ['CLOSED', 'APPROVED', 'REJECTED'].includes(stage);

const PAGE_META: Record<string, { title: string; description: string }> = {
  overview: { title: 'Your work overview', description: 'See the applications, upcoming work and updates linked to your role.' },
  intake: { title: 'New applications', description: 'Check newly submitted applications and send complete applications to the review team.' },
  queue: { title: 'Your work queue', description: 'See applications waiting for action from your role.' },
  scrutiny: { title: 'Application review', description: 'Check the latest application details and supporting documents. Record any missing or incorrect information.' },
  clarification: { title: 'Waiting for institution response', description: 'See which applications are waiting for an institution to submit corrections or missing documents.' },
  're-scrutiny': { title: 'Updated applications', description: 'Review the corrected documents and information submitted by an institution.' },
  dossiers: { title: 'Application details', description: 'Open an application to see its documents, current status, actions and previous updates.' },
  reports: { title: 'Work reports', description: 'Download a list of the applications and work currently available to your role.' },
  evc: { title: 'Visits to arrange', description: 'Arrange visits for applications that require an EVC and record the visit details.' },
  calendar: { title: 'Visit schedule', description: 'Review proposed visit dates and the applications awaiting a visit report.' },
  overdue: { title: 'Overdue work', description: 'See applications and conditions that have passed their recorded due date.' },
  assigned: { title: 'Your assigned activities', description: 'Open the visits or proceedings assigned to your role.' },
  schedule: { title: 'Proceeding schedule', description: 'Review the schedule details for the selected proceeding.' },
  materials: { title: 'Application documents', description: 'Review the application documents shared for this visit or proceeding.' },
  observations: { title: 'Observations and meeting notes', description: 'Record the observations and minutes from the proceeding.' },
  completion: { title: 'Complete the proceeding', description: 'Save the required observations and meeting record before referring the application onward.' },
  regions: { title: 'Team workload comparison', description: 'Compare active applications, overdue work, visits and conditions across the teams you oversee.' },
  workload: { title: 'Workload by role', description: 'See how many active applications are waiting at each processing role.' },
  escalations: { title: 'Overdue applications', description: 'Review delayed work, record what action was taken and follow up unresolved items.' },
  decisions: { title: 'Applications awaiting your decision', description: 'Review the completed case record and enter the decision stated in the authorised order.' },
  analytics: { title: 'Progress and reports', description: 'Review application progress and download the current work and compliance reports.' },
  obligations: { title: 'Conditions and undertakings', description: 'Review the conditions recorded in the approval order and the evidence submitted against them.' },
  renewals: { title: 'Documents and renewals', description: 'Submit document validity details and review replacement documents and officer decisions.' },
  notifications: { title: 'Updates and reminders', description: 'See application updates, deadlines and items that need your attention.' },
  history: { title: 'Application updates', description: 'See the status changes and messages recorded for the selected application.' },
  'route-simulator': { title: 'Application path preview', description: 'Preview the processing steps currently configured for each application type. This does not change an application.' },
  sources: { title: 'Reference documents', description: 'Review the official documents and updates used when configuring application processing.' },
  deadlines: { title: 'Due-date rules', description: 'Review which dates come from official orders and which are internal processing reminders.' },
  'notification-policies': { title: 'Reminder settings', description: 'Review who receives reminders and when delayed work is brought to a supervisor.' },
};

const STAGE_GROUPS: Record<Workspace, string[]> = {
  institution: [],
  auditor: ['SUBMITTED', 'INTAKE_REVIEW', 'SCRUTINY', 'CLARIFICATION_REQUESTED', 'RESUBMITTED'],
  regional: ['EVC_COORDINATION', 'EVC_SCHEDULED', 'EVC_COMPLETED'],
  committee: ['COMMITTEE_PROCEEDINGS', 'EVC_COMPLETED'],
  lead: ['AWAITING_AUTHORITY', 'ON_HOLD', 'OBLIGATION_TRACKING', 'APPROVED', 'APPROVED_WITH_CONDITIONS', 'REJECTED'],
  admin: [],
};

interface Props {
  workspace: Workspace;
  section?: string;
}

export default function RoleWorkspacePage({ workspace, section: explicitSection }: Props) {
  const params = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const notificationApplicationId = searchParams.get('applicationId');
  const consumedNotificationApplicationId = useRef<string | null>(null);
  const section = explicitSection || params.section || 'overview';
  const auth = useAuth();
  const role = auth.activeContext?.role_code || '';
  const [cases, setCases] = useState<WorkflowCase[]>([]);
  const [obligations, setObligations] = useState<ComplianceObligation[]>([]);
  const [notifications, setNotifications] = useState<WorkflowNotification[]>([]);
  const [notificationFilter, setNotificationFilter] = useState<'ALL' | 'UNREAD' | 'READ' | 'WARNING'>('ALL');
  const [validityRecords, setValidityRecords] = useState<DocumentValidityRecord[]>([]);
  const [uploadRequirement, setUploadRequirement] = useState<ApplicationRequirementItem | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadPurpose, setUploadPurpose] = useState<'OBLIGATION' | 'VALIDITY' | null>(null);
  const [pendingObligationId, setPendingObligationId] = useState<string | null>(null);
  const [selected, setSelected] = useState<WorkflowDetail | null>(null);
  const [search, setSearch] = useState('');
  const [caseQuickFilter, setCaseQuickFilter] = useState<WorkflowCaseQuickFilter>('ALL');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [hasLoadedCases, setHasLoadedCases] = useState(false);
  const [error, setError] = useState('');
  const [evcDate, setEvcDate] = useState('');
  const [evcMode, setEvcMode] = useState('PHYSICAL');
  const [evcLocation, setEvcLocation] = useState('');
  const [reportReference, setReportReference] = useState('');
  const [proceedingType, setProceedingType] = useState('SHC');
  const [decisionOutcome, setDecisionOutcome] = useState('APPROVED_WITH_CONDITIONS');
  const [orderReference, setOrderReference] = useState('');
  const [decisionDate, setDecisionDate] = useState(new Date().toISOString().slice(0, 10));
  const [conditionTitle, setConditionTitle] = useState('');
  const [conditionDescription, setConditionDescription] = useState('');
  const [conditionSource, setConditionSource] = useState('');
  const [conditionDue, setConditionDue] = useState('');
  const [validityType, setValidityType] = useState('LEASE_DOCUMENT');
  const [validityIssuer, setValidityIssuer] = useState('');
  const [validFrom, setValidFrom] = useState('');
  const [validUntil, setValidUntil] = useState('');
  const [routeCategory, setRouteCategory] = useState('EOA_SELF_DISCLOSURE');

  const canLoadCases = workspace !== 'admin';
  const refresh = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      if (canLoadCases) {
        const caseResult = await workflowApi.cases();
        setCases(caseResult);
        const [obligationResult, notificationResult, validityResult] = await Promise.allSettled([
          workflowApi.obligations(),
          workflowApi.notifications(),
          workflowApi.documentValidity(),
        ]);
        if (obligationResult.status === 'fulfilled') setObligations(obligationResult.value);
        else setObligations([]);
        if (notificationResult.status === 'fulfilled') setNotifications(notificationResult.value);
        else setNotifications([]);
        if (validityResult.status === 'fulfilled') setValidityRecords(validityResult.value);
        else setValidityRecords([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load records from the approval workflow API.');
    } finally {
      setBusy(false);
      setHasLoadedCases(true);
    }
  }, [canLoadCases]);

  useEffect(() => { void refresh(); }, [refresh, role]);
  useEffect(() => { setCaseQuickFilter('ALL'); }, [section]);

  const visibleCases = useMemo(() => {
    let rows = cases;
    if (workspace === 'auditor' && section === 'intake') rows = rows.filter((item) => item.current_stage === 'SUBMITTED');
    if (workspace === 'auditor' && section === 'clarification') rows = rows.filter((item) => item.current_stage === 'CLARIFICATION_REQUESTED');
    if (workspace === 'institution' && section === 'clarification') rows = rows.filter((item) => item.current_stage === 'CLARIFICATION_REQUESTED');
    if (workspace === 'auditor' && section === 're-scrutiny') rows = rows.filter((item) => item.current_stage === 'RESUBMITTED');
    if (workspace === 'auditor' && section === 'scrutiny') rows = rows.filter((item) => ['INTAKE_REVIEW', 'SCRUTINY'].includes(item.current_stage));
    if (workspace === 'regional' && ['evc', 'calendar'].includes(section)) rows = rows.filter((item) => STAGE_GROUPS.regional.includes(item.current_stage));
    if (workspace === 'committee') rows = rows.filter((item) => item.current_stage === 'COMMITTEE_PROCEEDINGS' || (item.current_stage === 'EVC_COMPLETED' && item.route_snapshot.requires_committee === true) || (role === 'EVC_MEMBER' && item.current_stage === 'EVC_SCHEDULED'));
    if (workspace === 'lead' && section === 'decisions') rows = rows.filter((item) => item.current_stage === 'AWAITING_AUTHORITY');
    if ((workspace === 'lead' && section === 'escalations') || (workspace === 'regional' && section === 'overdue')) rows = rows.filter((item) => isOverdue(item.due_at) && !isClosedStage(item.current_stage));
    if (workspace === 'lead' && section === 'workload') rows = rows.filter((item) => !isClosedStage(item.current_stage));
    if (search.trim()) {
      const query = search.trim().toLowerCase();
      rows = rows.filter((item) => [item.application_number, item.institution_name, item.review_team_name || '', item.process_type, item.current_stage].some((value) => value.toLowerCase().includes(query)));
    }
    return rows;
  }, [cases, workspace, section, search, role]);

  const visibleObligations = useMemo(() => {
    let rows = obligations;
    if (workspace === 'lead' && section === 'escalations') rows = rows.filter((item) => isOverdue(item.due_at) && !['CLOSED', 'VERIFIED'].includes(item.status));
    if (search.trim()) {
      const query = search.trim().toLowerCase();
      rows = rows.filter((item) => [item.title, item.description, item.status].some((value) => value.toLowerCase().includes(query)));
    }
    return rows;
  }, [obligations, workspace, section, search]);

  const openCase = useCallback(async (item: WorkflowCase) => {
    setBusy(true);
    try {
      setSelected(await workflowApi.detail(item.workflow_case_id));
      setNote('');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Unable to open application details.');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!notificationApplicationId || busy || !hasLoadedCases || consumedNotificationApplicationId.current === notificationApplicationId) return;
    consumedNotificationApplicationId.current = notificationApplicationId;
    const match = cases.find((item) => item.application_id === notificationApplicationId);
    setSearchParams({}, { replace: true });
    if (!match) {
      toast.error('This application is not available in your current role or team.');
      return;
    }
    void openCase(match);
  }, [notificationApplicationId, cases, busy, hasLoadedCases, setSearchParams, openCase]);

  const transition = async (target: string, reasonOverride?: string) => {
    const reason = (reasonOverride || note).trim();
    if (!selected || reason.length < 8) {
      toast.error('Enter a reason of at least 8 characters before changing the case stage.');
      return;
    }
    setBusy(true);
    try {
      const updated = await workflowApi.transition(selected.workflow_case_id, target, reason);
      setSelected(updated);
      setNote('');
      await refresh();
      toast.success('Case moved to ' + label(target) + '.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'The backend rejected this transition.');
    } finally {
      setBusy(false);
    }
  };

  const recordEvent = async (eventType: string, summary: string, payload: Record<string, unknown>) => {
    if (!selected || summary.trim().length < 8) {
      toast.error('Select a case and provide a meaningful event summary.');
      return false;
    }
    setBusy(true);
    try {
      await workflowApi.event(selected.workflow_case_id, eventType, summary.trim(), payload);
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('Event recorded in the application audit timeline.');
      return true;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'The backend rejected this event.');
      return false;
    } finally {
      setBusy(false);
    }
  };

  const allowedTransitions = (item: WorkflowDetail) => {
    const stage = item.current_stage;
    if (role === 'INSTITUTION_USER') {
      if (stage === 'DRAFT') return ['SUBMITTED'];
      if (stage === 'CLARIFICATION_REQUESTED') return ['RESUBMITTED'];
    }
    if (role === 'INTAKE_OFFICER' || role === 'AUDITOR') {
      if (stage === 'SUBMITTED') return ['INTAKE_REVIEW'];
      if (stage === 'RESUBMITTED' && item.route_snapshot.requires_scrutiny === false) return ['INTAKE_REVIEW'];
      if (stage === 'INTAKE_REVIEW' && item.route_snapshot.requires_scrutiny === false) return ['AWAITING_AUTHORITY', 'CLARIFICATION_REQUESTED'];
    }
    if (role === 'SCRUTINY_OFFICER' || role === 'AUDITOR') {
      if (stage === 'INTAKE_REVIEW' || stage === 'RESUBMITTED') return ['SCRUTINY'];
      if (stage === 'SCRUTINY') {
        const actions = ['CLARIFICATION_REQUESTED'];
        if (item.route_snapshot.requires_evc === true) actions.push('EVC_COORDINATION');
        else if (item.route_snapshot.requires_evc === false && item.route_snapshot.requires_committee === false) actions.push('AWAITING_AUTHORITY');
        return actions;
      }
    }
    if (role === 'REGIONAL_OFFICER' || role === 'EVC_COORDINATOR' || role === 'LEAD_AUDITOR') {
      if (stage === 'EVC_COMPLETED' && item.route_snapshot.requires_committee === false) return ['AWAITING_AUTHORITY'];
      if (stage === 'APPROVED' || stage === 'REJECTED') return ['CLOSED'];
    }
    if (role === 'COMMITTEE_SECRETARIAT' && stage === 'EVC_COMPLETED' && item.route_snapshot.requires_committee === true) {
      return ['COMMITTEE_PROCEEDINGS'];
    }
    if (role === 'COMPETENT_AUTHORITY' && stage === 'APPROVED_WITH_CONDITIONS' && item.obligations.length > 0) {
      return ['OBLIGATION_TRACKING'];
    }
    if ((role === 'BUREAU_SUPERVISOR' || role === 'REGIONAL_OFFICER' || role === 'LEAD_AUDITOR') && ['APPROVED', 'REJECTED', 'OBLIGATION_TRACKING'].includes(stage)) return ['CLOSED'];
    if ((role === 'BUREAU_SUPERVISOR' || role === 'REGIONAL_OFFICER' || role === 'LEAD_AUDITOR') && stage === 'ON_HOLD') return [item.route_snapshot.requires_scrutiny === true ? 'SCRUTINY' : 'INTAKE_REVIEW'];
    return [];
  };

  const createDecision = async () => {
    if (!selected || role !== 'COMPETENT_AUTHORITY' || selected.current_stage !== 'AWAITING_AUTHORITY') return;
    if (orderReference.trim().length < 3 || !decisionDate || note.trim().length < 8) {
      toast.error('Enter the official order reference, decision date and reason.');
      return;
    }
    const saved = await recordEvent('DECISION_RECORDED', 'Authorised decision recorded: ' + decisionOutcome + '. ' + note.trim(), {
      outcome: decisionOutcome,
      official_order_reference: orderReference.trim(),
      decision_date: decisionDate,
      authority_role: role,
      statutory_decision_made_by_human: true,
    });
    if (saved) await transition(decisionOutcome, 'Decision recorded under order ' + orderReference.trim() + ': ' + note.trim());
  };

  const registerCondition = async () => {
    if (!selected || !conditionTitle.trim() || !conditionDescription.trim() || !conditionSource.trim() || !conditionDue) {
      toast.error('Complete the condition text, source/order and due date.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.createObligation(selected.workflow_case_id, {
        title: conditionTitle.trim(),
        description: conditionDescription.trim(),
        source_condition: conditionSource.trim(),
        due_at: new Date(conditionDue + 'T23:59:00').toISOString(),
      });
      setConditionTitle('');
      setConditionDescription('');
      setConditionSource('');
      setConditionDue('');
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('Decision condition added to the obligation ledger.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not register the obligation.');
    } finally {
      setBusy(false);
    }
  };

  const chooseUploadRequirement = (detail: WorkflowDetail, type: string) => {
    const expectedType = type === 'FIRE_SAFETY'
      ? 'FIRE_SAFETY_CERTIFICATE'
      : type;
    return detail.requirements.find((item) =>
      item.applicability_status === 'APPLICABLE'
      && item.expected_document_type_code === expectedType
      && item.status !== 'SATISFIED'
    ) || detail.requirements.find((item) =>
      item.applicability_status === 'APPLICABLE'
      && item.expected_document_type_code === expectedType
    );
  };

  const beginValidityUpload = () => {
    if (!selected || role !== 'INSTITUTION_USER' || !validityIssuer.trim() || !validUntil) {
      toast.error('Select an application and complete issuer and validity dates first.');
      return;
    }
    const requirement = chooseUploadRequirement(selected, validityType);
    if (!requirement) {
      toast.error('This application does not have a matching required document. Check the application checklist before adding validity dates; the system will not attach a file to an unrelated requirement.');
      return;
    }
    setUploadPurpose('VALIDITY');
    setUploadRequirement(requirement);
    setUploadOpen(true);
  };

  const beginObligationUpload = async (item: ComplianceObligation) => {
    try {
      const detail = await workflowApi.detail(item.workflow_case_id);
      setSelected(detail);
      const conditionText = (item.title + ' ' + item.description).toLowerCase();
      const expectedDocumentType = conditionText.includes('fire')
        ? 'FIRE_SAFETY_CERTIFICATE'
        : conditionText.includes('affidavit') || conditionText.includes('undertaking')
          ? 'AFFIDAVIT_UNDERTAKING'
          : conditionText.includes('building') || conditionText.includes('occupancy')
            ? 'BUILDING_DOCUMENT'
            : null;
      if (!expectedDocumentType) {
        toast.error('This condition does not match a document already listed on the application. Ask the processing team to add the correct requirement before submitting evidence.');
        return;
      }
      const requirement = chooseUploadRequirement(detail, expectedDocumentType);
      if (!requirement) {
        toast.error('The matching document requirement is not applicable or is not present on this application revision.');
        return;
      }
      setPendingObligationId(item.obligation_id);
      setUploadPurpose('OBLIGATION');
      setUploadRequirement(requirement);
      setUploadOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Unable to open the linked application.');
    }
  };

  const handleDocumentUploaded = async (response: DocumentUploadResponse) => {
    if (!response.document_version.is_clean || !uploadRequirement) {
      toast.warning('The document is not clean-scanned. It cannot be attached to a compliance or validity record.');
      return;
    }
    try {
      const version = response.document_version;
      try {
        const job = await documentsApi.process(
          response.application_requirement_id,
          version.document_version_id,
        );
        toast.success('Document saved and extraction queued.', {
          description: 'Processing status: ' + job.processing_status.toLowerCase(),
        });
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Document saved, but extraction could not be queued.');
      }

      if (uploadPurpose === 'OBLIGATION' && pendingObligationId) {
        await workflowApi.obligationAction(
          pendingObligationId,
          'EVIDENCE_SUBMITTED',
          note.trim().length >= 5 ? note.trim() : 'Institution submitted clean-scanned supporting evidence.',
          undefined,
          version.document_id,
        );
        toast.success('Evidence submitted for officer verification.');
      } else if (uploadPurpose === 'VALIDITY' && selected) {
        await workflowApi.createDocumentValidity(selected.workflow_case_id, {
          document_id: version.document_id,
          document_version_id: version.document_version_id,
          document_type: validityType,
          issuer: validityIssuer.trim(),
          valid_from: validFrom || null,
          valid_until: validUntil,
          document_reference: version.original_filename + ' · version ' + version.version_number,
        });
        toast.success('Validity record saved and queued for officer verification.');
        setValidityIssuer('');
        setValidFrom('');
        setValidUntil('');
      }
      await refresh();
      if (selected) setSelected(await workflowApi.detail(selected.workflow_case_id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'The record could not be linked to the uploaded document.');
    } finally {
      setPendingObligationId(null);
      setUploadPurpose(null);
    }
  };

  const obligationAction = async (id: string, action: string, reference?: string) => {
    if (note.trim().length < 5) {
      toast.error('Add a reason or evidence description for this action.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.obligationAction(id, action, note.trim(), reference);
      setNote('');
      await refresh();
      if (selected) setSelected(await workflowApi.detail(selected.workflow_case_id));
      toast.success('Obligation updated: ' + label(action) + '.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'The obligation action was rejected.');
    } finally {
      setBusy(false);
    }
  };

  const exportCsv = () => {
    let header: string[];
    let rows: string[][];

    if (section === 'obligations' || section === 'escalations') {
      header = ['Obligation reference', 'Condition', 'Description', 'Status', 'Due date', 'Source order or clause', 'Evidence reference', 'Verification note'];
      rows = visibleObligations.map((item) => [
        item.obligation_id,
        item.title,
        item.description,
        item.status,
        item.due_at,
        item.source_condition,
        item.evidence_reference || '',
        item.verification_note || '',
      ]);
    } else if (section === 'renewals') {
      header = ['Validity record', 'Application reference', 'Document type', 'Issuer', 'Valid from', 'Valid until', 'Verification status', 'Document reference', 'Replacement record'];
      rows = validityRecords
        .filter((item) => !selected || item.workflow_case_id === selected.workflow_case_id)
        .map((item) => [
          item.document_validity_id,
          item.application_id,
          item.document_type,
          item.issuer,
          item.valid_from || '',
          item.valid_until,
          item.verification_status,
          item.document_reference,
          item.replacement_of_id || '',
        ]);
    } else if (section === 'analytics') {
      header = ['Record type', 'Record reference', 'Institution or application', 'Process or condition', 'Status', 'Owner role', 'Due date', 'Source'];
      rows = [
        ...visibleCases.map((item) => [
          'APPLICATION',
          item.application_number,
          item.institution_name,
          item.process_type,
          item.current_stage,
          item.assigned_role_code || '',
          item.due_at || '',
          item.route_code,
        ]),
        ...visibleObligations.map((item) => [
          'OBLIGATION',
          item.obligation_id,
          item.application_id,
          item.title,
          item.status,
          '',
          item.due_at,
          item.source_condition,
        ]),
        ...validityRecords.map((item) => [
          'DOCUMENT_VALIDITY',
          item.document_validity_id,
          item.application_id,
          item.document_type + ' · ' + item.issuer,
          item.verification_status,
          '',
          item.valid_until,
          item.document_reference,
        ]),
      ];
    } else {
      header = ['Application reference', 'Institution', 'Process type', 'Academic year', 'Route', 'Current stage', 'Assigned role', 'Due date'];
      rows = visibleCases.map((item) => [
        item.application_number,
        item.institution_name,
        item.process_type,
        item.academic_year,
        item.route_code,
        item.current_stage,
        item.assigned_role_code || '',
        item.due_at || '',
      ]);
    }

    const escape = (value: string) => '"' + String(value).replaceAll('"', '""') + '"';
    const csv = [header, ...rows].map((row) => row.map((value) => escape(String(value))).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'aic-flow-' + workspace + '-' + section + '.csv';
    anchor.click();
    URL.revokeObjectURL(url);
    toast.success('CSV generated from the currently loaded authorised records.');
  };

  const markNotificationRead = async (id: string) => {
    try {
      const changed = await workflowApi.markRead(id);
      setNotifications((previous) => previous.map((item) => item.notification_id === id ? changed : item));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not update notification state.');
    }
  };

  const markAllNotificationsRead = async () => {
    const unread = notifications.filter((item) => !item.read_at);
    if (unread.length === 0) return;
    setBusy(true);
    try {
      const results = await Promise.allSettled(unread.map((item) => workflowApi.markRead(item.notification_id)));
      const failed = results.filter((item) => item.status === 'rejected').length;
      await refresh();
      if (failed) toast.warning(failed + ' notification(s) could not be marked as read.');
      else toast.success('All notifications in this account have been marked as read.');
    } finally {
      setBusy(false);
    }
  };

  const unreadCount = notifications.filter((item) => !item.read_at).length;
  const activeCount = cases.filter((item) => !isClosedStage(item.current_stage)).length;
  const overdueCases = cases.filter((item) => isOverdue(item.due_at) && !isClosedStage(item.current_stage));
  const dueObligations = obligations.filter((item) => isOverdue(item.due_at) && !['CLOSED', 'VERIFIED'].includes(item.status));
  const page = PAGE_META[section] || PAGE_META.overview;

  const summaryCards = workspace === 'institution'
    ? [
        { label: 'My applications', value: cases.length, icon: Building2 },
        { label: 'Open obligations', value: obligations.filter((item) => !['CLOSED', 'VERIFIED'].includes(item.status)).length, icon: ClipboardCheck },
        { label: 'Overdue items', value: overdueCases.length + dueObligations.length, icon: AlertTriangle },
        { label: 'Unread alerts', value: unreadCount, icon: Bell },
      ]
    : workspace === 'auditor'
      ? [
          { label: 'Cases in scope', value: cases.length, icon: FileText },
          { label: 'Awaiting scrutiny', value: cases.filter((item) => ['INTAKE_REVIEW', 'SCRUTINY', 'RESUBMITTED'].includes(item.current_stage)).length, icon: ClipboardCheck },
          { label: 'Clarifications', value: cases.filter((item) => item.current_stage === 'CLARIFICATION_REQUESTED').length, icon: Clock3 },
          { label: 'Overdue stages', value: overdueCases.length, icon: AlertTriangle },
        ]
      : workspace === 'regional'
        ? [
            { label: 'Regional cases in scope', value: cases.length, icon: Building2 },
            { label: 'EVC coordination', value: cases.filter((item) => item.current_stage === 'EVC_COORDINATION').length, icon: CalendarClock },
            { label: 'Scheduled visits', value: cases.filter((item) => item.current_stage === 'EVC_SCHEDULED').length, icon: CalendarDays },
            { label: 'Overdue cases', value: overdueCases.length, icon: AlertTriangle },
          ]
        : workspace === 'committee'
          ? [
              { label: 'Proceedings in scope', value: cases.length, icon: Landmark },
              { label: 'Awaiting proceedings', value: cases.filter((item) => item.current_stage === 'COMMITTEE_PROCEEDINGS').length, icon: BookOpen },
              { label: 'Pending reports', value: cases.filter((item) => item.current_stage === 'EVC_COMPLETED' && item.route_snapshot.requires_committee === true).length, icon: Clock3 },
              { label: 'Unread alerts', value: unreadCount, icon: Bell },
            ]
          : [
              { label: 'Cases in scope', value: cases.length, icon: FileText },
              { label: 'Active stages', value: activeCount, icon: Workflow },
              { label: 'Awaiting decision', value: cases.filter((item) => item.current_stage === 'AWAITING_AUTHORITY').length, icon: Gavel },
              { label: 'Overdue items', value: overdueCases.length + dueObligations.length, icon: AlertTriangle },
            ];

  const filteredNotifications = notifications.filter((item) => {
    if (notificationFilter === 'UNREAD') return !item.read_at;
    if (notificationFilter === 'READ') return Boolean(item.read_at);
    if (notificationFilter === 'WARNING') return item.severity === 'WARNING';
    return true;
  });

  if (workspace === 'admin' && section === 'route-simulator') {
    const profile = routeCategory === 'EOA_SELF_DISCLOSURE'
      ? { route: 'EOA_SELF_DISCLOSURE', stages: ['Intake review', 'Competent authority'], scrutiny: 'Not required in the currently configured baseline profile', evc: 'Not required in the currently configured baseline profile', committee: 'Not applicable in the currently configured baseline profile', status: 'Configured baseline' }
      : routeCategory === 'INCREASE_INTAKE'
        ? { route: 'INCREASE_INTAKE_SCRUTINY_EVC', stages: ['Intake review', 'Scrutiny', 'EVC coordination', 'EVC schedule', 'EVC completion', 'Committee applicability review', 'Competent authority'], scrutiny: 'Required by configured baseline profile', evc: 'Required by configured baseline profile', committee: 'Unresolved: authorised policy confirmation required', status: 'Partially configured baseline' }
        : { route: 'ROUTE_PENDING_POLICY_CONFIRMATION', stages: ['Authorised policy review'], scrutiny: 'Not resolved', evc: 'Not resolved', committee: 'Not resolved', status: 'Manual confirmation required' };
    return (
      <div className="space-y-5">
        <PageHeading title={page.title} description={page.description} onRefresh={refresh} busy={busy} showRefresh={false} />
        <SyntheticNotice />
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[260px] flex-1">
              <label className="mb-1.5 block text-xs font-semibold text-slate-700">Application category profile</label>
              <select value={routeCategory} onChange={(event) => setRouteCategory(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm">
                <option value="EOA_SELF_DISCLOSURE">Extension of Approval — self-disclosure</option>
                <option value="INCREASE_INTAKE">Increase in intake / additional courses</option>
                <option value="UNCONFIGURED">Unconfigured / unknown category</option>
              </select>
            </div>
            <Badge variant="outline">{profile.status}</Badge>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
            <div className="rounded-lg border border-slate-200 p-4">
              <h2 className="font-semibold text-slate-900">Resolved stage path</h2>
              <ol className="mt-3 space-y-2">{profile.stages.map((stage, index) => <li key={stage} className="flex items-center gap-2 text-sm"><span className="flex size-6 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700">{index + 1}</span><span className="text-slate-700">{stage}</span></li>)}</ol>
            </div>
            <div className="space-y-3 rounded-lg border border-slate-200 p-4 text-sm">
              <h2 className="font-semibold text-slate-900">Why this route applies</h2>
              <p><span className="text-slate-500">Scrutiny:</span> {profile.scrutiny}</p>
              <p><span className="text-slate-500">EVC:</span> {profile.evc}</p>
              <p><span className="text-slate-500">SAC / SHC:</span> {profile.committee}</p>
              <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-900">This is a read-only preview of the route profiles currently implemented in the backend. It is not an APH policy publisher, does not create a route snapshot and must not be treated as confirmation of later amendments.</div>
              <div className="text-xs text-slate-500">Regulatory baseline shown by configured profiles: APH 2024–2027 baseline. Verify effective corrigenda and category-specific clauses before operational activation.</div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (workspace === 'admin') {
    const policyRole = role === 'REGULATORY_POLICY_PUBLISHER';
    const adminLinks = [
      { title: 'Users and roles', description: 'Provision accounts and manage granted permission packages.', href: '/admin/users', allowed: !policyRole },
      { title: 'Review teams', description: 'Manage operational teams and memberships.', href: '/admin/teams', allowed: !policyRole },
      { title: 'Workflow and validation rules', description: 'Review the currently configured rule administration screen.', href: '/admin/rules', allowed: true },
      { title: 'Regulatory source register', description: 'Review baseline source references and amendment verification status.', href: '/admin/policy/sources', allowed: policyRole },
      { title: 'Category route simulator', description: 'Preview only implemented route profiles without changing a live case.', href: '/admin/policy/route-simulator', allowed: policyRole },
      { title: 'Deadline policies', description: 'Review deadline classes and distinguish statutory time from internal targets.', href: '/admin/policy/deadlines', allowed: policyRole },
      { title: 'Notification policies', description: 'Review reminder and escalation policy requirements.', href: '/admin/policy/notifications', allowed: policyRole },
      { title: 'Integrations', description: 'Inspect configured connector metadata; no production integration is implied.', href: '/admin/connectors', allowed: !policyRole },
      { title: 'System health and logs', description: 'Inspect platform health and technical event logs.', href: '/admin/health', allowed: !policyRole },
      { title: 'Settings', description: 'Platform settings and environment configuration.', href: '/admin/settings', allowed: !policyRole },
    ].filter((item) => item.allowed);
    if (['sources', 'deadlines', 'notification-policies'].includes(section)) {
      const isSource = section === 'sources';
      const rows = isSource
        ? [
            ['APH 2024–2027', 'Baseline referenced by configured route profiles', 'Verify current amendments before publication'],
            ['PIB release · 6 Dec 2023', 'Handbook announcement / context', 'Context source, not route configuration'],
            ['Category route bundle', 'Backend profile: EoA self-disclosure', 'Configured baseline profile'],
            ['Category route bundle', 'Backend profile: Increase in intake', 'Committee applicability unresolved'],
          ]
        : section === 'deadlines'
          ? [
              ['Statutory / regulatory', 'Explicit regulation or official order', 'Requires verified source, clause and counting convention'],
              ['Annual processing schedule', 'Academic-year schedule / official notice', 'Must be effective-year specific'],
              ['Case-specific order condition', 'Deadline in authorised decision/order', 'Must preserve exact order and basis date'],
              ['Administrative target', 'Internal processing target', 'Must never be labelled statutory'],
              ['Reminder window', 'Advance notification window', 'Operational policy, not legal deadline'],
            ]
          : [
              ['Advance reminders', 'Configurable windows such as 30 / 15 / 7 days', 'Policy not published by this screen'],
              ['Deduplication', 'Recipient + event + policy version + reminder window', 'Required before production scheduling'],
              ['Escalation levels', 'Designated role / scope / overdue threshold', 'Requires approved recipient and threshold policy'],
              ['Delivery attempts', 'Persist provider response and bounded retries', 'External channels remain disabled unless authorised'],
            ];
      return (
        <div className="space-y-5">
          <PageHeading title={page.title} description={page.description} onRefresh={refresh} busy={busy} showRefresh={false} />
          <SyntheticNotice />
          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 p-4"><h2 className="font-semibold text-slate-900">Configuration review</h2><p className="mt-1 text-xs text-slate-500">Read-only reference view. No publish or activation control is exposed because a persistence-backed policy API is not yet present.</p></div>
            <div className="divide-y divide-slate-100">{rows.map((row) => <div key={row[0]} className="grid gap-2 p-4 md:grid-cols-[190px_1fr_1fr]"><div className="text-sm font-semibold text-slate-800">{row[0]}</div><div className="text-sm text-slate-600">{row[1]}</div><div className="text-xs text-amber-700">{row[2]}</div></div>)}</div>
          </section>
        </div>
      );
    }
    return (
      <div className="space-y-5">
        <PageHeading title="Administration workspace" description={policyRole ? 'Regulatory source and workflow policy governance.' : 'Technical administration, account provisioning and platform operations.'} onRefresh={refresh} busy={busy} showRefresh={false} />
        <SyntheticNotice />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{adminLinks.map((item) => <Link key={item.href} to={item.href} className="rounded-xl border border-slate-200 bg-white p-4 transition hover:border-indigo-300 hover:shadow-sm"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">{item.title}</h2><ArrowRight className="size-4 text-indigo-600" /></div><p className="mt-2 text-sm text-slate-500">{item.description}</p></Link>)}</div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">Platform Administrator accounts do not inherit confidential case access or statutory decision authority. Regulatory Policy Publisher accounts are separate and cannot record case decisions.</div>
      </div>
    );
  }

  const noCaseSections = ['notifications', 'obligations'];
  const showCaseQueue = !noCaseSections.includes(section);
  const caseList = showCaseQueue ? visibleCases : [];
  const nowMs = Date.now();
  const overdueQueueCount = caseList.filter((item) => isOverdue(item.due_at) && !isClosedStage(item.current_stage)).length;
  const dueSoonQueueCount = countWorkflowCasesDueWithinSevenDays(caseList, nowMs);
  const filteredCaseList = filterWorkflowCases(caseList, caseQuickFilter, nowMs);
  const groupedTeams = new Map<string, { id: string; name: string; applications: WorkflowCase[] }>();
  for (const item of cases) {
    const id = item.review_team_id || 'unassigned';
    const name = item.review_team_name || 'Unassigned team';
    const group = groupedTeams.get(id) || { id, name, applications: [] };
    group.applications.push(item);
    groupedTeams.set(id, group);
  }
  const teamSummaries = Array.from(groupedTeams.values()).map((team) => {
    const ids = new Set(team.applications.map((item) => item.workflow_case_id));
    const linkedObligations = obligations.filter((item) => ids.has(item.workflow_case_id));
    return {
      ...team,
      active: team.applications.filter((item) => !isClosedStage(item.current_stage)).length,
      overdue: team.applications.filter((item) => isOverdue(item.due_at) && !isClosedStage(item.current_stage)).length
        + linkedObligations.filter((item) => isOverdue(item.due_at) && !['CLOSED', 'VERIFIED'].includes(item.status)).length,
      evc: team.applications.filter((item) => ['EVC_COORDINATION', 'EVC_SCHEDULED', 'EVC_COMPLETED'].includes(item.current_stage)).length,
      authority: team.applications.filter((item) => item.current_stage === 'AWAITING_AUTHORITY').length,
      obligations: linkedObligations.length,
    };
  }).sort((a, b) => a.name.localeCompare(b.name));
  const roleWorkloadCounts = new Map<string, number>();
  for (const item of cases.filter((entry) => !isClosedStage(entry.current_stage))) {
    const key = item.assigned_role_code || 'UNASSIGNED';
    roleWorkloadCounts.set(key, (roleWorkloadCounts.get(key) || 0) + 1);
  }
  const roleWorkload = Array.from(roleWorkloadCounts.entries())
    .map(([roleCode, count]) => ({ roleCode, count }))
    .sort((a, b) => b.count - a.count || a.roleCode.localeCompare(b.roleCode));
  const selectedObligations = selected ? selected.obligations : [];
  const pendingEvc = selected && selected.current_stage === 'EVC_COORDINATION';
  const pendingEvcReport = selected && selected.current_stage === 'EVC_SCHEDULED';
  const pendingProceeding = selected && selected.current_stage === 'COMMITTEE_PROCEEDINGS';
  const canConfirmDocument = ['SCRUTINY_OFFICER', 'AUDITOR', 'REGIONAL_OFFICER', 'BUREAU_SUPERVISOR', 'LEAD_AUDITOR'].includes(role);

  return (
    <div className="space-y-5">
      <PageHeading title={page.title} description={page.description} onRefresh={refresh} busy={busy} onExport={['reports', 'analytics', 'obligations', 'escalations', 'renewals'].includes(section) ? exportCsv : undefined} />
      <SyntheticNotice />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((item) => <Metric key={item.label} label={item.label} value={item.value} icon={item.icon} />)}
      </div>

      {workspace === 'lead' && section === 'regions' ? (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
            <div>
              <h2 className="font-semibold text-slate-900">Team workload comparison</h2>
              <p className="mt-1 text-xs text-slate-500">Compare the applications and follow-up work in the review teams you oversee.</p>
            </div>
            <Badge variant="secondary">{teamSummaries.length} teams</Badge>
          </div>
          {teamSummaries.length === 0 ? (
            <Empty title="No team activity to compare" description="Team summaries appear when applications are assigned to your review teams."/>
          ) : (
            <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
              {teamSummaries.map((team) => (
                <button key={team.id} type="button" onClick={() => setSearch(team.name)} className="min-w-0 rounded-lg border border-slate-200 p-4 text-left transition hover:border-indigo-300 hover:bg-indigo-50/30">
                  <div className="flex items-start justify-between gap-2">
                    <span className="break-words text-sm font-semibold text-slate-900">{team.name}</span>
                    <Badge variant="secondary">{team.applications.length} applications</Badge>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-md bg-slate-50 p-2"><span className="text-slate-500">Active</span><div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{team.active}</div></div>
                    <div className="rounded-md bg-slate-50 p-2"><span className="text-slate-500">Overdue</span><div className="mt-1 text-lg font-semibold tabular-nums text-red-700">{team.overdue}</div></div>
                    <div className="rounded-md bg-slate-50 p-2"><span className="text-slate-500">EVC visits</span><div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{team.evc}</div></div>
                    <div className="rounded-md bg-slate-50 p-2"><span className="text-slate-500">Awaiting decision</span><div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{team.authority}</div></div>
                  </div>
                  <div className="mt-3 text-xs text-indigo-700">{team.obligations} linked conditions · Select to view applications</div>
                </button>
              ))}
            </div>
          )}
          <div className="border-t border-slate-100 px-4 py-3 text-[11px] text-slate-500">Demo team names are fictional review groups, not official AICTE regions.</div>
        </section>
      ) : null}

      {workspace === 'lead' && section === 'workload' ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between gap-2">
            <div><h2 className="font-semibold text-slate-900">Active applications by role</h2><p className="mt-1 text-xs text-slate-500">Counts are based on the current applications assigned to your teams.</p></div>
            <Badge variant="secondary">{roleWorkload.reduce((sum, item) => sum + item.count, 0)} active</Badge>
          </div>
          {roleWorkload.length === 0 ? <Empty title="No active applications" description="There are no active applications in the current team scope."/> : (
            <div className="mt-4 space-y-3">
              {roleWorkload.map((item) => {
                const total = Math.max(1, roleWorkload.reduce((sum, value) => sum + value.count, 0));
                const share = Math.round((item.count / total) * 100);
                return <div key={item.roleCode}>
                  <div className="mb-1 flex items-center justify-between gap-2 text-xs"><span className="font-medium text-slate-700">{label(item.roleCode)}</span><span className="tabular-nums text-slate-500">{item.count}</span></div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: share + '%' }}/></div>
                </div>;
              })}
            </div>
          )}
        </section>
      ) : null}

      {error && <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{error}</div>}

      {section === 'notifications' ? (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
            <div className="flex items-center gap-2"><Bell className="size-4 text-indigo-600"/><h2 className="font-semibold text-slate-900">Your notification inbox</h2><Badge variant="secondary">{unreadCount} unread</Badge></div>
            <div className="flex flex-wrap items-center gap-2">
              <select value={notificationFilter} onChange={(event) => setNotificationFilter(event.target.value as typeof notificationFilter)} aria-label="Filter notifications" className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs">
                <option value="ALL">All notifications</option>
                <option value="UNREAD">Unread only</option>
                <option value="READ">Read only</option>
                <option value="WARNING">Action required</option>
              </select>
              <Button size="sm" variant="outline" disabled={busy || unreadCount === 0} onClick={() => void markAllNotificationsRead()}>Mark all read</Button>
            </div>
          </div>
          {filteredNotifications.length === 0 ? <Empty title="No notifications in this account" description="Notifications appear when a scoped workflow event has a recipient match."/> : <div className="divide-y divide-slate-100">{filteredNotifications.map((item) => <div key={item.notification_id} className="flex flex-wrap items-start justify-between gap-3 p-4"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-sm text-slate-900">{item.title}</span>{item.severity === 'WARNING' ? <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-800">Action required</Badge> : <Badge variant="secondary">Information</Badge>}{!item.read_at && <Badge variant="outline">Unread</Badge>}</div><p className="mt-1 text-sm text-slate-600">{item.body}</p><p className="mt-1 text-xs text-slate-400">{new Date(item.created_at).toLocaleString()}</p></div><div className="flex flex-wrap items-center gap-2">
                    {item.application_id && <Button size="sm" variant="outline" onClick={() => {
                      if (!item.read_at) void markNotificationRead(item.notification_id);
                      navigate(workflowApplicationLinkPath(workspace) + '?applicationId=' + encodeURIComponent(item.application_id!));
                    }}>Open application</Button>}
                    {!item.read_at && <Button size="sm" variant="ghost" onClick={() => void markNotificationRead(item.notification_id)}>Mark read</Button>}
                  </div></div>)}</div>}
        </section>
      ) : null}

      {section === 'obligations' || section === 'escalations' ? (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-100 p-4"><h2 className="font-semibold text-slate-900">Condition and undertaking register</h2><p className="mt-1 text-xs text-slate-500">Deadlines shown are the values recorded against each obligation; check the source order before treating a date as regulatory.</p></div>
          {visibleObligations.length === 0 ? <Empty title="No obligations in the current scope" description="An obligation is created from a condition recorded by the competent authority after an authorised decision."/> : <div className="divide-y divide-slate-100">{visibleObligations.map((item) => <ObligationRow key={item.obligation_id} item={item} role={role} note={note} setNote={setNote} onAction={obligationAction} onUploadEvidence={beginObligationUpload}/>)}</div>}
        </section>
      ) : null}

      {section === 'renewals' ? (
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold text-slate-900">Document validity register</h2>
                <p className="mt-1 text-xs text-slate-500">Each record points to a specific clean-scanned document version. Declared dates remain pending until an authorised officer verifies them.</p>
              </div>
              <Badge variant="secondary">{validityRecords.length} records</Badge>
            </div>
            {selected && role === 'INSTITUTION_USER' ? (
              <div className="mt-4 grid gap-3 rounded-lg bg-slate-50 p-3 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-700">Document type</label>
                  <select value={validityType} onChange={(event) => setValidityType(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm">
                    <option value="LEASE_DOCUMENT">Lease document</option>
                    <option value="BUILDING_DOCUMENT">Building / occupancy document</option>
                    <option value="FIRE_SAFETY">Fire safety certificate</option>
                    <option value="OTHER_PRESCRIBED_DOCUMENT">Other prescribed document</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-700">Issuing authority / lessor</label>
                  <input value={validityIssuer} onChange={(event) => setValidityIssuer(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" placeholder="Issuer or lessor name"/>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-700">Valid from</label>
                  <input type="date" value={validFrom} onChange={(event) => setValidFrom(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"/>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-700">Valid until</label>
                  <input type="date" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"/>
                </div>
                <div className="flex items-center justify-between gap-3 md:col-span-2">
                  <p className="text-xs text-slate-500">Select an application with a matching supporting-document slot, then upload the actual file.</p>
                  <Button size="sm" disabled={busy || !validityIssuer.trim() || !validUntil} onClick={beginValidityUpload}>Upload and submit</Button>
                </div>
              </div>
            ) : selected && canConfirmDocument ? (
              <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">Review records below. Open the linked application from the case queue to inspect its document checklist and audit timeline.</div>
            ) : !selected ? (
              <p className="mt-3 text-sm text-slate-500">Choose an application from the queue to submit or review its validity records.</p>
            ) : null}
          </section>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 p-4">
              <h3 className="font-semibold text-slate-900">Submitted validity records</h3>
              <p className="mt-1 text-xs text-slate-500">Expired is calculated from the recorded valid-until date. It is not a separate regulatory finding.</p>
            </div>
            {validityRecords.filter((record) => !selected || record.workflow_case_id === selected.workflow_case_id).length === 0 ? (
              <Empty title="No validity records yet" description="Upload a document version and submit its issuer and validity dates from an application that has a matching supporting-document slot."/>
            ) : (
              <div className="divide-y divide-slate-100">
                {validityRecords.filter((record) => !selected || record.workflow_case_id === selected.workflow_case_id).map((record) => (
                  <div key={record.document_validity_id} className="p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-semibold text-sm text-slate-900">{label(record.document_type)} · {record.issuer}</div>
                        <p className="mt-1 text-xs text-slate-500 break-all">{record.document_reference}</p>
                        <p className="mt-1 text-xs text-slate-500">Valid {date(record.valid_from)} to {date(record.valid_until)} · {isOverdue(record.valid_until + 'T23:59:59') ? 'Expired' : 'Within recorded validity'}</p>
                        {record.replacement_of_id && <p className="mt-1 text-xs text-indigo-700">Replacement of an earlier version</p>}
                        {record.verification_note && <p className="mt-1 text-xs text-slate-500">Review note: {record.verification_note}</p>}
                      </div>
                      <Status value={record.verification_status}/>
                    </div>
                    {canConfirmDocument && ['PENDING_VERIFICATION', 'RETURNED', 'DISPUTED'].includes(record.verification_status) && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button size="sm" disabled={busy || note.trim().length < 5} onClick={async () => { try { await workflowApi.reviewDocumentValidity(record.document_validity_id, 'VERIFY', note.trim()); setNote(''); await refresh(); toast.success('Document validity verified.'); } catch (err) { toast.error(err instanceof Error ? err.message : 'Verification was not accepted.'); } }}>Verify dates</Button>
                        <Button size="sm" variant="outline" disabled={busy || note.trim().length < 5} onClick={async () => { try { await workflowApi.reviewDocumentValidity(record.document_validity_id, 'RETURN', note.trim()); setNote(''); await refresh(); toast.success('Validity record returned with the review reason.'); } catch (err) { toast.error(err instanceof Error ? err.message : 'Return was not accepted.'); } }}>Return for correction</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}

      {showCaseQueue ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(340px,0.82fr)_minmax(0,1.18fr)]">
          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 p-4">
              <div className="flex items-center justify-between gap-2"><h2 className="font-semibold text-slate-900">{section === 'evc' ? 'EVC eligible / active cases' : section === 'decisions' ? 'Awaiting authority' : section === 'escalations' ? 'Overdue application stages' : section === 'assigned' ? 'Assigned proceedings' : 'Applications in scope'}</h2><Badge variant="secondary">{filteredCaseList.length}</Badge></div>
              <div className="relative mt-3"><Search className="absolute left-3 top-2.5 size-4 text-slate-400"/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search application number, institution or status" aria-label="Search applications" className="h-9 w-full rounded-lg border border-slate-200 pl-9 pr-3 text-sm outline-none focus:border-indigo-400"/></div>
              <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Filter applications">
                <Button size="xs" variant={caseQuickFilter === 'ALL' ? 'secondary' : 'outline'} onClick={() => setCaseQuickFilter('ALL')}>All ({caseList.length})</Button>
                <Button size="xs" variant={caseQuickFilter === 'DUE_SOON' ? 'secondary' : 'outline'} onClick={() => setCaseQuickFilter('DUE_SOON')}>Due in 7 days ({dueSoonQueueCount})</Button>
                <Button size="xs" variant={caseQuickFilter === 'OVERDUE' ? 'secondary' : 'outline'} onClick={() => setCaseQuickFilter('OVERDUE')}>Overdue ({overdueQueueCount})</Button>
                {workspace === 'institution' && <Button size="xs" variant={caseQuickFilter === 'MY_ACTIONS' ? 'secondary' : 'outline'} onClick={() => setCaseQuickFilter('MY_ACTIONS')}>Needs your response</Button>}
                {workspace === 'lead' && <Button size="xs" variant={caseQuickFilter === 'UNASSIGNED' ? 'secondary' : 'outline'} onClick={() => setCaseQuickFilter('UNASSIGNED')}>Unassigned</Button>}
                {(search || caseQuickFilter !== 'ALL') && <Button size="xs" variant="ghost" onClick={() => { setSearch(''); setCaseQuickFilter('ALL'); }}>Clear filters</Button>}
              </div>
            </div>
            {filteredCaseList.length === 0 ? <Empty title="No applications match these filters" description="Try another filter or clear your search to see the rest of your applications."/> : <div className="max-h-[760px] divide-y divide-slate-100 overflow-auto">{filteredCaseList.map((item) => <button key={item.workflow_case_id} type="button" onClick={() => void openCase(item)} className={'block w-full px-4 py-3 text-left transition hover:bg-slate-50 ' + (selected?.workflow_case_id === item.workflow_case_id ? 'bg-indigo-50/70' : '')}><div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold text-slate-900">{item.application_number}</span><Status value={item.current_stage}/></div><div className="mt-1 text-xs text-slate-600">{item.institution_name}</div><div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-slate-400"><span>{label(item.process_type)}</span><span>AY {item.academic_year}</span><span>Due: {date(item.due_at)}</span></div>{workspace !== 'institution' && <div className="mt-1 text-[11px] text-slate-500">Assigned role: {label(item.assigned_role_code)}</div>}
                  {workspace === 'lead' && item.review_team_name && <div className="mt-1 text-[11px] text-indigo-700">{item.review_team_name}</div>}</button>)}</div>}
          </section>

          <section className="space-y-4">
            {selected ? (
              <>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">{workspace === 'institution' ? 'Application details' : workspace === 'committee' ? 'Proceeding details' : 'Case details'}</div><h2 className="mt-1 text-lg font-bold text-slate-900">{selected.application_number}</h2><p className="text-sm text-slate-600">{selected.institution_name} · {label(selected.process_type)}</p></div><Status value={selected.current_stage}/></div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs"><div className="rounded-lg bg-slate-50 p-3"><span className="text-slate-500">Application type</span><div className="mt-1 font-semibold text-slate-800">{label(selected.process_type)}</div></div><div className="rounded-lg bg-slate-50 p-3"><span className="text-slate-500">Academic year</span><div className="mt-1 font-semibold text-slate-800">{selected.academic_year}</div></div></div>
                  {selected.route_snapshot.route_status === 'MANUAL_CONFIRMATION_REQUIRED' && <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">This application type needs an approved processing path before it can move forward. A policy officer must confirm the next steps.</div>}
                  {selected.route_snapshot.requires_committee === null && selected.route_snapshot.requires_evc === true && <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">An EVC visit is required, but any further committee step still needs confirmation. The application will be held until the correct next step is confirmed.</div>}
                  {workspace === 'institution' ? (
                    <div className="mt-4 grid gap-2 sm:grid-cols-2 text-xs">
                      <div><span className="text-slate-500">Last updated</span><p className="mt-0.5 font-medium text-slate-800">{new Date(selected.updated_at).toLocaleString()}</p></div>
                      <div><span className="text-slate-500">Next due date</span><p className={'mt-0.5 font-medium ' + (isOverdue(selected.due_at) ? 'text-red-700' : 'text-slate-800')}>{date(selected.due_at)}</p></div>
                    </div>
                  ) : (
                    <div className="mt-4 grid gap-2 sm:grid-cols-3 text-xs">
                      <div><span className="text-slate-500">Stage entered</span><p className="mt-0.5 font-medium text-slate-800">{new Date(selected.stage_entered_at).toLocaleString()}</p></div>
                      <div><span className="text-slate-500">Due date</span><p className={'mt-0.5 font-medium ' + (isOverdue(selected.due_at) ? 'text-red-700' : 'text-slate-800')}>{date(selected.due_at)}</p></div>
                      <div><span className="text-slate-500">Assigned role</span><p className="mt-0.5 font-medium text-slate-800">{label(selected.assigned_role_code)}</p></div>
                    </div>
                  )}
                  <div className="mt-4"><label className="mb-1.5 block text-xs font-semibold text-slate-700">{workspace === 'institution' ? 'Submission note' : 'Reason for this action'}</label><textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} placeholder={workspace === 'institution' ? 'Add a note for the processing team...' : 'Explain the action or observation...'} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"/></div>
                  <div className="mt-3 flex flex-wrap gap-2">{allowedTransitions(selected).map((target) => <Button key={target} size="sm" disabled={busy || note.trim().length < 8} onClick={() => void transition(target)}>{actionLabel(target)}</Button>)}</div>
                  {workspace === 'institution' && ['DRAFT', 'CLARIFICATION_REQUESTED'].includes(selected.current_stage) && <div className="mt-3 flex flex-wrap gap-3 text-sm"><Link className="text-indigo-700 underline" to="/institution/overview">Open current application checklist</Link><Link className="text-indigo-700 underline" to="/institution/rectification">Open clarification queue</Link><Link className="text-indigo-700 underline" to="/institution/documents">Review document validity and renewals</Link></div>}
                </div>

                {pendingEvc && (role === 'EVC_COORDINATOR' || role === 'REGIONAL_OFFICER' || role === 'LEAD_AUDITOR') ? <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Record EVC schedule</h3><p className="mt-1 text-xs text-slate-500">This records administrative scheduling metadata; it does not constitute official committee appointment.</p><div className="mt-3 grid gap-2 sm:grid-cols-2"><div><label className="mb-1 block text-xs font-medium">Proposed visit date</label><input type="date" value={evcDate} onChange={(event) => setEvcDate(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm"/></div><div><label className="mb-1 block text-xs font-medium">Visit mode</label><select value={evcMode} onChange={(event) => setEvcMode(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm"><option>PHYSICAL</option><option>ONLINE</option><option>HYBRID</option></select></div><div className="sm:col-span-2"><label className="mb-1 block text-xs font-medium">Location / meeting details</label><input value={evcLocation} onChange={(event) => setEvcLocation(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm" placeholder="Location or approved meeting details"/></div></div><Button className="mt-3" size="sm" disabled={busy || !evcDate || !evcLocation.trim() || note.trim().length < 8} onClick={async () => { const saved = await recordEvent('EVC_VISIT_SCHEDULED', note, { visit_date: evcDate, visit_mode: evcMode, location: evcLocation.trim(), schedule_status: 'PROPOSED', coordination_only: true }); if (saved) await transition('EVC_SCHEDULED', 'EVC schedule recorded for ' + evcDate + '. ' + note); }}>Save schedule and move to scheduled</Button></div> : null}

                {pendingEvcReport && (role === 'EVC_MEMBER' || role === 'EVC_COORDINATOR') ? <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Visit completion and report</h3><p className="mt-1 text-xs text-slate-500">A completed visit and a received report are separate facts; record the report reference before completing this workflow stage.</p><input value={reportReference} onChange={(event) => setReportReference(event.target.value)} className="mt-3 h-9 w-full rounded-lg border px-3 text-sm" placeholder="Visit report reference / document ID"/><Button className="mt-3" size="sm" disabled={busy || !reportReference.trim() || note.trim().length < 8} onClick={async () => { const saved = await recordEvent('EVC_REPORT_RECORDED', note, { report_reference: reportReference.trim(), report_status: 'RECEIVED' }); if (saved) await transition('EVC_COMPLETED', 'EVC report recorded: ' + reportReference.trim() + '. ' + note); }}>Record report and complete EVC stage</Button></div> : null}

                {pendingProceeding && role === 'COMMITTEE_SECRETARIAT' ? <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Proceeding record</h3><div className="mt-3"><label className="mb-1 block text-xs font-medium">Proceeding type</label><select value={proceedingType} onChange={(event) => setProceedingType(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm"><option value="SHC">Standing Hearing Committee (SHC)</option><option value="SAC">Standing Appellate Committee (SAC)</option><option value="OTHER_AUTHORISED_PROCEEDING">Other authorised proceeding</option></select></div><div className="mt-3 flex flex-wrap gap-2">
                    {!selected.events.some((event) => event.event_type === 'COMMITTEE_CONVENED') ? (
                      <Button size="sm" disabled={busy || note.trim().length < 8} onClick={() => void recordEvent('COMMITTEE_CONVENED', note, { proceeding_type: proceedingType, record_status: 'CONVENED' })}>Record meeting opened</Button>
                    ) : (
                      <Button size="sm" disabled={busy || note.trim().length < 8} onClick={async () => { const saved = await recordEvent('COMMITTEE_MINUTES_RECORDED', note, { proceeding_type: proceedingType, minutes_reference: reportReference || null, outcome_type: 'OBSERVATION_OR_RECOMMENDATION' }); if (saved) await transition('AWAITING_AUTHORITY', 'Proceeding record completed; committee recommendation is recorded, not a statutory outcome. ' + note); }}>Save minutes and send for decision</Button>
                    )}
                  </div><p className="mt-2 text-xs text-slate-500">SAC and SHC remain distinct. A committee recommendation is not automatically the statutory decision.</p></div> : null}

                {role === 'COMPETENT_AUTHORITY' && selected.current_stage === 'AWAITING_AUTHORITY' ? <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><Gavel className="size-4 text-indigo-600"/><h3 className="font-semibold text-slate-900">Competent authority decision</h3></div><p className="mt-1 text-xs text-slate-500">Only this explicitly authorised role can record the statutory outcome.</p><div className="mt-3 grid gap-2 sm:grid-cols-2"><div><label className="mb-1 block text-xs font-medium">Outcome</label><select value={decisionOutcome} onChange={(event) => setDecisionOutcome(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm"><option value="APPROVED">Approved</option><option value="APPROVED_WITH_CONDITIONS">Approved with conditions</option><option value="REJECTED">Rejected</option><option value="ON_HOLD">On hold</option></select></div><div><label className="mb-1 block text-xs font-medium">Decision date</label><input type="date" value={decisionDate} onChange={(event) => setDecisionDate(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm"/></div><div className="sm:col-span-2"><label className="mb-1 block text-xs font-medium">Official order / reference</label><input value={orderReference} onChange={(event) => setOrderReference(event.target.value)} className="h-9 w-full rounded-lg border px-3 text-sm" placeholder="Enter authorised order reference"/></div></div><Button className="mt-3" size="sm" disabled={busy || note.trim().length < 8 || orderReference.trim().length < 3} onClick={() => void createDecision()}>Record authorised decision</Button></div> : null}

                {role === 'COMPETENT_AUTHORITY' && selected.current_stage === 'APPROVED_WITH_CONDITIONS' ? <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Register a decision condition</h3><div className="mt-3 grid gap-2"><input value={conditionTitle} onChange={(event) => setConditionTitle(event.target.value)} className="h-9 rounded-lg border px-3 text-sm" placeholder="Condition title"/><textarea value={conditionDescription} onChange={(event) => setConditionDescription(event.target.value)} rows={2} className="rounded-lg border px-3 py-2 text-sm" placeholder="Exact condition and required institutional action"/><input value={conditionSource} onChange={(event) => setConditionSource(event.target.value)} className="h-9 rounded-lg border px-3 text-sm" placeholder="Official order / source clause reference"/><input type="date" value={conditionDue} onChange={(event) => setConditionDue(event.target.value)} className="h-9 rounded-lg border px-3 text-sm"/><Button size="sm" disabled={busy || !conditionTitle.trim() || !conditionDescription.trim() || !conditionSource.trim() || !conditionDue} onClick={() => void registerCondition()}>Add obligation</Button></div></div> : null}

                {section === 'escalations' && ['REGIONAL_OFFICER', 'BUREAU_SUPERVISOR', 'LEAD_AUDITOR'].includes(role) && isOverdue(selected.due_at) && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><h3 className="font-semibold text-amber-950">Overdue stage review</h3><p className="mt-1 text-xs text-amber-900">This is a due-date-based review signal, not an automatic penalty or statutory finding.</p><div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={busy || note.trim().length < 8} onClick={() => void recordEvent('ESCALATION_ACKNOWLEDGED', note, { trigger_type: 'STAGE_OVERDUE', due_at: selected.due_at, escalation_level: 'SUPERVISORY_REVIEW' })}>Acknowledge escalation</Button><Button size="sm" disabled={busy || note.trim().length < 8} onClick={() => void recordEvent('ESCALATION_RESOLVED', note, { trigger_type: 'STAGE_OVERDUE', due_at: selected.due_at, resolution: 'MANUAL_SUPERVISORY_ACTION' })}>Record resolution</Button></div></div>}

                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between"><h3 className="font-semibold text-slate-900">{workspace === 'institution' ? 'Required documents' : 'Evidence checklist'}</h3><Badge variant="secondary">{selected.requirements.length} items</Badge></div>
                  {selected.requirements.length === 0 ? <p className="mt-3 text-sm text-slate-500">No document requirements are linked to this application.</p> : <div className="mt-3 divide-y divide-slate-100">{selected.requirements.map((item) => <div key={item.application_requirement_id} className="py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium text-slate-800">{workspace === 'institution' ? item.title : item.item_code + ' · ' + item.title}</span>
                      <div className="flex flex-wrap items-center gap-2">
                        <Status value={item.status}/>
                        {workspace === 'institution' && item.applicability_status === 'APPLICABLE' && item.status !== 'SATISFIED' && (
                          <Button size="xs" variant="outline" disabled={busy} onClick={() => {
                            setUploadPurpose(null);
                            setPendingObligationId(null);
                            setUploadRequirement(item);
                            setUploadOpen(true);
                          }}>Upload document</Button>
                        )}
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{label(item.applicability_status)}{item.determination_reason ? ' · ' + item.determination_reason : ''}</p>
                    {workspace === 'institution' && item.applicability_status === 'PENDING_DETERMINATION' && <p className="mt-1 text-[11px] text-amber-700">This requirement will become available for upload after its applicability is confirmed.</p>}
                  </div>)}</div>}
                </div>

                {selectedObligations.length > 0 ? <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Linked conditions and obligations</h3><div className="mt-3 divide-y divide-slate-100">{selectedObligations.map((item) => <div key={item.obligation_id} className="py-2"><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-slate-800">{item.title}</span><Status value={item.status}/></div><p className="mt-1 text-xs text-slate-600">{item.description}</p><p className="mt-1 text-xs text-slate-400">Due {date(item.due_at)} · Source: {item.source_condition}</p></div>)}</div></div> : null}

                <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between"><h3 className="font-semibold text-slate-900">{workspace === 'institution' ? 'Application updates' : 'Application activity'}</h3><Badge variant="secondary">{selected.events.length} events</Badge></div>{selected.events.length === 0 ? <p className="mt-3 text-sm text-slate-500">No workflow events have been recorded yet.</p> : <div className="mt-3 space-y-3">{selected.events.map((event) => <div key={event.workflow_event_id} className="flex gap-3 text-xs"><div className="mt-1 size-2 rounded-full bg-indigo-500"/><div className="min-w-0 flex-1"><div className="flex flex-wrap justify-between gap-2"><span className="font-semibold text-slate-800">{label(event.event_type)}</span><span className="text-slate-400">{new Date(event.occurred_at).toLocaleString()}</span></div><p className="mt-1 text-slate-600">{event.summary}</p></div></div>)}</div>}</div>
              </>
            ) : <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center"><FileText className="mx-auto size-8 text-slate-300"/><p className="mt-2 text-sm font-semibold text-slate-700">Select a case to open its dossier</p><p className="mt-1 text-xs text-slate-500">Actions appear only when the selected case state and authenticated role permit them.</p></div>}
          </section>
        </div>
      ) : null}
      <DocumentUploadModal
        open={uploadOpen}
        onOpenChange={(open) => {
          setUploadOpen(open);
          if (!open) {
            setUploadRequirement(null);
            setUploadPurpose(null);
          }
        }}
        requirement={uploadRequirement}
        onUploadSuccess={(response) => void handleDocumentUploaded(response)}
      />
    </div>
  );
}

function PageHeading({ title, description, onRefresh, busy, onExport, showRefresh = true }: { title: string; description: string; onRefresh: () => void; busy: boolean; onExport?: () => void; showRefresh?: boolean }) {
  return <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4"><div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700"><Workflow className="size-4"/> AIC-Flow operational workspace</div><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">{title}</h1><p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p></div><div className="flex gap-2">{showRefresh && <Button size="sm" variant="outline" disabled={busy} onClick={onRefresh}><RefreshCw className={'mr-1.5 size-3.5 ' + (busy ? 'animate-spin' : '')}/>Refresh</Button>}{onExport && <Button size="sm" onClick={onExport}><Download className="mr-1.5 size-3.5"/>Export CSV</Button>}</div></div>;
}

function SyntheticNotice() {
  return <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-900"><span className="font-semibold">DEMO ENVIRONMENT</span><span>Sample applications are fictional. This workspace does not connect to live AICTE or external systems.</span></div>;
}

function Metric({ label: title, value, icon: Icon }: { label: string; value: number; icon: typeof Activity }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between gap-2"><span className="text-xs font-medium text-slate-500">{title}</span><Icon className="size-4 text-indigo-600"/></div><div className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{value}</div></div>;
}

function Status({ value }: { value: string }) {
  const tone = ['OVERDUE', 'REJECTED', 'EXPIRED', 'DEFICIENT', 'ON_HOLD'].includes(value) ? 'border-red-200 bg-red-50 text-red-700'
    : ['VERIFIED', 'CLOSED', 'APPROVED', 'COMPLETED'].includes(value) ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : ['CLARIFICATION_REQUESTED', 'RETURNED', 'AWAITING_AUTHORITY', 'EVIDENCE_SUBMITTED'].includes(value) ? 'border-amber-200 bg-amber-50 text-amber-800'
        : 'border-slate-200 bg-slate-50 text-slate-700';
  return <Badge variant="outline" className={'max-w-[220px] truncate ' + tone}>{label(value)}</Badge>;
}

function Empty({ title, description }: { title: string; description: string }) {
  return <div className="p-8 text-center"><FileText className="mx-auto size-8 text-slate-300"/><p className="mt-2 text-sm font-semibold text-slate-700">{title}</p><p className="mx-auto mt-1 max-w-md text-xs text-slate-500">{description}</p></div>;
}

function ObligationRow({ item, role, note, setNote, onAction, onUploadEvidence }: {
  item: ComplianceObligation;
  role: string;
  note: string;
  setNote: (value: string) => void;
  onAction: (id: string, action: string, reference?: string) => void;
  onUploadEvidence: (item: ComplianceObligation) => void;
}) {
  const institutionCanSubmit = role === 'INSTITUTION_USER' && ['OPEN', 'RETURNED'].includes(item.status);
  const verifierCanReview = ['SCRUTINY_OFFICER', 'AUDITOR'].includes(role) && item.status === 'EVIDENCE_SUBMITTED';
  const verifierCanVerify = ['SCRUTINY_OFFICER', 'AUDITOR', 'BUREAU_SUPERVISOR', 'LEAD_AUDITOR'].includes(role) && ['EVIDENCE_SUBMITTED', 'UNDER_VERIFICATION'].includes(item.status);
  const supervisorCanClose = ['BUREAU_SUPERVISOR', 'REGIONAL_OFFICER', 'LEAD_AUDITOR'].includes(role) && item.status === 'VERIFIED';
  return (
    <div className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-semibold text-sm text-slate-900">{item.title}</div>
        <Status value={item.status}/>
      </div>
      <p className="mt-1 text-sm text-slate-600">{item.description}</p>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>Due: {date(item.due_at)}</span>
        <span>Source: {item.source_condition}</span>
      </div>
      {item.evidence_reference && <p className="mt-2 text-xs text-indigo-700 break-all">Evidence submission: {item.evidence_reference}</p>}
      {item.verification_note && <p className="mt-2 text-xs text-slate-500">Last review note: {item.verification_note}</p>}
      {(institutionCanSubmit || verifierCanReview || verifierCanVerify || supervisorCanClose) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Reason or review note"
            className="h-9 min-w-[180px] flex-1 rounded-lg border border-slate-200 px-3 text-xs"
            aria-label="Obligation action note"
          />
          {institutionCanSubmit && <Button size="sm" disabled={note.trim().length < 5} onClick={() => onUploadEvidence(item)}>Upload evidence</Button>}
          {verifierCanReview && <Button size="sm" variant="outline" disabled={note.trim().length < 5} onClick={() => onAction(item.obligation_id, 'START_VERIFICATION')}>Start verification</Button>}
          {verifierCanVerify && <>
            <Button size="sm" disabled={note.trim().length < 5} onClick={() => onAction(item.obligation_id, 'VERIFY')}>Verify evidence</Button>
            <Button size="sm" variant="outline" disabled={note.trim().length < 5} onClick={() => onAction(item.obligation_id, 'RETURN')}>Return for correction</Button>
          </>}
          {supervisorCanClose && <Button size="sm" disabled={note.trim().length < 5} onClick={() => onAction(item.obligation_id, 'CLOSE')}>Close verified obligation</Button>}
        </div>
      )}
    </div>
  );
}
