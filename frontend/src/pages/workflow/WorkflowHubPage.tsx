import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bell, CalendarClock, Clock3, FileCheck, FileText, Gavel, MapPin, RefreshCw, Search, ShieldCheck, Video, Workflow } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { workflowApi, type WorkflowCase, type WorkflowDetail, type WorkflowNotification } from '@/features/workflow/api';
import { DocumentUploadModal } from '@/components/documents/DocumentUploadModal';
import { documentsApi } from '@/features/documents/api';
import type { ApplicationRequirementItem } from '@/types/application';
import type { DocumentUploadResponse } from '@/types/document';

const stageLabel = (value: string) => value === 'COMMITTEE_PROCEEDINGS' ? 'Standing Hearing Committee (SHC)' : value === 'AWAITING_AUTHORITY' ? 'Executive Committee Decision' : value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());
const dateLabel = (value: string | null) => value ? new Date(value).toLocaleDateString() : 'Not set';
const dateTimeLabel = (value: string | null) => value ? new Date(value).toLocaleString() : 'Not set';
const stageAgeDays = (value: string) => Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 86_400_000));
const ageLabel = (value: string) => {
  const days = stageAgeDays(value);
  return days === 0 ? 'Entered today' : `${days} day${days === 1 ? '' : 's'} in stage`;
};

const ROLE_GUIDANCE: Record<string, { title: string; description: string }> = {
  INSTITUTION_USER: { title: 'Institution representative', description: 'Prepare applications, submit required documents, respond to clarifications and provide evidence against approval conditions.' },
  INTAKE_OFFICER: { title: 'Intake and registry', description: 'Check filing completeness, register the case, confirm its routing basis and direct it to the appropriate processing role.' },
  SCRUTINY_OFFICER: { title: 'Scrutiny officer', description: 'Examine application requirements, record observations, request clarifications and complete re-scrutiny of revised submissions.' },
  AUDITOR: { title: 'Processing officer', description: 'Review assigned application evidence, record scrutiny observations and progress authorised case actions.' },
  REGIONAL_OFFICER: { title: 'Regional coordination', description: 'Coordinate regional processing, monitor ageing and workload, and supervise assigned case hand-offs.' },
  EVC_COORDINATOR: { title: 'EVC coordination', description: 'Coordinate visit logistics, record the schedule and ensure the visit report is recorded against the case.' },
  EVC_MEMBER: { title: 'EVC assigned participant', description: 'Record the visit outcome and supporting report for the assigned case.' },
  COMMITTEE_SECRETARIAT: { title: 'Standing Hearing Committee secretariat', description: 'Maintain the SHC hearing schedule, institution appearance record and recommendation for Executive Committee consideration.' },
  SAC_SECRETARIAT: { title: 'Standing Appellate Committee secretariat', description: 'Coordinate appeal hearings, record institution appearances and present the SAC recommendation to the Council.' },
  COUNCIL_SECRETARIAT: { title: 'Council secretariat', description: 'Record the Council decision following consideration of the Standing Appellate Committee recommendation.' },
  BUREAU_SUPERVISOR: { title: 'Bureau supervision', description: 'Oversee case pendency, review escalations and verify closure of post-decision obligations.' },
  LEAD_AUDITOR: { title: 'Senior regulatory oversight', description: 'Review escalated cases, supervise processing and monitor compliance resolution.' },
  COMPETENT_AUTHORITY: { title: 'Competent authority', description: 'Review the completed case record and record the authorised statutory outcome and any binding conditions.' },
  REGULATORY_POLICY_PUBLISHER: { title: 'Regulatory policy administration', description: 'Review the category-specific route and regulatory-version baseline assigned to your policy-governance account.' },
  ADMIN: { title: 'Platform administration', description: 'View your platform-administration role and the access scope assigned to your account.' },
};

