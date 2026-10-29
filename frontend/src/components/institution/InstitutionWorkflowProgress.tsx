import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  FileCheck2,
  ShieldCheck,
  Building2,
  FileText,
  UserCheck,
  Award,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useDemoScenario } from '@/features/demo/demoContext';

export interface WorkflowStep {
  id: number;
  title: string;
  shortTitle: string;
  description: string;
  completedDetail: string;
  status: 'completed' | 'current' | 'pending';
  actionLabel?: string;
  actionRoute?: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const InstitutionWorkflowProgress: React.FC = () => {
  const navigate = useNavigate();
  const { demoState } = useDemoScenario();

  const isRectified =
    demoState.activeRevisionNumber >= 2 ||
    demoState.rectification.status === 'RECTIFICATION_SUBMITTED' ||
    demoState.rectification.status === 'CONCURRED';

  const isConcurred =
    demoState.rectification.status === 'CONCURRED' ||
    demoState.currentStage === 'CONCURRED' ||
    demoState.leadDisposition?.disposition !== null;

  const steps: WorkflowStep[] = [
    {
      id: 1,
      title: 'Application Self-Disclosure',
      shortTitle: 'Self-Disclosure',
      description: 'Institutional baseline declarations for AY 2026-27 filed under AICTE norms.',
      completedDetail: 'Application APP-2026-EOA-0023 registered with initial parameters.',
      status: 'completed',
      icon: Building2,
    },
    {
      id: 2,
      title: 'Evidence Documents Ingest',
      shortTitle: 'Evidence Ingest',
      description: 'Statutory Annexure 2.1 compliance documents uploaded to private evidence vault.',
      completedDetail: 'All primary institutional affidavits and certifications ingested.',
      status: 'completed',
      icon: FileText,
    },
    {
      id: 3,
      title: 'Automated Rule Validation',
      shortTitle: 'Rule Validation',
      description: 'Independent evaluation against 6 authoritative source snapshots.',
      completedDetail: 'Validation Engine executed: 4 Deficient, 3 Unable to Determine.',
      status: 'completed',
      icon: ShieldCheck,
      actionLabel: 'View Initial Results',
      actionRoute: '/institution/reports',
    },
    {
      id: 4,
      title: 'Deficiency Resolution & Rectification',
      shortTitle: 'Rectification',
      description: 'Mandatory structural stability certificate upload for >30-year building structure.',
      completedDetail: 'Revision #2 Ingested: Er. Deshmukh Stability Certificate verified (SHA-256 recorded).',
      status: isRectified ? 'completed' : 'current',
      icon: AlertTriangle,
      actionLabel: isRectified ? 'View Ingested Rev #2' : 'Resolve Deficiency Now',
      actionRoute: '/institution/rectification',
    },
    {
      id: 5,
      title: 'Auditor & Supervisory Review',
      shortTitle: 'Supervisory Review',
      description: 'Verification review and concurrence by Review Team and Lead Auditor.',
      completedDetail: isConcurred
        ? 'Lead Auditor concurred: EOA-SD-04 deficiency resolved.'
        : 'Under active supervisory review with verified replacement evidence.',
      status: isConcurred ? 'completed' : isRectified ? 'current' : 'pending',
      icon: UserCheck,
      actionLabel: 'Check Status',
      actionRoute: '/institution/overview',
    },
    {
      id: 6,
      title: 'Regulatory Council Decision',
      shortTitle: 'Council Decision',
      description: 'Final statutory Extension of Approval determination by AICTE competent authority.',
      completedDetail: 'Recommendation recorded for approval grant.',
      status: isConcurred ? 'current' : 'pending',
      icon: Award,
    },
  ];

  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const progressPercent = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-xs p-5 space-y-5">
      {/* Stepper Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              Regulatory Verification Lifecycle
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              Academic Year 2026-27
            </span>
          </div>
          <h2 className="text-lg font-bold text-foreground mt-1 flex items-center gap-2">
            Application Progress Tracker
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time compliance stages from initial self-disclosure through regulatory determination.
          </p>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-1.5 shrink-0">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={
                isRectified
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold text-xs px-2.5 py-1'
                  : 'bg-amber-50 text-amber-800 border-amber-300 font-semibold text-xs px-2.5 py-1'
              }
            >
              {isRectified
                ? 'Active: Revision #2 (Rectified)'
                : 'Active: Revision #1 (Action Required)'}
            </Badge>
            <span className="text-xs font-bold text-foreground">
              {progressPercent}% Complete
            </span>
          </div>
          <div className="w-48 bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
            <div
              className="bg-emerald-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Steps Visual Chain */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3 pt-1">
        {steps.map((step) => {
          const isCompleted = step.status === 'completed';
          const isCurrent = step.status === 'current';
          const isPending = step.status === 'pending';
          const StepIcon = step.icon;

          return (
            <div
              key={step.id}
              className={`relative rounded-lg p-3.5 flex flex-col justify-between transition-all border ${
                isCompleted
                  ? 'bg-emerald-50/50 border-emerald-300/80 shadow-2xs'
                  : isCurrent
                    ? 'bg-amber-50/60 border-amber-300 shadow-xs ring-2 ring-amber-400/30'
                    : 'bg-slate-50/60 border-slate-200 opacity-70'
              }`}
            >
              {/* Step Top Indicator Row */}
              <div className="flex items-center justify-between gap-1 mb-2">
                <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                  Step 0{step.id}
                </span>

                {/* Status Indicator Icon */}
                {isCompleted && (
                  <div className="flex items-center gap-1 bg-emerald-600 text-white rounded-full px-2 py-0.5 text-[10px] font-bold shadow-xs">
                    <CheckCircle2 className="w-3.5 h-3.5 stroke-[2.5]" />
                    <span>DONE</span>
                  </div>
                )}

                {isCurrent && (
                  <div className="flex items-center gap-1 bg-amber-500 text-white rounded-full px-2 py-0.5 text-[10px] font-bold animate-pulse shadow-xs">
                    <Clock className="w-3 h-3 stroke-[2.5]" />
                    <span>ACTIVE</span>
                  </div>
                )}

                {isPending && (
                  <div className="flex items-center gap-1 bg-slate-200 text-slate-600 rounded-full px-1.5 py-0.5 text-[10px] font-medium">
                    <span>UPCOMING</span>
                  </div>
                )}
              </div>

              {/* Title and Icon */}
              <div className="space-y-1 my-1">
                <div className="flex items-center gap-1.5">
                  <div
                    className={`p-1 rounded-md ${
                      isCompleted
                        ? 'bg-emerald-100 text-emerald-800'
                        : isCurrent
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-200 text-slate-500'
                    }`}
                  >
                    <StepIcon className="w-3.5 h-3.5" />
                  </div>
                  <h3
                    className={`text-xs font-bold leading-tight ${
                      isCompleted
                        ? 'text-emerald-950'
                        : isCurrent
                          ? 'text-amber-950 font-extrabold'
                          : 'text-slate-600'
                    }`}
                  >
                    {step.shortTitle}
                  </h3>
                </div>

                <p
                  className={`text-[11px] leading-relaxed line-clamp-3 ${
                    isCompleted
                      ? 'text-emerald-800'
                      : isCurrent
                        ? 'text-amber-900 font-medium'
                        : 'text-muted-foreground'
                  }`}
                >
                  {isCompleted ? step.completedDetail : step.description}
                </p>
              </div>

              {/* Action Button if actionable */}
              {step.actionLabel && step.actionRoute && (
                <div className="pt-2 mt-2 border-t border-slate-200/60">
                  <Button
                    size="sm"
                    variant={isCompleted ? 'outline' : 'default'}
                    onClick={() => navigate(step.actionRoute!)}
                    className={`w-full h-7 text-[10px] font-semibold px-2 justify-between ${
                      isCompleted
                        ? 'border-emerald-300 text-emerald-900 hover:bg-emerald-100/60'
                        : 'bg-amber-600 hover:bg-amber-700 text-white'
                    }`}
                  >
                    <span>{step.actionLabel}</span>
                    <ArrowRight className="w-3 h-3" />
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Active Stage Callout Banner */}
      <div
        className={`rounded-lg p-3.5 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 border ${
          isRectified
            ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
            : 'bg-amber-50/80 border-amber-200 text-amber-950'
        }`}
      >
        <div className="flex items-center gap-2.5">
          {isRectified ? (
            <div className="p-1.5 rounded-full bg-emerald-600 text-white shrink-0">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          ) : (
            <div className="p-1.5 rounded-full bg-amber-600 text-white shrink-0">
              <AlertTriangle className="w-4 h-4" />
            </div>
          )}
          <div>
            <span className="font-bold">
              {isRectified
                ? 'Current Stage: Step 5: Supervisory Verification (Revision #2 Ingested)'
                : 'Current Stage: Step 4: Regulatory Action Required on EOA-SD-04'}
            </span>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {isRectified
                ? 'Replacement Structural Stability Certificate was successfully ingested. Requirement EOA-SD-04 shifted to SATISFIED. Ready for final committee concurrence.'
                : 'A mandatory Structural Stability Certificate is required for structures exceeding 30 years. Submit replacement documentation to generate Revision #2.'}
            </p>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-2">
          {!isRectified && (
            <Button
              size="sm"
              onClick={() => navigate('/institution/rectification')}
              className="bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs h-8 px-3 shadow-2xs"
            >
              <FileCheck2 className="w-3.5 h-3.5 mr-1.5" />
              Upload Certificate (Rev #2)
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate('/institution/reports')}
            className="border-slate-300 text-slate-700 hover:bg-slate-100 text-xs h-8 px-3"
          >
            <FileText className="w-3.5 h-3.5 mr-1.5" />
            View Compliance Report
          </Button>
        </div>
      </div>
    </div>
  );
};
export default InstitutionWorkflowProgress;
