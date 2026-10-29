import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bell, Clock3, FileText, RefreshCw, Search, ShieldCheck, Workflow } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { workflowApi, type WorkflowCase, type WorkflowDetail, type WorkflowNotification } from '@/features/workflow/api';
import { DocumentUploadModal } from '@/components/documents/DocumentUploadModal';
import { documentsApi } from '@/features/documents/api';
import type { ApplicationRequirementItem } from '@/types/application';
import type { DocumentUploadResponse } from '@/types/document';

const stageLabel = (value: string) => value === 'COMMITTEE_PROCEEDINGS' ? 'Standing Hearing Committee (SHC)' : value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());
const dateLabel = (value: string | null) => value ? new Date(value).toLocaleDateString() : 'Not set';
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
  COMMITTEE_SECRETARIAT: { title: 'Standing Hearing Committee secretariat', description: 'Maintain the hearing proceeding record and record the convening and minutes before the next hand-off.' },
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
  const [uploadRequirement, setUploadRequirement] = useState<ApplicationRequirementItem | null>(null);
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
      if (stage === 'EVC_COORDINATION') return ['EVC_SCHEDULED'];
      if (stage === 'EVC_SCHEDULED') return ['EVC_COMPLETED'];
      if (stage === 'EVC_COMPLETED' && requiresCommittee === false) return ['AWAITING_AUTHORITY'];
    }
    if (role === 'EVC_MEMBER' && stage === 'EVC_SCHEDULED') return ['EVC_COMPLETED'];
    if (role === 'COMMITTEE_SECRETARIAT') {
      if (stage === 'EVC_COMPLETED' && requiresCommittee) return ['COMMITTEE_PROCEEDINGS'];
      if (stage === 'COMMITTEE_PROCEEDINGS') return ['AWAITING_AUTHORITY'];
    }
    if (role === 'COMPETENT_AUTHORITY' && stage === 'AWAITING_AUTHORITY') {
      return ['APPROVED', 'APPROVED_WITH_CONDITIONS', 'REJECTED', 'ON_HOLD'];
    }
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

  const recordEvent = async (eventType: string, prompt: string) => {
    if (!selected || note.trim().length < 8) { toast.error(prompt); return; }
    setBusy(true);
    try { await workflowApi.event(selected.workflow_case_id, eventType, note.trim()); setNote(''); setSelected(await workflowApi.detail(selected.workflow_case_id)); await refresh(); toast.success('Timeline event recorded.'); }
    catch (err) { toast.error(err instanceof Error ? err.message : 'Could not record event.'); }
    finally { setBusy(false); }
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
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Case dossier</div><h2 className="mt-1 text-lg font-bold text-slate-900">{selected.application_number}</h2><p className="text-sm text-slate-600">{selected.institution_name} · {selected.process_type}</p></div><span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">{stageLabel(selected.current_stage)}</span></div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs"><div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Route</span><div className="mt-0.5 font-semibold text-slate-800">{selected.route_code}</div></div><div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Regulatory baseline</span><div className="mt-0.5 font-semibold text-slate-800">{selected.regulatory_version}</div></div></div>
              {selected.route_snapshot.route_status === 'MANUAL_CONFIRMATION_REQUIRED' && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">Route confirmation is required: an authorised policy officer must record the applicable category-specific route before this case can progress.</p>}
              {selected.route_snapshot.requires_committee == null && selected.route_snapshot.requires_evc === true && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">EVC completion is recorded here. The approved category-specific route determines whether the Standing Hearing Committee (SHC) stage follows.</p>}
              {role === 'INTAKE_OFFICER' && selected.current_stage === 'SUBMITTED' && selected.assigned_role_code === 'INTAKE_OFFICER' && !selected.assigned_user_id && teamId && <button onClick={() => void assignCase()} disabled={busy} className="mt-3 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Assign to my review team</button>}
              <div className="mt-4 space-y-2"><label className="text-xs font-semibold text-slate-700">Action reason / case note</label><textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Record the reason, instruction or review note..." className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"/>
                <div className="flex flex-wrap gap-2">{nextStages.map((stage) => <button key={stage} onClick={() => void transition(stage)} disabled={busy} className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{stageLabel(stage)}</button>)}</div>
                {role === 'EVC_COORDINATOR' && selected.current_stage === 'EVC_COORDINATION' && <button onClick={() => void recordEvent('EVC_VISIT_SCHEDULED', 'Enter the scheduling note first.')} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700">Record EVC schedule</button>}
                {role === 'EVC_MEMBER' && selected.current_stage === 'EVC_SCHEDULED' && <button onClick={() => void recordEvent('EVC_REPORT_RECORDED', 'Enter the visit report summary first.')} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700">Record EVC report</button>}
                {role === 'COMMITTEE_SECRETARIAT' && selected.current_stage === 'COMMITTEE_PROCEEDINGS' && <div className="flex gap-2"><button onClick={() => void recordEvent('COMMITTEE_CONVENED', 'Enter the SHC convening note first.')} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold">Record SHC convening</button><button onClick={() => void recordEvent('COMMITTEE_MINUTES_RECORDED', 'Enter the SHC minutes reference first.')} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold">Record SHC minutes</button></div>}
              </div>
            </div>

            {role === 'COMPETENT_AUTHORITY' && ['APPROVED_WITH_CONDITIONS', 'OBLIGATION_TRACKING'].includes(selected.current_stage) && <div className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold text-slate-900">Register approval condition</h3><div className="mt-3 grid gap-2"><input value={conditionTitle} onChange={(e) => setConditionTitle(e.target.value)} placeholder="Condition title" className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><textarea value={conditionDescription} onChange={(e) => setConditionDescription(e.target.value)} placeholder="What must the institution do?" rows={2} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><textarea value={conditionSource} onChange={(e) => setConditionSource(e.target.value)} placeholder="Decision / condition source reference" rows={2} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><input type="date" value={conditionDue} onChange={(e) => setConditionDue(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"/><button onClick={() => void createCondition()} disabled={busy} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white">Add condition</button></div></div>}

            {selected.requirements.length > 0 && <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-900">Application evidence checklist</h3><p className="mt-0.5 text-xs text-slate-500">Documents and requirement states linked to this application.</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">{selected.requirements.length} items</span></div><div className="mt-3 divide-y divide-slate-100">{selected.requirements.map((req) => { const canUpload = role === 'INSTITUTION_USER' && ['DRAFT', 'CLARIFICATION_REQUESTED'].includes(selected.current_stage) && req.applicability_status !== 'NOT_APPLICABLE' && req.status !== 'SATISFIED'; return <div key={req.application_requirement_id} className="flex flex-wrap items-center justify-between gap-3 py-2.5"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="font-mono text-[10px] font-semibold text-slate-500">{req.item_code}</span><span className="text-sm font-medium text-slate-800">{req.title}</span></div><p className="mt-0.5 text-[11px] text-slate-500">{stageLabel(req.status)} · {stageLabel(req.applicability_status)}{req.determination_reason ? ` · ${req.determination_reason}` : ''}</p></div>{canUpload && <button onClick={() => { setUploadRequirement(req); setUploadOpen(true); }} className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100">Upload evidence</button>}</div>; })}</div></div>}

            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><Clock3 className="size-4 text-indigo-600"/><h3 className="font-semibold text-slate-900">Evidence-to-resolution timeline</h3></div><div className="mt-3 space-y-3">{selected.events.map((event) => <div key={event.workflow_event_id} className="relative border-l-2 border-indigo-100 pl-3"><div className="text-xs font-semibold text-slate-800">{event.event_type.replace('COMMITTEE_', 'SHC ').replaceAll('_', ' ')}</div><p className="mt-0.5 text-xs text-slate-600">{event.summary}</p><div className="mt-0.5 text-[10px] text-slate-400">{new Date(event.occurred_at).toLocaleString()}</div></div>)}</div></div>

            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><ShieldCheck className="size-4 text-emerald-600"/><h3 className="font-semibold text-slate-900">Compliance obligations</h3></div>{selected.obligations.length === 0 ? <p className="mt-2 text-xs text-slate-500">No post-decision conditions recorded.</p> : <div className="mt-3 space-y-3">{selected.obligations.map((o) => <div key={o.obligation_id} className="rounded-lg border border-slate-100 p-3"><div className="flex items-start justify-between gap-2"><div className="text-sm font-semibold text-slate-800">{o.title}</div><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold">{stageLabel(o.status)}</span></div><p className="mt-1 text-xs text-slate-600">{o.description}</p><p className="mt-1 text-[11px] text-slate-400">Due {dateLabel(o.due_at)} · {o.source_condition}</p>{role === 'INSTITUTION_USER' && ['OPEN','RETURNED'].includes(o.status) && <div className="mt-2 flex gap-2"><input value={evidenceReference} onChange={(e) => setEvidenceReference(e.target.value)} placeholder="Evidence reference" className="min-w-0 flex-1 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"/><button onClick={() => void obligationAction(o.obligation_id, 'EVIDENCE_SUBMITTED', evidenceReference)} className="rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white">Submit</button></div>}{['SCRUTINY_OFFICER','AUDITOR','BUREAU_SUPERVISOR','LEAD_AUDITOR'].includes(role) && ['EVIDENCE_SUBMITTED','UNDER_VERIFICATION'].includes(o.status) && <div className="mt-2 flex gap-2">{o.status === 'EVIDENCE_SUBMITTED' && <button onClick={() => void obligationAction(o.obligation_id, 'START_VERIFICATION')} className="rounded border px-2 py-1 text-xs">Start review</button>}<button onClick={() => void obligationAction(o.obligation_id, 'VERIFY')} className="rounded bg-emerald-600 px-2 py-1 text-xs font-semibold text-white">Verify</button><button onClick={() => void obligationAction(o.obligation_id, 'RETURN')} className="rounded border border-amber-300 px-2 py-1 text-xs">Return</button></div>}{o.status === 'VERIFIED' && ['BUREAU_SUPERVISOR','REGIONAL_OFFICER','LEAD_AUDITOR'].includes(role) && <button onClick={() => void obligationAction(o.obligation_id, 'CLOSE')} className="mt-2 rounded bg-slate-900 px-2 py-1 text-xs font-semibold text-white">Close verified condition</button>}</div>)}</div>}</div>
          </> : <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center"><FileText className="mx-auto size-8 text-slate-300"/><p className="mt-2 text-sm font-semibold text-slate-700">Select a case to view its dossier</p><p className="mt-1 text-xs text-slate-500">The detailed view includes route snapshot, permitted actions, case events and compliance obligations.</p></div>}
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2"><Bell className="size-4 text-indigo-600"/><h2 className="font-semibold text-slate-900">In-app notification centre</h2></div>{notifications.length === 0 ? <p className="mt-2 text-xs text-slate-500">No notifications yet. Case events generate persistent in-app alerts for authorised participants.</p> : <div className="mt-3 divide-y divide-slate-100">{notifications.slice(0,8).map((n) => <div key={n.notification_id} className="flex items-start justify-between gap-3 py-2"><div><div className="text-xs font-semibold text-slate-800">{n.title}</div><p className="mt-0.5 text-xs text-slate-600">{n.body}</p><div className="mt-0.5 text-[10px] text-slate-400">{new Date(n.created_at).toLocaleString()}</div></div>{!n.read_at && <button onClick={async () => { await workflowApi.markRead(n.notification_id); await refresh(); }} className="shrink-0 rounded border border-slate-200 px-2 py-1 text-[10px] font-medium text-slate-600">Mark read</button>}</div>)}</div>}</section>
      <DocumentUploadModal open={uploadOpen} onOpenChange={(open) => { setUploadOpen(open); if (!open) setUploadRequirement(null); }} requirement={uploadRequirement} onUploadSuccess={handleEvidenceUploaded}/>
    </div>
  );
}
