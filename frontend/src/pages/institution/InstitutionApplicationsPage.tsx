import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { useAuth } from '@/hooks/useAuth';
import { applicationsApi } from '@/features/applications/api';
import type { ApplicationListItem } from '@/types/application';
import {
  FileText,
  PlusCircle,
  Eye,
  RefreshCw,
  AlertCircle,
  Calendar,
} from 'lucide-react';
import { InstitutionWorkflowProgress } from '@/components/institution/InstitutionWorkflowProgress';

export default function InstitutionApplicationsPage() {
  const navigate = useNavigate();
  const { activeContext } = useAuth();
  const institutionId = activeContext?.institution_id;

  const [applications, setApplications] = useState<ApplicationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApplications = useCallback(async () => {
    if (!institutionId) {
      setError('Institution account context missing.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await applicationsApi.list(institutionId);
      setApplications(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load applications.');
    } finally {
      setLoading(false);
    }
  }, [institutionId]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const hasEoaApplication = applications.some((app) =>
    app.academic_year === '2026-27'
    && app.application_family === 'EXISTING_INSTITUTION'
    && app.process_type === 'EOA_SELF_DISCLOSURE'
  );
  const hasIncreaseIntakeApplication = applications.some((app) =>
    app.academic_year === '2026-27'
    && app.application_family === 'EXISTING_INSTITUTION'
    && app.process_type === 'INCREASE_INTAKE'
  );
  const canCreateApplication = !hasEoaApplication || !hasIncreaseIntakeApplication;

  const processLabels: Record<string, string> = {
    EOA_SELF_DISCLOSURE: 'Extension of Approval — self-disclosure',
    INCREASE_INTAKE: 'Increase in intake',
  };
  const processLabel = (value: string) =>
    processLabels[value] || value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (part) => part.toUpperCase());

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Institutional Applications
            </h1>
            <Badge
              variant="outline"
              className="text-xs font-semibold bg-emerald-50 text-emerald-800 border-emerald-200"
            >
              Institution account
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Application records linked to your authorised institution account.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchApplications}
            disabled={loading}
            className="h-8 text-xs border-slate-200"
          >
            <RefreshCw className={`size-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            size="sm"
            onClick={() => navigate('/institution/applications/new')}
            disabled={loading || !canCreateApplication}
            title={
              !canCreateApplication
                ? 'Both supported application types are already registered for AY 2026–27'
                : 'Create a new application'
            }
            className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs disabled:opacity-50"
          >
            <PlusCircle className="size-3.5 mr-1.5" />
            New Application
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-start gap-3">
          <AlertCircle className="size-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-semibold text-rose-900">Unable to retrieve application records</p>
            <p className="text-rose-700 text-[11px]">{error}</p>
          </div>
          <Button
            size="xs"
            variant="outline"
            onClick={fetchApplications}
            className="text-xs border-rose-200 text-rose-800 hover:bg-rose-100"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Lifecycle Progress Stepper */}
      <InstitutionWorkflowProgress />

      {/* Single Application Notice if already exists */}
      {hasEoaApplication && (
        <div className="p-3.5 rounded-xl border border-indigo-100 bg-indigo-50/60 text-xs text-indigo-900 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="size-4 text-indigo-600 shrink-0" />
            <span>
              <strong>Extension of Approval already registered:</strong> You can still create an Increase in Intake application for AY 2026–27, where applicable.
            </span>
          </div>
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate('/institution/overview')}
            className="text-xs border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-50 shrink-0"
          >
            Go to Active Checklist
          </Button>
        </div>
      )}

      {/* Applications List Card */}
      <Card className="bg-white border-slate-200/90 shadow-2xs">
        <CardHeader className="p-4 sm:p-5 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <CardTitle className="text-base font-semibold text-slate-900">
                Registered Applications
              </CardTitle>
              <CardDescription className="text-xs text-slate-500">
                Application type, academic year, current status and last update
              </CardDescription>
            </div>
            <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              {applications.length} Record{applications.length === 1 ? '' : 's'}
            </span>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-500 space-y-2">
              <RefreshCw className="size-5 text-indigo-600 animate-spin mx-auto opacity-70" />
              <p>Loading application records...</p>
            </div>
          ) : applications.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <div className="size-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <FileText className="size-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-slate-800">
                  No Applications Initiated
                </h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Your institution does not yet have an application for AY 2026–27. Start an Extension of Approval or Increase in Intake application to continue.
                </p>
              </div>
              <div className="pt-2">
                <Button
                  size="sm"
                  disabled={!canCreateApplication}
                  onClick={() => navigate('/institution/applications/new')}
                  className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  <PlusCircle className="size-3.5 mr-1.5" />
                  Initiate AY 2026–27 Application
                </Button>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50/70 border-b border-slate-100 text-slate-600 uppercase tracking-wider text-[10px] font-semibold">
                  <tr>
                    <th className="py-3 px-4">Application No.</th>
                    <th className="py-3 px-4">Academic Year</th>
                    <th className="py-3 px-4">Type / Family</th>
                    <th className="py-3 px-4">Revision</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Last Updated</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {applications.map((app) => (
                    <tr
                      key={app.application_id}
                      className="hover:bg-slate-50/60 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                        {app.application_number}
                      </td>
                      <td className="py-3.5 px-4 text-slate-700 font-medium">
                        {app.academic_year}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        {processLabel(app.process_type)}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        Rev-0{app.current_revision_number ?? 1}
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={app.status} />
                      </td>
                      <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                        {new Date(app.updated_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => navigate('/institution/overview')}
                          className="h-7 text-xs border-slate-200 text-slate-700 hover:text-indigo-600 hover:bg-slate-50 gap-1.5"
                        >
                          <Eye className="size-3" />
                          <span>View Checklist</span>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