export default function WorkflowHubPage() {
  const auth = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const role = auth.activeContext?.role_code || '';
  const teamId = auth.activeContext?.review_team_id || '';
  const [cases, setCases] = useState<WorkflowCase[]>([]);
  const [selected, setSelected] = useState<WorkflowDetail | null>(null);
  const [notifications, setNotifications] = useState<WorkflowNotification[]>([]);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [queueQuery, setQueueQuery] = useState('');
  const [queueFilter, setQueueFilter] = useState<'ALL' | 'ACTION' | 'OPEN'>('ALL');
  const [conditionTitle, setConditionTitle] = useState('');
  const [conditionDescription, setConditionDescription] = useState('');
  const [conditionSource, setConditionSource] = useState('');
  const [conditionDue, setConditionDue] = useState('');
  const [evidenceReference, setEvidenceReference] = useState('');
  const [evcMode, setEvcMode] = useState<'ONLINE' | 'OFFLINE'>('ONLINE');
  const [evcStartAt, setEvcStartAt] = useState('');
  const [evcEndAt, setEvcEndAt] = useState('');
  const [evcVenue, setEvcVenue] = useState('');
  const [evcOfficialReference, setEvcOfficialReference] = useState('');
  const [evcContactName, setEvcContactName] = useState('');
  const [evcContactEmail, setEvcContactEmail] = useState('');
  const [evcCoordinationNote, setEvcCoordinationNote] = useState('');
  const [evcReportReference, setEvcReportReference] = useState('');
  const [evcReportSummary, setEvcReportSummary] = useState('');
  const [evcReportOutcome, setEvcReportOutcome] = useState<'NO_DEFICIENCY_RECORDED' | 'DEFICIENCIES_OBSERVED' | 'FOLLOW_UP_REQUIRED' | 'INCONCLUSIVE'>('INCONCLUSIVE');
  const [evcReportNote, setEvcReportNote] = useState('');
  const [evcCancelReason, setEvcCancelReason] = useState('');
  const [shcHearingMode, setShcHearingMode] = useState<'ONLINE' | 'IN_PERSON'>('ONLINE');
  const [shcHearingAt, setShcHearingAt] = useState('');
  const [shcHearingDetails, setShcHearingDetails] = useState('');
  const [shcNoticeReference, setShcNoticeReference] = useState('');
  const [shcOfficialReference, setShcOfficialReference] = useState('');
  const [shcSubmissionReference, setShcSubmissionReference] = useState('');
  const [shcSubmissionNote, setShcSubmissionNote] = useState('');
  const [shcRepOneName, setShcRepOneName] = useState('');
  const [shcRepOneDesignation, setShcRepOneDesignation] = useState('');
  const [shcRepTwoName, setShcRepTwoName] = useState('');
  const [shcRepTwoDesignation, setShcRepTwoDesignation] = useState('');
  const [shcHearingSummary, setShcHearingSummary] = useState('');
  const [shcHearingNote, setShcHearingNote] = useState('');
  const [shcRecommendationCode, setShcRecommendationCode] = useState<'COMPLIANCE_REVIEWED' | 'FURTHER_COMPLIANCE_REQUIRED' | 'DEFICIENCIES_REMAIN' | 'INCONCLUSIVE'>('INCONCLUSIVE');
  const [shcRecommendationText, setShcRecommendationText] = useState('');
  const [shcRecommendationReference, setShcRecommendationReference] = useState('');
  const [ecOutcome, setEcOutcome] = useState<'APPROVED' | 'APPROVED_WITH_CONDITIONS' | 'REJECTED'>('APPROVED_WITH_CONDITIONS');
  const [ecDecisionReference, setEcDecisionReference] = useState('');
  const [ecDecisionReasons, setEcDecisionReasons] = useState('');
  const [ecSpeakingOrderReference, setEcSpeakingOrderReference] = useState('');
  const [ecSpeakingOrderUploadedAt, setEcSpeakingOrderUploadedAt] = useState('');
  const [sacAppealReference, setSacAppealReference] = useState('');
  const [sacAppealGrounds, setSacAppealGrounds] = useState('');
  const [sacSupportingMaterialReference, setSacSupportingMaterialReference] = useState('');
  const [sacHearingMode, setSacHearingMode] = useState<'ONLINE' | 'IN_PERSON'>('ONLINE');
  const [sacHearingAt, setSacHearingAt] = useState('');
  const [sacHearingDetails, setSacHearingDetails] = useState('');
  const [sacOfficialScheduleReference, setSacOfficialScheduleReference] = useState('');
  const [sacBureauObservationReference, setSacBureauObservationReference] = useState('');
  const [sacBureauObservations, setSacBureauObservations] = useState('');
  const [sacRepOneName, setSacRepOneName] = useState('');
  const [sacRepOneDesignation, setSacRepOneDesignation] = useState('');
  const [sacRepOneIdReference, setSacRepOneIdReference] = useState('');
  const [sacRepOneIdSelfAttested, setSacRepOneIdSelfAttested] = useState(false);
  const [sacRepTwoName, setSacRepTwoName] = useState('');
  const [sacRepTwoDesignation, setSacRepTwoDesignation] = useState('');
  const [sacRepTwoIdReference, setSacRepTwoIdReference] = useState('');
  const [sacRepTwoIdSelfAttested, setSacRepTwoIdSelfAttested] = useState(false);
  const [sacHearingSummary, setSacHearingSummary] = useState('');
  const [sacRecommendationCode, setSacRecommendationCode] = useState<'RECOMMEND_TO_COUNCIL' | 'NOT_RECOMMEND_TO_COUNCIL' | 'FURTHER_REVIEW_REQUIRED'>('FURTHER_REVIEW_REQUIRED');
  const [sacRecommendationText, setSacRecommendationText] = useState('');
  const [sacRecommendationReference, setSacRecommendationReference] = useState('');
  const [councilOutcome, setCouncilOutcome] = useState<'UPHOLD_EXECUTIVE_COMMITTEE' | 'SET_ASIDE_EXECUTIVE_COMMITTEE' | 'MODIFY_EXECUTIVE_COMMITTEE' | 'REMAND_FOR_RECONSIDERATION'>('UPHOLD_EXECUTIVE_COMMITTEE');
  const [councilDecisionReference, setCouncilDecisionReference] = useState('');
  const [councilDecisionText, setCouncilDecisionText] = useState('');
  const [councilDecisionUploadedAt, setCouncilDecisionUploadedAt] = useState('');
  const [uploadRequirement, setUploadRequirement] = useState<ApplicationRequirementItem | null>(null);
  const [uploadObligationId, setUploadObligationId] = useState<string | null>(null);
  const [obligationEvidenceRequirementIds, setObligationEvidenceRequirementIds] = useState<Record<string, string>>({});
  const [uploadOpen, setUploadOpen] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const [caseRows, notificationRows] = await Promise.all([workflowApi.cases(), workflowApi.notifications()]);
      setCases(caseRows);
      setNotifications(notificationRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load approval workflow records.');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (role === 'ADMIN' || role === 'REGULATORY_POLICY_PUBLISHER') return;
    void refresh();
  }, [refresh, role]);

  const openCase = useCallback(async (row: WorkflowCase) => {
    try { setSelected(await workflowApi.detail(row.workflow_case_id)); }
    catch (err) { toast.error(err instanceof Error ? err.message : 'Unable to open case.'); }
  }, []);

  useEffect(() => {
    const applicationId = searchParams.get('application');
    if (!applicationId) return;
    const matchingCase = cases.find((item) => item.application_id === applicationId);
    if (matchingCase) {
      void openCase(matchingCase);
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        next.delete('application');
        return next;
      }, { replace: true });
    }
  }, [cases, openCase, searchParams, setSearchParams]);

  const visibleCases = useMemo(() => {
    const query = queueQuery.trim().toLowerCase();
    return cases.filter((item) => {
      const matchesQuery = !query || [
        item.application_number, item.institution_name, item.process_type,
        item.current_stage, item.route_code,
      ].some((value) => value.toLowerCase().includes(query));
      const matchesFilter = queueFilter === 'ALL'
        || (queueFilter === 'OPEN' && item.current_stage !== 'CLOSED')
        || (queueFilter === 'ACTION' && item.assigned_role_code === role
          && (!item.assigned_user_id || item.assigned_user_id === auth.user?.user_id));
      return matchesQuery && matchesFilter;
    });
  }, [cases, queueQuery, queueFilter, role, auth.user?.user_id]);

  const nextStages = useMemo(() => {
    if (!selected) return [] as string[];
    const stage = selected.current_stage;
    const route = selected.route_snapshot || {};
    const requiresEvc = route.requires_evc === true;
    const requiresScrutiny = route.requires_scrutiny === true;
    const requiresCommittee = route.requires_committee === true;
    if (role === 'INSTITUTION_USER') {
      if (stage === 'DRAFT') return ['SUBMITTED'];
      if (stage === 'CLARIFICATION_REQUESTED') return ['RESUBMITTED'];
    }
    if (['INTAKE_OFFICER', 'AUDITOR'].includes(role)) {
      if (stage === 'SUBMITTED') return ['INTAKE_REVIEW'];
      if (stage === 'RESUBMITTED' && !requiresScrutiny) return ['INTAKE_REVIEW'];
      if (stage === 'INTAKE_REVIEW') {
        const actions = ['CLARIFICATION_REQUESTED'];
        if (!requiresScrutiny) actions.push('AWAITING_AUTHORITY');
        if (requiresScrutiny && role === 'AUDITOR') actions.push('SCRUTINY');
        return actions;
      }
    }
    if (['SCRUTINY_OFFICER', 'AUDITOR'].includes(role)) {
      if ((stage === 'INTAKE_REVIEW' || stage === 'RESUBMITTED') && requiresScrutiny) return ['SCRUTINY'];
      if (stage === 'SCRUTINY') return ['CLARIFICATION_REQUESTED', requiresEvc ? 'EVC_COORDINATION' : 'AWAITING_AUTHORITY'];
    }
    if (['EVC_COORDINATOR', 'REGIONAL_OFFICER', 'LEAD_AUDITOR'].includes(role)) {
      if (stage === 'EVC_COORDINATION') return selected.evc_visit?.status === 'SCHEDULED' ? ['EVC_SCHEDULED'] : [];
      if (stage === 'EVC_SCHEDULED') return selected.evc_visit?.status === 'COMPLETED' ? ['EVC_COMPLETED'] : [];
      if (stage === 'EVC_COMPLETED' && requiresCommittee === false) return ['AWAITING_AUTHORITY'];
    }
    if (role === 'EVC_MEMBER' && stage === 'EVC_SCHEDULED' && selected.evc_visit?.status === 'COMPLETED') return ['EVC_COMPLETED'];
    if (role === 'COMMITTEE_SECRETARIAT') {
      if (stage === 'EVC_COMPLETED' && requiresCommittee) return ['COMMITTEE_PROCEEDINGS'];
      if (stage === 'COMMITTEE_PROCEEDINGS' && selected.shc_proceeding?.status === 'RECOMMENDATION_RECORDED') return ['AWAITING_AUTHORITY'];
    }
    if (role === 'COMPETENT_AUTHORITY' && stage === 'AWAITING_AUTHORITY') return ['ON_HOLD'];
    if (role === 'COMPETENT_AUTHORITY' && stage === 'APPROVED_WITH_CONDITIONS') return ['OBLIGATION_TRACKING'];
    if (['BUREAU_SUPERVISOR', 'REGIONAL_OFFICER', 'LEAD_AUDITOR'].includes(role) && ['APPROVED', 'REJECTED', 'OBLIGATION_TRACKING'].includes(stage)) return ['CLOSED'];
    if (['BUREAU_SUPERVISOR', 'REGIONAL_OFFICER', 'LEAD_AUDITOR'].includes(role) && stage === 'ON_HOLD') return [requiresScrutiny ? 'SCRUTINY' : 'INTAKE_REVIEW'];
    return [];
  }, [selected, role]);

  const transition = async (target: string) => {
    if (!selected || note.trim().length < 8) { toast.error('Enter a reason of at least 8 characters.'); return; }
    setBusy(true);
    try {
      const updated = await workflowApi.transition(selected.workflow_case_id, target, note.trim());
      setSelected(updated); setNote(''); await refresh();
      toast.success(`Case moved to ${stageLabel(target)}.`);
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Transition was not accepted.'); }
    finally { setBusy(false); }
  };

  const assignCase = async () => {
    if (!selected || !teamId || note.trim().length < 8) { toast.error('A team scope and assignment note are required.'); return; }
    setBusy(true);
    try {
      const updated = await workflowApi.assign(selected.workflow_case_id, teamId, note.trim());
      setSelected(updated); setNote(''); await refresh(); toast.success('Case assigned to your review team.');
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Assignment failed.'); }
    finally { setBusy(false); }
  };


  const scheduleEvc = async () => {
    if (!selected || !evcStartAt || evcVenue.trim().length < 5 || evcCoordinationNote.trim().length < 8) {
      toast.error('Enter a visit date and time, venue or meeting details, and a coordination note.');
      return;
    }
    const start = new Date(evcStartAt);
    const end = evcEndAt ? new Date(evcEndAt) : null;
    if (Number.isNaN(start.getTime()) || (end && (Number.isNaN(end.getTime()) || end <= start))) {
      toast.error('Check the visit date and time range.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.scheduleEvcVisit(selected.workflow_case_id, {
        visit_mode: evcMode,
        scheduled_start_at: start.toISOString(),
        scheduled_end_at: end ? end.toISOString() : null,
        venue_or_meeting_details: evcVenue.trim(),
        official_schedule_reference: evcOfficialReference.trim() || null,
        institution_contact_name: evcContactName.trim() || null,
        institution_contact_email: evcContactEmail.trim() || null,
        coordination_note: evcCoordinationNote.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      setEvcCoordinationNote('');
      await refresh();
      toast.success('EVC visit schedule saved.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not save the EVC visit schedule.');
    } finally {
      setBusy(false);
    }
  };

  const recordEvcReport = async () => {
    if (!selected?.evc_visit || evcReportReference.trim().length < 3 || evcReportSummary.trim().length < 10 || evcReportNote.trim().length < 8) {
      toast.error('Enter the report reference, visit observations and recording note.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordEvcReport(selected.evc_visit.evc_visit_id, {
        report_reference: evcReportReference.trim(),
        report_summary: evcReportSummary.trim(),
        report_outcome: evcReportOutcome,
        note: evcReportNote.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      setEvcReportReference('');
      setEvcReportSummary('');
      setEvcReportNote('');
      await refresh();
      toast.success('EVC report recorded in the case history.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the EVC report.');
    } finally {
      setBusy(false);
    }
  };

  const cancelEvc = async () => {
    if (!selected?.evc_visit || evcCancelReason.trim().length < 8) {
      toast.error('Enter a reason of at least 8 characters.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.cancelEvcVisit(selected.evc_visit.evc_visit_id, evcCancelReason.trim());
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      setEvcCancelReason('');
      await refresh();
      toast.success('EVC visit cancelled. A revised schedule can be recorded.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not cancel the EVC visit.');
    } finally {
      setBusy(false);
    }
  };


  const scheduleShc = async () => {
    if (!selected || !shcHearingAt || shcHearingDetails.trim().length < 5) {
      toast.error('Enter the hearing date and time and the hearing details.');
      return;
    }
    const hearingAt = new Date(shcHearingAt);
    if (Number.isNaN(hearingAt.getTime()) || hearingAt <= new Date()) {
      toast.error('The SHC hearing must be scheduled for a future date and time.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.scheduleShcHearing(selected.workflow_case_id, {
        hearing_mode: shcHearingMode,
        hearing_scheduled_at: hearingAt.toISOString(),
        hearing_details: shcHearingDetails.trim(),
        notice_reference: shcNoticeReference.trim() || null,
        official_schedule_reference: shcOfficialReference.trim() || null,
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('SHC hearing schedule recorded.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not schedule the SHC hearing.');
    } finally {
      setBusy(false);
    }
  };

  const submitShcCompliance = async () => {
    if (!selected?.shc_proceeding || shcSubmissionReference.trim().length < 5 || shcSubmissionNote.trim().length < 8) {
      toast.error('Enter the compliance submission reference and a note.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.submitShcCompliance(selected.shc_proceeding.shc_proceeding_id, {
        submission_reference: shcSubmissionReference.trim(),
        note: shcSubmissionNote.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      setShcSubmissionNote('');
      await refresh();
      toast.success('Compliance submission reference recorded.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the compliance submission.');
    } finally {
      setBusy(false);
    }
  };

  const recordShcHearing = async () => {
    if (!selected?.shc_proceeding ||
        shcRepOneName.trim().length < 2 || shcRepOneDesignation.trim().length < 2 ||
        shcRepTwoName.trim().length < 2 || shcRepTwoDesignation.trim().length < 2 ||
        shcHearingSummary.trim().length < 15 || shcHearingNote.trim().length < 8) {
      toast.error('Complete both institution representatives and the hearing record.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordShcHearing(selected.shc_proceeding.shc_proceeding_id, {
        representative_one_name: shcRepOneName.trim(),
        representative_one_designation: shcRepOneDesignation.trim(),
        representative_two_name: shcRepTwoName.trim(),
        representative_two_designation: shcRepTwoDesignation.trim(),
        hearing_summary: shcHearingSummary.trim(),
        note: shcHearingNote.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      setShcHearingNote('');
      await refresh();
      toast.success('SHC hearing record saved.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the SHC hearing.');
    } finally {
      setBusy(false);
    }
  };

  const recordShcRecommendation = async () => {
    if (!selected?.shc_proceeding || shcRecommendationText.trim().length < 15) {
      toast.error('Enter the SHC recommendation and supporting reasons.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordShcRecommendation(selected.shc_proceeding.shc_proceeding_id, {
        recommendation_code: shcRecommendationCode,
        recommendation_text: shcRecommendationText.trim(),
        recommendation_reference: shcRecommendationReference.trim() || null,
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('SHC recommendation recorded for Executive Committee consideration.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the SHC recommendation.');
    } finally {
      setBusy(false);
    }
  };

  const recordExecutiveDecision = async () => {
    if (!selected || ecDecisionReference.trim().length < 2 || ecDecisionReasons.trim().length < 15 || ecSpeakingOrderReference.trim().length < 2 || !ecSpeakingOrderUploadedAt) {
      toast.error('Complete the Executive Committee decision, reasons and Speaking Order details.');
      return;
    }
    const uploadedAt = new Date(ecSpeakingOrderUploadedAt);
    if (Number.isNaN(uploadedAt.getTime()) || uploadedAt > new Date()) {
      toast.error('Enter a valid Speaking Order upload time that is not in the future.');
      return;
    }
    setBusy(true);
    try {
      const updated = await workflowApi.recordExecutiveCommitteeDecision(selected.workflow_case_id, {
        outcome_code: ecOutcome,
        decision_reference: ecDecisionReference.trim(),
        decision_reasons: ecDecisionReasons.trim(),
        speaking_order_reference: ecSpeakingOrderReference.trim(),
        speaking_order_uploaded_at: uploadedAt.toISOString(),
      });
      setSelected(updated);
      await refresh();
      toast.success('Executive Committee decision recorded with its Speaking Order reference.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the Executive Committee decision.');
    } finally {
      setBusy(false);
    }
  };

  const fileSacAppeal = async () => {
    if (!selected || sacAppealGrounds.trim().length < 20 || sacSupportingMaterialReference.trim().length < 5) {
      toast.error('Enter the grounds of appeal and the supporting material reference.');
      return;
    }
    const deadline = selected.executive_committee_decision?.appeal_deadline_at;
    if (!deadline || Date.now() > new Date(deadline).getTime()) {
      toast.error('The appeal filing period shown on this decision has ended.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.fileSacAppeal(selected.workflow_case_id, {
        appeal_reference: sacAppealReference.trim() || null,
        appeal_grounds: sacAppealGrounds.trim(),
        supporting_material_reference: sacSupportingMaterialReference.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      setSacAppealGrounds('');
      setSacSupportingMaterialReference('');
      await refresh();
      toast.success('Appeal filed and linked to the Executive Committee decision.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not file the appeal.');
    } finally {
      setBusy(false);
    }
  };

  const scheduleSacHearing = async () => {
    if (!selected?.sac_appeal || !sacHearingAt || sacHearingDetails.trim().length < 5) {
      toast.error('Enter the SAC hearing date and time and hearing details.');
      return;
    }
    const scheduledAt = new Date(sacHearingAt);
    if (Number.isNaN(scheduledAt.getTime()) || scheduledAt <= new Date()) {
      toast.error('The SAC hearing must be scheduled for a future date and time.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.scheduleSacHearing(selected.sac_appeal.sac_appeal_id, {
        hearing_mode: sacHearingMode,
        hearing_scheduled_at: scheduledAt.toISOString(),
        hearing_details: sacHearingDetails.trim(),
        official_schedule_reference: sacOfficialScheduleReference.trim() || null,
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('SAC hearing schedule recorded.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not schedule the SAC hearing.');
    } finally {
      setBusy(false);
    }
  };

  const recordSacBureauObservations = async () => {
    if (!selected?.sac_appeal || sacBureauObservationReference.trim().length < 2 || sacBureauObservations.trim().length < 15) {
      toast.error('Enter the Regulation Bureau observation reference and observations.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordSacBureauObservations(selected.sac_appeal.sac_appeal_id, {
        observation_reference: sacBureauObservationReference.trim(),
        observations: sacBureauObservations.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('Regulation Bureau observations recorded for SAC.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record Regulation Bureau observations.');
    } finally {
      setBusy(false);
    }
  };

  const recordSacHearing = async () => {
    if (!selected?.sac_appeal ||
        sacRepOneName.trim().length < 2 || sacRepOneDesignation.trim().length < 2 || sacRepOneIdReference.trim().length < 3 ||
        sacRepTwoName.trim().length < 2 || sacRepTwoDesignation.trim().length < 2 || sacRepTwoIdReference.trim().length < 3 ||
        !sacRepOneIdSelfAttested || !sacRepTwoIdSelfAttested || sacHearingSummary.trim().length < 20) {
      toast.error('Complete both representatives, self-attested ID proof references and hearing summary.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordSacHearing(selected.sac_appeal.sac_appeal_id, {
        representative_one_name: sacRepOneName.trim(),
        representative_one_designation: sacRepOneDesignation.trim(),
        representative_one_id_reference: sacRepOneIdReference.trim(),
        representative_one_id_self_attested: true,
        representative_two_name: sacRepTwoName.trim(),
        representative_two_designation: sacRepTwoDesignation.trim(),
        representative_two_id_reference: sacRepTwoIdReference.trim(),
        representative_two_id_self_attested: true,
        hearing_summary: sacHearingSummary.trim(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('SAC hearing record saved.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the SAC hearing.');
    } finally {
      setBusy(false);
    }
  };

  const recordSacRecommendation = async () => {
    if (!selected?.sac_appeal || sacRecommendationText.trim().length < 15) {
      toast.error('Enter the SAC recommendation and its reasons.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordSacRecommendation(selected.sac_appeal.sac_appeal_id, {
        recommendation_code: sacRecommendationCode,
        recommendation_text: sacRecommendationText.trim(),
        recommendation_reference: sacRecommendationReference.trim() || null,
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('SAC recommendation recorded for Council consideration.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the SAC recommendation.');
    } finally {
      setBusy(false);
    }
  };

  const recordCouncilAppealDecision = async () => {
    if (!selected?.sac_appeal || councilDecisionReference.trim().length < 2 || councilDecisionText.trim().length < 15 || !councilDecisionUploadedAt) {
      toast.error('Complete the Council decision reference, reasons and upload date/time.');
      return;
    }
    const uploadedAt = new Date(councilDecisionUploadedAt);
    if (Number.isNaN(uploadedAt.getTime()) || uploadedAt > new Date()) {
      toast.error('Enter a valid Council decision upload date and time.');
      return;
    }
    setBusy(true);
    try {
      await workflowApi.recordCouncilAppealDecision(selected.sac_appeal.sac_appeal_id, {
        outcome_code: councilOutcome,
        decision_reference: councilDecisionReference.trim(),
        decision_text: councilDecisionText.trim(),
        decision_uploaded_at: uploadedAt.toISOString(),
      });
      setSelected(await workflowApi.detail(selected.workflow_case_id));
      await refresh();
      toast.success('Council appeal decision recorded.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not record the Council appeal decision.');
    } finally {
      setBusy(false);
    }
  };

  const createCondition = async () => {
    if (!selected || !conditionTitle || !conditionDescription || !conditionSource || !conditionDue) { toast.error('Complete all condition fields.'); return; }
    setBusy(true);
    try {
      await workflowApi.createObligation(selected.workflow_case_id, {
        title: conditionTitle, description: conditionDescription, source_condition: conditionSource,
        due_at: new Date(`${conditionDue}T23:59:00`).toISOString(),
      });
      setConditionTitle(''); setConditionDescription(''); setConditionSource(''); setConditionDue('');
      setSelected(await workflowApi.detail(selected.workflow_case_id)); await refresh(); toast.success('Condition added to the obligation ledger.');
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Could not add condition.'); }
    finally { setBusy(false); }
  };

  const handleEvidenceUploaded = async (response: DocumentUploadResponse) => {
    if (response.document_version.is_clean) {
      try {
        const job = await documentsApi.process(
          response.application_requirement_id,
          response.document_version.document_version_id,
        );
        toast.success('Evidence saved; document extraction queued.', {
          description: `Processing status: ${job.processing_status.toLowerCase()}.`,
        });
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Evidence was saved, but extraction could not be queued.');
      }
    }
    if (selected) {
      try { setSelected(await workflowApi.detail(selected.workflow_case_id)); }
      catch { /* Keep the current dossier visible; the next refresh will reload it. */ }
    }
    await refresh();
  };

  const obligationAction = async (id: string, action: string, reference?: string) => {
    if (note.trim().length < 5) { toast.error('Add a brief note for this action.'); return; }
    setBusy(true);
    try { await workflowApi.obligationAction(id, action, note.trim(), reference); setNote(''); if (selected) setSelected(await workflowApi.detail(selected.workflow_case_id)); await refresh(); toast.success('Obligation updated.'); }
    catch (err) { toast.error(err instanceof Error ? err.message : 'Obligation action failed.'); }
    finally { setBusy(false); }
  };

  if (role === 'ADMIN' || role === 'REGULATORY_POLICY_PUBLISHER') {
    const isPolicyRole = role === 'REGULATORY_POLICY_PUBLISHER';
    return (
      <section className="mx-auto max-w-4xl space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-7">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700"><ShieldCheck className="size-4"/> AIC-Flow Operations</div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{isPolicyRole ? 'Regulatory Policy Workspace' : 'Platform Administration'}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">{isPolicyRole ? 'Your account is assigned to regulatory policy governance for category-specific approval routes and effective regulatory baselines.' : 'Your account is assigned to platform administration for access and operational governance.'}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold text-slate-500">Signed-in account</div>
            <div className="mt-1 text-sm font-semibold text-slate-900">{auth.user?.full_name || 'Authorised user'}</div>
            <div className="mt-1 text-xs text-slate-500">{auth.user?.email || ''}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold text-slate-500">Assigned access scopes</div>
            <div className="mt-1 text-2xl font-bold text-indigo-700">{auth.roles.length}</div>
            <div className="mt-1 text-xs text-slate-500">Role assignments linked to this account</div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><div className="flex items-center gap-2 text-sm font-semibold text-indigo-700"><Workflow className="size-4"/> AIC-Flow Operations</div><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">Approval Workflow</h1><p className="mt-1 text-sm text-slate-500">One connected case lifecycle from application intake to verified compliance closure.</p></div>
        <button onClick={() => void refresh()} disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"><RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`}/> Refresh</button>
      </div>

      {ROLE_GUIDANCE[role] && <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 px-4 py-3"><div className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">Your workspace · {ROLE_GUIDANCE[role].title}</div><p className="mt-1 text-xs leading-relaxed text-slate-600">{ROLE_GUIDANCE[role].description}</p></div>}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-medium text-slate-500">Cases in your scope</div><div className="mt-1 text-2xl font-bold text-slate-900">{cases.length}</div></div>
        <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-medium text-slate-500">Awaiting action</div><div className="mt-1 text-2xl font-bold text-amber-600">{cases.filter((c) => c.current_stage !== 'CLOSED').length}</div></div>
        <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-medium text-slate-500">Oldest active case</div><div className="mt-1 text-2xl font-bold text-slate-900">{cases.filter((c) => c.current_stage !== 'CLOSED').length ? Math.max(...cases.filter((c) => c.current_stage !== 'CLOSED').map((c) => stageAgeDays(c.stage_entered_at))) : 0}<span className="ml-1 text-xs font-medium text-slate-500">days</span></div></div>
        <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-1 text-xs font-medium text-slate-500"><Bell className="size-3.5"/> Unread notifications</div><div className="mt-1 text-2xl font-bold text-indigo-700">{notifications.filter((n) => !n.read_at).length}</div></div>
      </div>

      {error && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{error}</div>}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(420px,1.1fr)]">
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-4 py-3"><h2 className="font-semibold text-slate-900">Case queue</h2><p className="text-xs text-slate-500">Applications within your authorised institution or review-team scope.</p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400"/><input value={queueQuery} onChange={(event) => setQueueQuery(event.target.value)} placeholder="Search application, institution or stage" aria-label="Search case queue" className="h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-xs outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"/></div>
              <div className="flex shrink-0 gap-1">
                {([['ALL','All cases'],['ACTION','My action'],['OPEN','In progress']] as const).map(([value,label]) => <button key={value} type="button" onClick={() => setQueueFilter(value)} className={`rounded-lg px-2.5 py-2 text-[11px] font-semibold transition ${queueFilter === value ? 'bg-indigo-600 text-white' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}>{label}</button>)}
              </div>
            </div>
          </div>
          {cases.length === 0 ? <div className="p-8 text-center"><FileText className="mx-auto size-8 text-slate-300"/><p className="mt-2 text-sm font-medium text-slate-700">No workflow cases in this scope</p><p className="mt-1 text-xs text-slate-500">Create an institution application or ask an administrator to assign your role to a review team.</p></div> : visibleCases.length === 0 ? <div className="p-8 text-center"><Search className="mx-auto size-7 text-slate-300"/><p className="mt-2 text-sm font-medium text-slate-700">No matching cases</p><p className="mt-1 text-xs text-slate-500">Change the search text or select another queue filter.</p></div> : <div className="divide-y divide-slate-100">{visibleCases.map((item) => <button key={item.workflow_case_id} onClick={() => void openCase(item)} className={`block w-full px-4 py-3 text-left transition hover:bg-slate-50 ${selected?.workflow_case_id === item.workflow_case_id ? 'bg-indigo-50/70' : ''}`}><div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold text-slate-900">{item.application_number}</span><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600">{stageLabel(item.current_stage)}</span></div><div className="mt-1 text-xs text-slate-600">{item.institution_name}</div><div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-slate-400"><span>{item.process_type}</span><span>AY {item.academic_year}</span><span>{ageLabel(item.stage_entered_at)}</span><span>Due: {dateLabel(item.due_at)}</span></div></button>)}</div>}
        </section>

        <section className="space-y-4">
          {selected ? <>

            {selected.route_snapshot.requires_evc === true && <section className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700"><CalendarClock className="size-4"/> EVC visit coordination</div>
                  <h3 className="mt-1 text-base font-semibold text-slate-900">Visit schedule &amp; report</h3>
                  <p className="mt-0.5 text-xs text-slate-500">Coordination records and report traceability for this application.</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-700">{selected.evc_visit?.status ? stageLabel(selected.evc_visit.status) : 'Not scheduled'}</span>
              </div>

              {selected.evc_visit && <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-3">
                  <div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-slate-500"><CalendarClock className="size-3.5"/> Scheduled visit</div>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{dateTimeLabel(selected.evc_visit.scheduled_start_at)}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500">{selected.evc_visit.scheduled_end_at ? 'Until ' + dateTimeLabel(selected.evc_visit.scheduled_end_at) : 'End time not recorded'} · Revision {selected.evc_visit.schedule_revision}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-slate-500">{selected.evc_visit.visit_mode === 'ONLINE' ? <Video className="size-3.5"/> : <MapPin className="size-3.5"/>} Visit mode &amp; venue</div>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{selected.evc_visit.visit_mode || 'Awaiting details'}</p>
                  <p className="mt-0.5 whitespace-pre-wrap text-[11px] text-slate-600">{selected.evc_visit.venue_or_meeting_details || 'Venue or meeting details not recorded'}</p>
                </div>
                <div className="rounded-lg border border-slate-100 p-3">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Official schedule reference</div>
                  <p className="mt-1 break-all text-xs text-slate-800">{selected.evc_visit.official_schedule_reference || 'Not provided'}</p>
                  <div className="mt-2 text-[10px] font-semibold uppercase text-slate-500">Institution contact</div>
                  <p className="mt-1 text-xs text-slate-800">{selected.evc_visit.institution_contact_name || 'Not provided'}{selected.evc_visit.institution_contact_email ? ' · ' + selected.evc_visit.institution_contact_email : ''}</p>
                </div>
                <div className="rounded-lg border border-slate-100 p-3">
                  <div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-slate-500"><FileCheck className="size-3.5"/> Visit report</div>
                  {selected.evc_visit.report_reference ? <>
                    <p className="mt-1 text-xs font-semibold text-slate-900">{selected.evc_visit.report_reference}</p>
                    <p className="mt-1 text-[11px] text-slate-600">{selected.evc_visit.report_outcome?.replaceAll('_', ' ')}</p>
                    <p className="mt-1 whitespace-pre-wrap text-[11px] text-slate-600">{selected.evc_visit.report_summary}</p>
                    <p className="mt-1 text-[10px] text-slate-400">Recorded {dateTimeLabel(selected.evc_visit.report_recorded_at)}</p>
                  </> : <p className="mt-1 text-xs text-slate-500">Report not yet recorded</p>}
                </div>
              </div>}

              {selected.evc_visit?.status === 'DETAILS_REQUIRED' && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">Complete the visit details before progressing this case. The earlier schedule note remains in the case history.</p>}
              {selected.evc_visit?.status === 'CANCELLED' && <p className="mt-3 rounded-lg border border-rose-100 bg-rose-50 p-2.5 text-xs text-rose-800">Previous visit cancelled: {selected.evc_visit.cancellation_reason}</p>}

              {['EVC_COORDINATOR', 'REGIONAL_OFFICER', 'LEAD_AUDITOR'].includes(role) && ['EVC_COORDINATION', 'EVC_SCHEDULED'].includes(selected.current_stage) && selected.evc_visit?.status !== 'COMPLETED' && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">{selected.evc_visit?.status === 'SCHEDULED' ? 'Reschedule visit' : 'Schedule visit'}</h4>
                <p className="mt-0.5 text-[11px] text-slate-500">Record the visit details communicated for this application.</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Visit mode
                    <select value={evcMode} onChange={(e) => setEvcMode(e.target.value as 'ONLINE' | 'OFFLINE')} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="ONLINE">Online</option><option value="OFFLINE">Offline</option></select>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Visit start
                    <input type="datetime-local" value={evcStartAt} onChange={(e) => setEvcStartAt(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Visit end (optional)
                    <input type="datetime-local" value={evcEndAt} onChange={(e) => setEvcEndAt(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Official schedule reference (optional)
                    <input value={evcOfficialReference} onChange={(e) => setEvcOfficialReference(e.target.value)} placeholder="Reference from the official portal" className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Institution contact name (optional)
                    <input value={evcContactName} onChange={(e) => setEvcContactName(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Institution contact email (optional)
                    <input type="email" value={evcContactEmail} onChange={(e) => setEvcContactEmail(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                </div>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Venue or meeting details
                  <textarea value={evcVenue} onChange={(e) => setEvcVenue(e.target.value)} rows={2} placeholder="Physical venue or online meeting instructions" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Coordination note
                  <textarea value={evcCoordinationNote} onChange={(e) => setEvcCoordinationNote(e.target.value)} rows={2} placeholder="Record the coordination instruction or schedule communication" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <button onClick={() => void scheduleEvc()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{selected.evc_visit?.status === 'SCHEDULED' ? 'Save revised schedule' : 'Save visit schedule'}</button>
                {selected.evc_visit?.status === 'SCHEDULED' && <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <input value={evcCancelReason} onChange={(e) => setEvcCancelReason(e.target.value)} placeholder="Reason for cancelling the visit" className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                  <button onClick={() => void cancelEvc()} disabled={busy} className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 disabled:opacity-50">Cancel visit</button>
                </div>}
              </div>}

              {['EVC_MEMBER', 'EVC_COORDINATOR'].includes(role) && selected.current_stage === 'EVC_SCHEDULED' && selected.evc_visit?.status === 'SCHEDULED' && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">Record EVC visit report</h4>
                <p className="mt-0.5 text-[11px] text-slate-500">Enter the report reference, observations and outcome category. The statutory decision remains separate.</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Report reference
                    <input value={evcReportReference} onChange={(e) => setEvcReportReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Report outcome
                    <select value={evcReportOutcome} onChange={(e) => setEvcReportOutcome(e.target.value as typeof evcReportOutcome)} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs">
                      <option value="INCONCLUSIVE">Inconclusive</option><option value="NO_DEFICIENCY_RECORDED">No deficiency recorded</option><option value="DEFICIENCIES_OBSERVED">Deficiencies observed</option><option value="FOLLOW_UP_REQUIRED">Follow-up required</option>
                    </select>
                  </label>
                </div>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Visit observations
                  <textarea value={evcReportSummary} onChange={(e) => setEvcReportSummary(e.target.value)} rows={3} placeholder="Summarise the observations recorded during the EVC visit" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Report recording note
                  <textarea value={evcReportNote} onChange={(e) => setEvcReportNote(e.target.value)} rows={2} placeholder="Add a note about recording this report" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <button onClick={() => void recordEvcReport()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Save EVC report</button>
              </div>}
            </section>}

            {selected.route_snapshot.requires_committee === true && <section className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700"><Gavel className="size-4"/> Standing Hearing Committee</div>
                  <h3 className="mt-1 text-base font-semibold text-slate-900">SHC hearing &amp; recommendation</h3>
                  <p className="mt-0.5 text-xs text-slate-500">Review of compliance relating to scrutiny, EVC or notice deficiencies.</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-700">{selected.shc_proceeding?.status ? stageLabel(selected.shc_proceeding.status) : 'Proceeding not scheduled'}</span>
              </div>

              {selected.shc_proceeding && <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-3">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Hearing schedule</div>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{dateTimeLabel(selected.shc_proceeding.hearing_scheduled_at)}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500">{selected.shc_proceeding.hearing_mode === 'IN_PERSON' ? 'In person' : selected.shc_proceeding.hearing_mode || 'Mode not recorded'} · Revision {selected.shc_proceeding.schedule_revision}</p>
                  <p className="mt-1 whitespace-pre-wrap text-[11px] text-slate-600">{selected.shc_proceeding.hearing_details || 'Hearing details not recorded'}</p>
                </div>
                <div className="rounded-lg border border-slate-100 p-3">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Notice and schedule references</div>
                  <p className="mt-1 text-xs text-slate-700">Notice: {selected.shc_proceeding.notice_reference || 'Not provided'}</p>
                  <p className="mt-1 break-all text-xs text-slate-700">Official schedule: {selected.shc_proceeding.official_schedule_reference || 'Not provided'}</p>
                  <div className="mt-2 text-[10px] font-semibold uppercase text-slate-500">Institution compliance submission</div>
                  <p className="mt-1 break-all text-xs text-slate-700">{selected.shc_proceeding.institution_submission_reference || 'Not submitted'}</p>
                </div>
                {selected.shc_proceeding.hearing_recorded_at && <div className="rounded-lg border border-slate-100 p-3 sm:col-span-2">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Institution representatives recorded</div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div><p className="text-xs font-semibold text-slate-900">{selected.shc_proceeding.representative_one_name}</p><p className="text-[11px] text-slate-500">{selected.shc_proceeding.representative_one_designation}</p></div>
                    <div><p className="text-xs font-semibold text-slate-900">{selected.shc_proceeding.representative_two_name}</p><p className="text-[11px] text-slate-500">{selected.shc_proceeding.representative_two_designation}</p></div>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-xs text-slate-700">{selected.shc_proceeding.hearing_summary}</p>
                  <p className="mt-1 text-[10px] text-slate-400">Hearing recorded {dateTimeLabel(selected.shc_proceeding.hearing_recorded_at)}</p>
                </div>}
                {selected.shc_proceeding.recommendation_recorded_at && <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3 sm:col-span-2">
                  <div className="text-[10px] font-semibold uppercase text-indigo-700">SHC recommendation for Executive Committee</div>
                  <p className="mt-1 text-xs font-semibold text-slate-900">{selected.shc_proceeding.recommendation_code?.replaceAll('_', ' ')}</p>
                  <p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{selected.shc_proceeding.recommendation_text}</p>
                  <p className="mt-1 text-[10px] text-slate-500">Reference: {selected.shc_proceeding.recommendation_reference || 'Not provided'} · Recorded {dateTimeLabel(selected.shc_proceeding.recommendation_recorded_at)}</p>
                </div>}
              </div>}

              {selected.current_stage === 'COMMITTEE_PROCEEDINGS' && role === 'COMMITTEE_SECRETARIAT' && (!selected.shc_proceeding || ['PREPARATION', 'SCHEDULED'].includes(selected.shc_proceeding.status)) && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">{selected.shc_proceeding?.status === 'SCHEDULED' ? 'Revise hearing schedule' : 'Schedule SHC hearing'}</h4>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Hearing mode
                    <select value={shcHearingMode} onChange={(e) => setShcHearingMode(e.target.value as 'ONLINE' | 'IN_PERSON')} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="ONLINE">Online</option><option value="IN_PERSON">In person</option></select>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Hearing date and time
                    <input type="datetime-local" value={shcHearingAt} onChange={(e) => setShcHearingAt(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Show Cause Notice / notice reference (optional)
                    <input value={shcNoticeReference} onChange={(e) => setShcNoticeReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Official hearing schedule reference (optional)
                    <input value={shcOfficialReference} onChange={(e) => setShcOfficialReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                  </label>
                </div>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Hearing details
                  <textarea value={shcHearingDetails} onChange={(e) => setShcHearingDetails(e.target.value)} rows={2} placeholder="Venue or online hearing instructions" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <button onClick={() => void scheduleShc()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{selected.shc_proceeding?.status === 'SCHEDULED' ? 'Save revised hearing schedule' : 'Schedule SHC hearing'}</button>
              </div>}

              {selected.shc_proceeding?.status === 'SCHEDULED' && role === 'INSTITUTION_USER' && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">Submit compliance material for the hearing</h4>
                <p className="mt-0.5 text-[11px] text-slate-500">Enter the reference for the compliance documents and supporting material submitted for SHC consideration.</p>
                <label className="mt-3 grid gap-1 text-[11px] font-medium text-slate-600">Submission / document reference
                  <input value={shcSubmissionReference} onChange={(e) => setShcSubmissionReference(e.target.value)} placeholder="Submission acknowledgement or document reference" className="h-9 rounded-lg border border-slate-200 px-3 text-xs"/>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Submission note
                  <textarea value={shcSubmissionNote} onChange={(e) => setShcSubmissionNote(e.target.value)} rows={2} placeholder="Describe the compliance material submitted" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <button onClick={() => void submitShcCompliance()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Record compliance submission</button>
              </div>}

              {selected.shc_proceeding?.status === 'SCHEDULED' && role === 'COMMITTEE_SECRETARIAT' && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">Record SHC hearing</h4>
                <p className="mt-0.5 text-[11px] text-slate-500">Record the two institution representatives and the hearing proceedings.</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 1 name<input value={shcRepOneName} onChange={(e) => setShcRepOneName(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 1 designation<input value={shcRepOneDesignation} onChange={(e) => setShcRepOneDesignation(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 2 name<input value={shcRepTwoName} onChange={(e) => setShcRepTwoName(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                  <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 2 designation<input value={shcRepTwoDesignation} onChange={(e) => setShcRepTwoDesignation(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                </div>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Hearing proceedings summary<textarea value={shcHearingSummary} onChange={(e) => setShcHearingSummary(e.target.value)} rows={3} placeholder="Summarise the institution's presentation and compliance material considered" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/></label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Record note<textarea value={shcHearingNote} onChange={(e) => setShcHearingNote(e.target.value)} rows={2} placeholder="Add a note for the proceeding history" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/></label>
                <button onClick={() => void recordShcHearing()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Save hearing record</button>
              </div>}

              {selected.shc_proceeding?.status === 'HEARING_RECORDED' && role === 'COMMITTEE_SECRETARIAT' && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">Record SHC recommendation</h4>
                <p className="mt-0.5 text-[11px] text-slate-500">This recommendation is placed before the Executive Committee; it is not the statutory decision.</p>
                <label className="mt-3 grid gap-1 text-[11px] font-medium text-slate-600">Recommendation category
                  <select value={shcRecommendationCode} onChange={(e) => setShcRecommendationCode(e.target.value as typeof shcRecommendationCode)} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs">
                    <option value="COMPLIANCE_REVIEWED">Compliance reviewed</option>
                    <option value="FURTHER_COMPLIANCE_REQUIRED">Further compliance required</option>
                    <option value="DEFICIENCIES_REMAIN">Deficiencies remain</option>
                    <option value="INCONCLUSIVE">Inconclusive</option>
                  </select>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Recommendation and reasons
                  <textarea value={shcRecommendationText} onChange={(e) => setShcRecommendationText(e.target.value)} rows={4} placeholder="Record the committee's recommendation and reasons for Executive Committee consideration" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Recommendation reference (optional)
                  <input value={shcRecommendationReference} onChange={(e) => setShcRecommendationReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-3 text-xs"/>
                </label>
                <button onClick={() => void recordShcRecommendation()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Submit SHC recommendation</button>
              </div>}

              {selected.shc_proceeding?.status === 'RECOMMENDATION_RECORDED' && <p className="mt-4 rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-xs text-emerald-800">SHC recommendation is recorded and ready for Executive Committee consideration.</p>}
            </section>}
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Case dossier</div><h2 className="mt-1 text-lg font-bold text-slate-900">{selected.application_number}</h2><p className="text-sm text-slate-600">{selected.institution_name} · {selected.process_type}</p></div><span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">{stageLabel(selected.current_stage)}</span></div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs"><div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Route</span><div className="mt-0.5 font-semibold text-slate-800">{selected.route_code}</div></div><div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Regulatory baseline</span><div className="mt-0.5 font-semibold text-slate-800">{selected.regulatory_version}</div></div></div>
              {selected.route_snapshot.route_status === 'MANUAL_CONFIRMATION_REQUIRED' && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">Route confirmation is required: an authorised policy officer must record the applicable category-specific route before this case can progress.</p>}
              {selected.route_snapshot.requires_committee == null && selected.route_snapshot.requires_evc === true && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">EVC completion is recorded here. The approved category-specific route determines whether the Standing Hearing Committee (SHC) stage follows.</p>}
              {role === 'INTAKE_OFFICER' && selected.current_stage === 'SUBMITTED' && selected.assigned_role_code === 'INTAKE_OFFICER' && !selected.assigned_user_id && teamId && <button onClick={() => void assignCase()} disabled={busy} className="mt-3 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Assign to my review team</button>}
              <div className="mt-4 space-y-2"><label className="text-xs font-semibold text-slate-700">Action reason / case note</label><textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Record the reason, instruction or review note..." className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"/>
                <div className="flex flex-wrap gap-2">{nextStages.map((stage) => <button key={stage} onClick={() => void transition(stage)} disabled={busy} className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{stageLabel(stage)}</button>)}</div>
              </div>
            </div>

            {selected.executive_committee_decision && <section className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700"><FileCheck className="size-4"/> Executive Committee decision</div>
              <div className="mt-2 flex flex-wrap items-start justify-between gap-2"><h3 className="text-base font-semibold text-slate-900">{stageLabel(selected.executive_committee_decision.outcome_code)}</h3><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold text-emerald-700">Decision recorded</span></div>
              <p className="mt-1 text-xs text-slate-600">Decision reference: {selected.executive_committee_decision.decision_reference}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{selected.executive_committee_decision.decision_reasons}</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-3"><div className="text-[10px] font-semibold uppercase text-slate-500">Speaking Order reference</div><p className="mt-1 break-all text-xs font-semibold text-slate-900">{selected.executive_committee_decision.speaking_order_reference}</p><p className="mt-1 text-[11px] text-slate-500">Uploaded {dateTimeLabel(selected.executive_committee_decision.speaking_order_uploaded_at)}</p></div>
                <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3"><div className="text-[10px] font-semibold uppercase text-indigo-700">Appeal filing deadline</div><p className="mt-1 text-sm font-semibold text-slate-900">{dateTimeLabel(selected.executive_committee_decision.appeal_deadline_at)}</p><p className="mt-1 text-[10px] text-slate-500">Calculated as seven days from Speaking Order upload time.</p></div>
              </div>
            </section>}


            {selected.executive_committee_decision && <section className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-700"><Gavel className="size-4"/> Standing Appellate Committee</div>
                  <h3 className="mt-1 text-base font-semibold text-slate-900">Institution appeal &amp; Council decision</h3>
                  <p className="mt-0.5 text-xs text-slate-500">A separate appeal record linked to the Executive Committee decision above.</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-700">{selected.sac_appeal ? stageLabel(selected.sac_appeal.status) : 'Appeal not filed'}</span>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-3">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Executive Committee decision</div>
                  <p className="mt-1 text-xs font-semibold text-slate-900">{selected.executive_committee_decision.decision_reference}</p>
                  <p className="mt-1 text-[11px] text-slate-500">Speaking Order uploaded {dateTimeLabel(selected.executive_committee_decision.speaking_order_uploaded_at)}</p>
                </div>
                <div className="rounded-lg border border-violet-100 bg-violet-50/50 p-3">
                  <div className="text-[10px] font-semibold uppercase text-violet-700">Last date for appeal</div>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{dateTimeLabel(selected.executive_committee_decision.appeal_deadline_at)}</p>
                  <p className="mt-1 text-[10px] text-slate-500">Seven days from the date and time the decision was uploaded.</p>
                </div>
              </div>

              {!selected.sac_appeal && role === 'INSTITUTION_USER' && Date.now() <= new Date(selected.executive_committee_decision.appeal_deadline_at).getTime() && <div className="mt-4 border-t border-slate-100 pt-4">
                <h4 className="text-sm font-semibold text-slate-900">File an appeal to the Council</h4>
                <p className="mt-0.5 text-[11px] text-slate-500">The appeal will be considered by the Standing Appellate Committee. Enter the grounds and references for supporting compliance material.</p>
                <label className="mt-3 grid gap-1 text-[11px] font-medium text-slate-600">Appeal / portal reference (optional)
                  <input value={sacAppealReference} onChange={(e) => setSacAppealReference(e.target.value)} placeholder="Reference received from the appeal portal, if available" className="h-9 rounded-lg border border-slate-200 px-3 text-xs"/>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Grounds of appeal
                  <textarea value={sacAppealGrounds} onChange={(e) => setSacAppealGrounds(e.target.value)} rows={4} placeholder="Explain why the institution is aggrieved by the Executive Committee decision" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Supporting compliance material references
                  <textarea value={sacSupportingMaterialReference} onChange={(e) => setSacSupportingMaterialReference(e.target.value)} rows={3} placeholder="List supporting document references, acknowledgements and compliance evidence to be presented before SAC" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                </label>
                <button onClick={() => void fileSacAppeal()} disabled={busy} className="mt-3 rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Submit appeal</button>
              </div>}

              {selected.sac_appeal && <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div><h4 className="text-sm font-semibold text-slate-900">Appeal record</h4><p className="mt-0.5 text-[11px] text-slate-500">Filed {dateTimeLabel(selected.sac_appeal.filed_at)} · {selected.sac_appeal.appeal_reference || 'Portal reference not provided'}</p></div>
                  <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-semibold text-violet-700">{stageLabel(selected.sac_appeal.status)}</span>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded-lg border border-slate-100 p-3"><div className="text-[10px] font-semibold uppercase text-slate-500">Grounds of appeal</div><p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{selected.sac_appeal.appeal_grounds}</p></div>
                  <div className="rounded-lg border border-slate-100 p-3"><div className="text-[10px] font-semibold uppercase text-slate-500">Supporting material</div><p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{selected.sac_appeal.supporting_material_reference}</p><p className="mt-2 text-[10px] text-slate-500">Appeal deadline: {dateTimeLabel(selected.sac_appeal.appeal_deadline_at)}</p></div>
                </div>

                <div className="rounded-lg border border-slate-100 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-slate-500"><CalendarClock className="size-3.5"/> SAC hearing schedule</div><span className="text-[10px] text-slate-400">Revision {selected.sac_appeal.schedule_revision}</span></div>
                  {selected.sac_appeal.hearing_scheduled_at ? <><p className="mt-1 text-sm font-semibold text-slate-900">{dateTimeLabel(selected.sac_appeal.hearing_scheduled_at)}</p><p className="mt-0.5 text-xs text-slate-600">{selected.sac_appeal.hearing_mode === 'IN_PERSON' ? 'In person' : selected.sac_appeal.hearing_mode} · {selected.sac_appeal.hearing_details}</p><p className="mt-1 break-all text-[10px] text-slate-500">Official schedule reference: {selected.sac_appeal.official_schedule_reference || 'Not provided'}</p></> : <p className="mt-1 text-xs text-slate-500">The SAC hearing schedule has not yet been recorded.</p>}
                  {role === 'SAC_SECRETARIAT' && ['FILED','SCHEDULED'].includes(selected.sac_appeal.status) && <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Hearing mode<select value={sacHearingMode} onChange={(e) => setSacHearingMode(e.target.value as 'ONLINE' | 'IN_PERSON')} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="ONLINE">Online</option><option value="IN_PERSON">In person</option></select></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Hearing date and time<input type="datetime-local" value={sacHearingAt} onChange={(e) => setSacHearingAt(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600 sm:col-span-2">Official schedule reference (optional)<input value={sacOfficialScheduleReference} onChange={(e) => setSacOfficialScheduleReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-3 text-xs"/></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600 sm:col-span-2">Hearing details<textarea value={sacHearingDetails} onChange={(e) => setSacHearingDetails(e.target.value)} rows={2} placeholder="Enter the schedule information notified for the SAC hearing" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/></label>
                    <button onClick={() => void scheduleSacHearing()} disabled={busy} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50 sm:col-span-2">{selected.sac_appeal.status === 'SCHEDULED' ? 'Save revised schedule' : 'Record SAC hearing schedule'}</button>
                  </div>}
                </div>

                <div className="rounded-lg border border-slate-100 p-3">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Regulation Bureau observations</div>
                  {selected.sac_appeal.regulation_bureau_observations ? <><p className="mt-1 text-xs font-semibold text-slate-800">{selected.sac_appeal.regulation_bureau_observation_reference}</p><p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{selected.sac_appeal.regulation_bureau_observations}</p><p className="mt-1 text-[10px] text-slate-400">Recorded {dateTimeLabel(selected.sac_appeal.bureau_observations_recorded_at)}</p></> : <p className="mt-1 text-xs text-slate-500">No Regulation Bureau observations have been recorded for this appeal.</p>}
                  {['BUREAU_SUPERVISOR','REGIONAL_OFFICER','LEAD_AUDITOR'].includes(role) && ['FILED','SCHEDULED','HEARING_RECORDED'].includes(selected.sac_appeal.status) && <div className="mt-3 space-y-2">
                    <input value={sacBureauObservationReference} onChange={(e) => setSacBureauObservationReference(e.target.value)} placeholder="Observation reference" className="h-9 w-full rounded-lg border border-slate-200 px-3 text-xs"/>
                    <textarea value={sacBureauObservations} onChange={(e) => setSacBureauObservations(e.target.value)} rows={3} placeholder="Record Regulation Bureau observations to be placed before SAC" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                    <button onClick={() => void recordSacBureauObservations()} disabled={busy} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 disabled:opacity-50">Save Bureau observations</button>
                  </div>}
                </div>

                {selected.sac_appeal.hearing_recorded_at && <div className="rounded-lg border border-slate-100 p-3">
                  <div className="text-[10px] font-semibold uppercase text-slate-500">Institution representatives &amp; SAC hearing</div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div><p className="text-xs font-semibold text-slate-900">{selected.sac_appeal.representative_one_name}</p><p className="text-[11px] text-slate-500">{selected.sac_appeal.representative_one_designation}</p>{['INSTITUTION_USER','SAC_SECRETARIAT','COUNCIL_SECRETARIAT'].includes(role) && <p className="mt-1 text-[10px] text-slate-500">Self-attested ID proof: {selected.sac_appeal.representative_one_id_reference}</p>}</div>
                    <div><p className="text-xs font-semibold text-slate-900">{selected.sac_appeal.representative_two_name}</p><p className="text-[11px] text-slate-500">{selected.sac_appeal.representative_two_designation}</p>{['INSTITUTION_USER','SAC_SECRETARIAT','COUNCIL_SECRETARIAT'].includes(role) && <p className="mt-1 text-[10px] text-slate-500">Self-attested ID proof: {selected.sac_appeal.representative_two_id_reference}</p>}</div>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-xs text-slate-700">{selected.sac_appeal.hearing_summary}</p>
                  <p className="mt-1 text-[10px] text-slate-400">Hearing recorded {dateTimeLabel(selected.sac_appeal.hearing_recorded_at)}</p>
                </div>}

                {role === 'SAC_SECRETARIAT' && selected.sac_appeal.status === 'SCHEDULED' && selected.sac_appeal.hearing_scheduled_at && new Date(selected.sac_appeal.hearing_scheduled_at).getTime() <= Date.now() && <div className="rounded-lg border border-slate-200 p-3">
                  <h4 className="text-sm font-semibold text-slate-900">Record SAC hearing</h4>
                  <p className="mt-0.5 text-[11px] text-slate-500">Record two applicant representatives and the material presented before the Committee.</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 1 name<input value={sacRepOneName} onChange={(e) => setSacRepOneName(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 1 designation<input value={sacRepOneDesignation} onChange={(e) => setSacRepOneDesignation(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 1 self-attested ID proof reference<input value={sacRepOneIdReference} onChange={(e) => setSacRepOneIdReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="flex items-center gap-2 text-[11px] text-slate-600"><input type="checkbox" checked={sacRepOneIdSelfAttested} onChange={(e) => setSacRepOneIdSelfAttested(e.target.checked)}/> ID proof is self-attested</label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 2 name<input value={sacRepTwoName} onChange={(e) => setSacRepTwoName(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 2 designation<input value={sacRepTwoDesignation} onChange={(e) => setSacRepTwoDesignation(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Representative 2 self-attested ID proof reference<input value={sacRepTwoIdReference} onChange={(e) => setSacRepTwoIdReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <label className="flex items-center gap-2 text-[11px] text-slate-600"><input type="checkbox" checked={sacRepTwoIdSelfAttested} onChange={(e) => setSacRepTwoIdSelfAttested(e.target.checked)}/> ID proof is self-attested</label>
                  </div>
                  <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">SAC hearing summary<textarea value={sacHearingSummary} onChange={(e) => setSacHearingSummary(e.target.value)} rows={4} placeholder="Record the institution's presentation and supporting compliance material considered by SAC" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/></label>
                  <button onClick={() => void recordSacHearing()} disabled={busy} className="mt-3 rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Save SAC hearing record</button>
                </div>}

                {selected.sac_appeal.hearing_recorded_at && <div className="rounded-lg border border-violet-100 bg-violet-50/40 p-3">
                  <div className="text-[10px] font-semibold uppercase text-violet-700">SAC recommendation to Council</div>
                  {selected.sac_appeal.recommendation_recorded_at ? <><p className="mt-1 text-xs font-semibold text-slate-900">{stageLabel(selected.sac_appeal.recommendation_code || '')}</p><p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{selected.sac_appeal.recommendation_text}</p><p className="mt-1 text-[10px] text-slate-500">Reference: {selected.sac_appeal.recommendation_reference || 'Not provided'} · Recorded {dateTimeLabel(selected.sac_appeal.recommendation_recorded_at)}</p></> : <p className="mt-1 text-xs text-slate-500">Recommendation not yet recorded.</p>}
                  {role === 'SAC_SECRETARIAT' && selected.sac_appeal.status === 'HEARING_RECORDED' && <div className="mt-3 space-y-2">
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Recommendation<select value={sacRecommendationCode} onChange={(e) => setSacRecommendationCode(e.target.value as typeof sacRecommendationCode)} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="RECOMMEND_TO_COUNCIL">Recommend to Council</option><option value="NOT_RECOMMEND_TO_COUNCIL">Not recommend to Council</option><option value="FURTHER_REVIEW_REQUIRED">Further review required</option></select></label>
                    <textarea value={sacRecommendationText} onChange={(e) => setSacRecommendationText(e.target.value)} rows={4} placeholder="Record the SAC recommendation and reasons for the Council" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                    <input value={sacRecommendationReference} onChange={(e) => setSacRecommendationReference(e.target.value)} placeholder="Recommendation reference (optional)" className="h-9 w-full rounded-lg border border-slate-200 px-3 text-xs"/>
                    <button onClick={() => void recordSacRecommendation()} disabled={busy} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Submit SAC recommendation to Council</button>
                  </div>}
                </div>}

                {selected.sac_appeal.recommendation_recorded_at && <div className="rounded-lg border border-emerald-100 bg-emerald-50/40 p-3">
                  <div className="text-[10px] font-semibold uppercase text-emerald-700">Council final decision</div>
                  {selected.sac_appeal.council_decision_recorded_at ? <><p className="mt-1 text-xs font-semibold text-slate-900">{stageLabel(selected.sac_appeal.council_outcome_code || '')}</p><p className="mt-1 text-xs font-semibold text-slate-800">{selected.sac_appeal.council_decision_reference}</p><p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{selected.sac_appeal.council_decision_text}</p><p className="mt-1 text-[10px] text-slate-500">Uploaded {dateTimeLabel(selected.sac_appeal.council_decision_uploaded_at)}</p></> : <p className="mt-1 text-xs text-slate-500">Council decision not yet recorded.</p>}
                  {role === 'COUNCIL_SECRETARIAT' && selected.sac_appeal.status === 'RECOMMENDATION_RECORDED' && <div className="mt-3 space-y-2">
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Council outcome<select value={councilOutcome} onChange={(e) => setCouncilOutcome(e.target.value as typeof councilOutcome)} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="UPHOLD_EXECUTIVE_COMMITTEE">Uphold Executive Committee decision</option><option value="SET_ASIDE_EXECUTIVE_COMMITTEE">Set aside Executive Committee decision</option><option value="MODIFY_EXECUTIVE_COMMITTEE">Modify Executive Committee decision</option><option value="REMAND_FOR_RECONSIDERATION">Remand for reconsideration</option></select></label>
                    <input value={councilDecisionReference} onChange={(e) => setCouncilDecisionReference(e.target.value)} placeholder="Council decision reference" className="h-9 w-full rounded-lg border border-slate-200 px-3 text-xs"/>
                    <label className="grid gap-1 text-[11px] font-medium text-slate-600">Decision upload date and time<input type="datetime-local" value={councilDecisionUploadedAt} onChange={(e) => setCouncilDecisionUploadedAt(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/></label>
                    <textarea value={councilDecisionText} onChange={(e) => setCouncilDecisionText(e.target.value)} rows={4} placeholder="Record the Council's final decision and reasons" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
                    <button onClick={() => void recordCouncilAppealDecision()} disabled={busy} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Record Council final decision</button>
                  </div>}
                </div>}
              </div>}
            </section>}

            {role === 'COMPETENT_AUTHORITY' && selected.current_stage === 'AWAITING_AUTHORITY' && !selected.executive_committee_decision && <section className="rounded-xl border border-indigo-200 bg-white p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700"><Gavel className="size-4"/> Executive Committee decision</div>
              <h3 className="mt-1 text-base font-semibold text-slate-900">Record authorised outcome</h3>
              <p className="mt-1 text-xs text-slate-500">Record the human decision and the issued Speaking Order reference. The appeal deadline is calculated from its upload time.</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label className="grid gap-1 text-[11px] font-medium text-slate-600">Decision outcome
                  <select value={ecOutcome} onChange={(e) => setEcOutcome(e.target.value as typeof ecOutcome)} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="APPROVED">Approved</option><option value="APPROVED_WITH_CONDITIONS">Approved with conditions</option><option value="REJECTED">Rejected</option></select>
                </label>
                <label className="grid gap-1 text-[11px] font-medium text-slate-600">Decision reference
                  <input value={ecDecisionReference} onChange={(e) => setEcDecisionReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                </label>
                <label className="grid gap-1 text-[11px] font-medium text-slate-600">Speaking Order reference
                  <input value={ecSpeakingOrderReference} onChange={(e) => setEcSpeakingOrderReference(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                </label>
                <label className="grid gap-1 text-[11px] font-medium text-slate-600">Speaking Order upload date and time
                  <input type="datetime-local" value={ecSpeakingOrderUploadedAt} onChange={(e) => setEcSpeakingOrderUploadedAt(e.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-xs"/>
                </label>
              </div>
              <label className="mt-2 grid gap-1 text-[11px] font-medium text-slate-600">Speaking Order reasons
                <textarea value={ecDecisionReasons} onChange={(e) => setEcDecisionReasons(e.target.value)} rows={4} placeholder="Record the reasons stated in the Speaking Order" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
              </label>
              <button onClick={() => void recordExecutiveDecision()} disabled={busy} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Record Executive Committee decision</button>
            </section>}

            {role === 'COMPETENT_AUTHORITY' && ['APPROVED_WITH_CONDITIONS', 'OBLIGATION_TRACKING'].includes(selected.current_stage) && <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Register approval condition</h3><div className="mt-3 grid gap-2"><input value={conditionTitle} onChange={(e) => setConditionTitle(e.target.value)} placeholder="Condition title" className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><textarea value={conditionDescription} onChange={(e) => setConditionDescription(e.target.value)} placeholder="What must the institution do?" rows={2} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><textarea value={conditionSource} onChange={(e) => setConditionSource(e.target.value)} placeholder="Decision / condition source reference" rows={2} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><input type="date" value={conditionDue} onChange={(e) => setConditionDue(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><button onClick={() => void createCondition()} disabled={busy} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white">Add condition</button></div></div>}

            {selected.requirements.length > 0 && <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-900">Application evidence checklist</h3><p className="mt-0.5 text-xs text-slate-500">Documents and requirement states linked to this application.</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">{selected.requirements.length} items</span></div><div className="mt-3 divide-y divide-slate-100">{selected.requirements.map((req) => { const canUpload = role === 'INSTITUTION_USER' && ['DRAFT', 'CLARIFICATION_REQUESTED'].includes(selected.current_stage) && req.applicability_status !== 'NOT_APPLICABLE' && req.status !== 'SATISFIED'; return <div key={req.application_requirement_id} className="flex flex-wrap items-center justify-between gap-3 py-2.5"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="font-mono text-[10px] font-semibold text-slate-500">{req.item_code}</span><span className="text-sm font-medium text-slate-800">{req.title}</span></div><p className="mt-0.5 text-[11px] text-slate-500">{stageLabel(req.status)} · {stageLabel(req.applicability_status)}{req.determination_reason ? ` · ${req.determination_reason}` : ''}</p></div>{canUpload && <button onClick={() => { setUploadRequirement(req); setUploadObligationId(null); setUploadOpen(true); }} className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100">Upload evidence</button>}</div>; })}</div></div>}

            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><Clock3 className="size-4 text-indigo-600"/><h3 className="font-semibold text-slate-900">Evidence-to-resolution timeline</h3></div><div className="mt-3 space-y-3">{selected.events.map((event) => <div key={event.workflow_event_id} className="relative border-l-2 border-indigo-100 pl-3"><div className="text-xs font-semibold text-slate-800">{event.event_type.replace('COMMITTEE_', 'SHC ').replaceAll('_', ' ')}</div><p className="mt-0.5 text-xs text-slate-600">{event.summary}</p><div className="mt-0.5 text-[10px] text-slate-400">{new Date(event.occurred_at).toLocaleString()}</div></div>)}</div></div>

            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><ShieldCheck className="size-4 text-emerald-600"/><h3 className="font-semibold text-slate-900">Compliance obligations</h3></div>{selected.obligations.length === 0 ? <p className="mt-2 text-xs text-slate-500">No post-decision conditions recorded.</p> : <div className="mt-3 space-y-3">{selected.obligations.map((o) => <div key={o.obligation_id} className="rounded-lg border border-slate-100 p-3"><div className="flex items-start justify-between gap-2"><div className="text-sm font-semibold text-slate-800">{o.title}</div><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold">{stageLabel(o.status)}</span></div><p className="mt-1 text-xs text-slate-600">{o.description}</p><p className="mt-1 text-[11px] text-slate-400">Due {dateLabel(o.due_at)} · {o.source_condition}</p>{o.evidence_document_version_id && <div className="mt-2 rounded-lg bg-slate-50 px-3 py-2"><p className="truncate text-[11px] font-medium text-slate-700">Submitted: {o.evidence_reference || 'Evidence document'}</p><a href={workflowApi.getObligationEvidenceDownloadUrl(o.obligation_id)} className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 hover:text-indigo-900"><FileCheck className="size-3.5"/> View submitted evidence file</a></div>}{role === 'INSTITUTION_USER' && ['OPEN','RETURNED'].includes(o.status) && <div className="mt-3 space-y-2"><label className="grid gap-1 text-[11px] font-medium text-slate-600">Document type<select value={obligationEvidenceRequirementIds[o.obligation_id] || ''} onChange={(e) => setObligationEvidenceRequirementIds((prev) => ({ ...prev, [o.obligation_id]: e.target.value }))} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-xs"><option value="">Select an applicable application requirement</option>{selected.requirements.filter((req) => req.applicability_status === 'APPLICABLE').map((req) => <option key={req.application_requirement_id} value={req.application_requirement_id}>{req.item_code} · {req.title}</option>)}</select></label><button onClick={() => { const req = selected.requirements.find((item) => item.application_requirement_id === obligationEvidenceRequirementIds[o.obligation_id]); if (!req) { toast.error('Select the document type for this evidence upload.'); return; } setUploadRequirement(req); setUploadObligationId(o.obligation_id); setUploadOpen(true); }} disabled={!obligationEvidenceRequirementIds[o.obligation_id]} className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Upload condition evidence</button><div className="flex gap-2"><input value={evidenceReference} onChange={(e) => setEvidenceReference(e.target.value)} placeholder="External evidence reference (optional)" className="min-w-0 flex-1 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"/><button onClick={() => void obligationAction(o.obligation_id, 'EVIDENCE_SUBMITTED', evidenceReference)} disabled={!evidenceReference.trim()} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50">Submit reference</button></div></div>}{['SCRUTINY_OFFICER','AUDITOR','BUREAU_SUPERVISOR','LEAD_AUDITOR'].includes(role) && ['EVIDENCE_SUBMITTED','UNDER_VERIFICATION'].includes(o.status) && <div className="mt-2 flex gap-2">{o.status === 'EVIDENCE_SUBMITTED' && <button onClick={() => void obligationAction(o.obligation_id, 'START_VERIFICATION')} className="rounded border px-2 py-1 text-xs">Start review</button>}<button onClick={() => void obligationAction(o.obligation_id, 'VERIFY')} className="rounded bg-emerald-600 px-2 py-1 text-xs font-semibold text-white">Verify</button><button onClick={() => void obligationAction(o.obligation_id, 'RETURN')} className="rounded border border-amber-300 px-2 py-1 text-xs">Return</button></div>}{o.status === 'VERIFIED' && ['BUREAU_SUPERVISOR','REGIONAL_OFFICER','LEAD_AUDITOR'].includes(role) && <button onClick={() => void obligationAction(o.obligation_id, 'CLOSE')} className="mt-2 rounded bg-slate-900 px-2 py-1 text-xs font-semibold text-white">Close verified condition</button>}</div>)}</div>}</div>
          </> : <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center"><FileText className="mx-auto size-8 text-slate-300"/><p className="mt-2 text-sm font-semibold text-slate-700">Select a case to view its dossier</p><p className="mt-1 text-xs text-slate-500">The detailed view includes route snapshot, permitted actions, case events and compliance obligations.</p></div>}
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><Bell className="size-4 text-indigo-600"/><h2 className="font-semibold text-slate-900">In-app notification centre</h2></div>{notifications.length === 0 ? <p className="mt-2 text-xs text-slate-500">No notifications yet. Case events generate persistent in-app alerts for authorised participants.</p> : <div className="mt-3 divide-y divide-slate-100">{notifications.slice(0,8).map((n) => <div key={n.notification_id} className="flex items-start justify-between gap-3 py-2"><div><div className="text-xs font-semibold text-slate-800">{n.title}</div><p className="mt-0.5 text-xs text-slate-600">{n.body}</p><div className="mt-0.5 text-[10px] text-slate-400">{new Date(n.created_at).toLocaleString()}</div></div>{!n.read_at && <button onClick={async () => { await workflowApi.markRead(n.notification_id); await refresh(); }} className="shrink-0 rounded border border-slate-200 px-2 py-1 text-[10px] font-medium text-slate-600">Mark read</button>}</div>)}</div>}</section>
      <DocumentUploadModal open={uploadOpen} onOpenChange={(open) => { setUploadOpen(open); if (!open) { setUploadRequirement(null); setUploadObligationId(null); } }} requirement={uploadRequirement} obligationId={uploadObligationId} onUploadSuccess={handleEvidenceUploaded}/>
    </div>
  );
}
