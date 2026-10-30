import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CalendarClock, FileText, RefreshCw } from 'lucide-react';
import { workflowApi, type WorkflowCase } from '@/features/workflow/api';

const STAGE_LABELS: Record<string, string> = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  INTAKE_REVIEW: 'Initial checks',
  SCRUTINY: 'Application review',
  CLARIFICATION_REQUESTED: 'Waiting for your response',
  RESUBMITTED: 'Updated documents submitted',
  EVC_COORDINATION: 'Visit being arranged',
  EVC_SCHEDULED: 'Visit scheduled',
  EVC_COMPLETED: 'Visit completed',
  COMMITTEE_PROCEEDINGS: 'Committee review',
  AWAITING_AUTHORITY: 'Awaiting decision',
  APPROVED: 'Approved',
  APPROVED_WITH_CONDITIONS: 'Approved with conditions',
  REJECTED: 'Decision recorded',
  ON_HOLD: 'On hold',
  OBLIGATION_TRACKING: 'Conditions follow-up',
  CLOSED: 'Completed',
};

function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] || stage.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (part) => part.toUpperCase());
}

const PROCESS_LABELS: Record<string, string> = {
  EOA_SELF_DISCLOSURE: 'Extension of Approval — self-disclosure',
  INCREASE_INTAKE: 'Increase in intake',
};

function processLabel(value: string): string {
  return PROCESS_LABELS[value] || value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (part) => part.toUpperCase());
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export const InstitutionWorkflowProgress = () => {
  const [applications, setApplications] = useState<WorkflowCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    workflowApi.cases()
      .then((items) => { if (active) setApplications(items); })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load application progress.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const recentApplications = [...applications]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 4);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Latest applications</h2>
          <p className="mt-1 text-xs text-slate-500">Current status and next due date for applications linked to your institution.</p>
        </div>
        <Link to="/institution/activity" className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:text-indigo-900">
          View updates <ArrowRight className="size-3.5"/>
        </Link>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-5 text-sm text-slate-500"><RefreshCw className="size-4 animate-spin"/>Loading application progress…</div>
      ) : error ? (
        <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">{error}</div>
      ) : recentApplications.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center">
          <FileText className="mx-auto size-7 text-slate-300"/>
          <p className="mt-2 text-sm font-semibold text-slate-700">No applications yet</p>
          <p className="mt-1 text-xs text-slate-500">New applications and their latest updates will appear here.</p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
          {recentApplications.map((item) => (
            <div key={item.workflow_case_id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">{item.application_number}</span>
                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-800">{stageLabel(item.current_stage)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{processLabel(item.process_type)} · AY {item.academic_year}</p>
                <p className="mt-1 text-[11px] text-slate-400">Updated {formatDate(item.updated_at)}</p>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-600">
                <CalendarClock className="size-3.5 text-slate-400"/>
                <span>Due {item.due_at ? formatDate(item.due_at) : 'Not set'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};
