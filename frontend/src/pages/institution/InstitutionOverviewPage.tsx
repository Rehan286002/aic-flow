import { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { useAuth } from '@/hooks/useAuth';
import { applicationsApi } from '@/features/applications/api';
import type {
  ApplicationDetail,
  ApplicationRequirementItem,
} from '@/types/application';
import {
  AlertTriangle,
  Calendar,
  ShieldCheck,
  FileText,
  Eye,
  Info,
  CheckCircle2,
  Clock,
  RefreshCw,
  PlusCircle,
  SlidersHorizontal,
  MinusCircle,
  UploadCloud,
  History,
} from 'lucide-react';
import { toast } from 'sonner';
import { DocumentUploadModal } from '@/components/documents/DocumentUploadModal';
import { DocumentVersionHistoryModal } from '@/components/documents/DocumentVersionHistoryModal';
import { InstitutionWorkflowProgress } from '@/components/institution/InstitutionWorkflowProgress';

export default function InstitutionOverviewPage() {
  const navigate = useNavigate();
  const { activeContext } = useAuth();
  const institutionId = activeContext?.institution_id;

  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [hasOtherApplications, setHasOtherApplications] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Requirement inspection dialog
  const [selectedReq, setSelectedReq] = useState<ApplicationRequirementItem | null>(null);

  // Document upload and version history dialogs
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedReqForUpload, setSelectedReqForUpload] = useState<ApplicationRequirementItem | null>(null);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [selectedReqForHistory, setSelectedReqForHistory] = useState<ApplicationRequirementItem | null>(null);

  // Edit declarations dialog
  const [declarationsOpen, setDeclarationsOpen] = useState(false);
  const [completionDate, setCompletionDate] = useState<string>('');
  const [paymentStatus, setPaymentStatus] = useState<'true' | 'false' | 'pending'>('pending');
  const [remarks, setRemarks] = useState<string>('');
  const [savingDeclarations, setSavingDeclarations] = useState(false);

  const loadApplication = useCallback(async (isRefresh = false) => {
    if (!institutionId) {
      setError('Institution account context missing.');
      setLoading(false);
      return;
    }

    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const list = await applicationsApi.list(institutionId);
      const eoaApplication = list.find((item) => item.process_type === 'EOA_SELF_DISCLOSURE');
      setHasOtherApplications(list.some((item) => item.process_type !== 'EOA_SELF_DISCLOSURE'));
      if (eoaApplication) {
        const detail = await applicationsApi.getDetail(institutionId, eoaApplication.application_id);
        setApplication(detail);

        // Prepopulate the declarations for the selected EoA application.
        const decls = detail.current_revision.declarations || {};
        setCompletionDate(decls.completion_certificate_issue_date || '');
        if (decls.payment_applicable === true) setPaymentStatus('true');
        else if (decls.payment_applicable === false) setPaymentStatus('false');
        else setPaymentStatus('pending');
        setRemarks(decls.application_remarks || '');
      } else {
        setApplication(null);
        setCompletionDate('');
        setPaymentStatus('pending');
        setRemarks('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load application data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [institutionId]);

  useEffect(() => {
    loadApplication();
  }, [loadApplication]);

  // Derived metrics from live requirements
  const metrics = useMemo(() => {
    if (!application?.requirements) {
      return { total: 0, applicable: 0, notApplicable: 0, pendingDet: 0, satisfied: 0 };
    }
    const reqs = application.requirements;
    return {
      total: reqs.length,
      applicable: reqs.filter((r) => r.applicability_status === 'APPLICABLE').length,
      notApplicable: reqs.filter((r) => r.applicability_status === 'NOT_APPLICABLE').length,
      pendingDet: reqs.filter((r) => r.applicability_status === 'PENDING_DETERMINATION').length,
      satisfied: reqs.filter((r) => r.status === 'SATISFIED').length,
    };
  }, [application]);

  const handleSaveDeclarations = async () => {
    if (!institutionId || !application) return;

    setSavingDeclarations(true);
    let paymentApplicable: boolean | null = null;
    if (paymentStatus === 'true') paymentApplicable = true;
    else if (paymentStatus === 'false') paymentApplicable = false;

    try {
      const updated = await applicationsApi.updateDraft(institutionId, application.application_id, {
        completion_certificate_issue_date: completionDate.trim() ? completionDate.trim() : null,
        payment_applicable: paymentApplicable,
        application_remarks: remarks.trim() ? remarks.trim() : null,
      });

      setApplication(updated);
      setDeclarationsOpen(false);
      toast.success('Declarations Updated', {
        description: 'Checklist applicability rules have been re-evaluated live by the verification service.',
      });
    } catch (err) {
      toast.error('Update Failed', {
        description: err instanceof Error ? err.message : 'Failed to update declarations.',
      });
    } finally {
      setSavingDeclarations(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-slate-500 space-y-2">
        <RefreshCw className="size-6 text-indigo-600 animate-spin mx-auto opacity-70" />
        <p>Loading institutional verification overview...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Institution Portal Overview
            </h1>
            <Badge
              variant="outline"
              className="text-xs font-semibold bg-emerald-50 text-emerald-800 border-emerald-200"
            >
              Authorized Representative
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Applications and supporting documents for your authorised institution account.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadApplication(true)}
            disabled={refreshing}
            className="h-8 text-xs border-slate-200"
          >
            <RefreshCw className={`size-3.5 mr-1.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {application && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeclarationsOpen(true)}
              className="h-8 text-xs border-indigo-200 text-indigo-700 bg-indigo-50/50 hover:bg-indigo-100"
            >
              <SlidersHorizontal className="size-3.5 mr-1.5" />
              Update Declarations
            </Button>
          )}

          {!application && (
            <Button
              size="sm"
              onClick={() => navigate('/institution/applications/new')}
              className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs"
            >
              <PlusCircle className="size-3.5 mr-1.5" />
              New Application
            </Button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-start gap-3">
          <AlertTriangle className="size-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-semibold text-rose-900">Unable to load portal records</p>
            <p className="text-rose-700 text-[11px]">{error}</p>
          </div>
        </div>
      )}

      {/* Lifecycle Progress Stepper */}
      <InstitutionWorkflowProgress />

      {/* Empty State when no application has been created */}
      {!application && (
        <Card className="bg-white border-slate-200/90 shadow-2xs">
          <CardContent className="p-10 text-center space-y-4">
            <div className="size-14 rounded-full bg-indigo-50 flex items-center justify-center mx-auto text-indigo-600">
              <FileText className="size-7" />
            </div>
            <div className="space-y-1.5 max-w-lg mx-auto">
              <h2 className="text-base font-semibold text-slate-900">
                No Active AY 2026–27 Extension of Approval Application
              </h2>
              <p className="text-xs text-slate-500 leading-relaxed">
                {hasOtherApplications
                  ? 'You have another application type for this academic year. Open My Applications to track it, or start an Extension of Approval application to access its separate document checklist.'
                  : 'Your institution does not have an Extension of Approval application for this academic year. Start one to view its document checklist and submit supporting evidence.'}
              </p>
            </div>
            <div className="pt-2">
              <Button
                size="sm"
                onClick={() => navigate('/institution/applications/new')}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                <PlusCircle className="size-3.5 mr-1.5" />
                Initiate AY 2026–27 Application
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Application Card */}
      {application && (
        <Card className="bg-white border-slate-200/90 shadow-2xs">
          <CardHeader className="p-4 sm:p-5 border-b border-slate-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <CardTitle className="text-base font-semibold text-slate-900">
                    Extension of Approval (EoA) Self-Disclosure
                  </CardTitle>
                  <StatusBadge status={application.status} />
                </div>
                <CardDescription className="text-xs text-slate-500 font-mono">
                  Application ID: {application.application_number} • Revision: Rev-0
                  {application.current_revision.revision_number} • Academic Year{' '}
                  {application.academic_year}
                </CardDescription>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200/60 shrink-0">
                <Calendar className="size-3.5 text-slate-400" />
                <span>
                  Created:{' '}
                  {new Date(application.created_at).toLocaleDateString('en-IN', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-4 sm:p-5 space-y-5">
            {/* Annexure 2.1 Checklist Header & Calculated Summary Metrics */}
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="space-y-0.5">
                  <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                    <ShieldCheck className="size-4 text-indigo-600" />
                    <span>Annexure 2.1 Evidence Checklist Status</span>
                  </h3>
                  <p className="text-xs text-slate-500">
                    Regulatory compliance self-disclosure requirements across all 7 statutory evidence categories
                  </p>
                </div>

                {/* Dynamic Summary Counts Badge Group */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Badge
                    variant="outline"
                    className="text-xs h-6 px-2 bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold gap-1"
                  >
                    <CheckCircle2 className="size-3 text-emerald-600" />
                    <span>{metrics.applicable} Applicable</span>
                  </Badge>

                  {metrics.notApplicable > 0 && (
                    <Badge
                      variant="outline"
                      className="text-xs h-6 px-2 bg-slate-100 text-slate-700 border-slate-200 font-medium gap-1"
                    >
                      <MinusCircle className="size-3 text-slate-400" />
                      <span>{metrics.notApplicable} Not Applicable</span>
                    </Badge>
                  )}

                  {metrics.pendingDet > 0 && (
                    <Badge
                      variant="outline"
                      className="text-xs h-6 px-2 bg-amber-50 text-amber-800 border-amber-300 font-semibold gap-1"
                    >
                      <Clock className="size-3 text-amber-600" />
                      <span>{metrics.pendingDet} Pending Determination</span>
                    </Badge>
                  )}

                  <span className="text-xs font-mono text-slate-400 pl-1">
                    ({metrics.total} Total)
                  </span>
                </div>
              </div>

              {/* Checklist Rows List */}
              <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden bg-white shadow-2xs">
                {application.requirements.map((req) => {
                  const isNotApplicable = req.applicability_status === 'NOT_APPLICABLE';
                  const isPendingDet = req.applicability_status === 'PENDING_DETERMINATION';

                  return (
                    <div
                      key={req.application_requirement_id}
                      className={`p-3.5 sm:p-4 transition-colors ${
                        isNotApplicable
                          ? 'bg-slate-50/40 hover:bg-slate-50/70'
                          : isPendingDet
                          ? 'bg-amber-50/20 hover:bg-amber-50/40'
                          : 'bg-white hover:bg-slate-50/40'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        {/* Left: Code, Name, Applicability, Description, and Determination Detail */}
                        <div className="space-y-1.5 flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                              {req.item_code}
                            </span>
                            <span className="font-semibold text-slate-900 text-xs sm:text-sm">
                              {req.title}
                            </span>

                            {isNotApplicable ? (
                              <Badge
                                variant="outline"
                                className="text-[10px] h-4.5 px-1.5 bg-slate-100 text-slate-600 border-slate-200"
                              >
                                Condition Not Applicable
                              </Badge>
                            ) : isPendingDet ? (
                              <Badge
                                variant="outline"
                                className="text-[10px] h-4.5 px-1.5 bg-amber-50 text-amber-800 border-amber-300 font-medium"
                              >
                                Pending Determination
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="text-[10px] h-4.5 px-1.5 bg-emerald-50 text-emerald-800 border-emerald-200 font-medium"
                              >
                                Applicable Requirement
                              </Badge>
                            )}
                          </div>

                          <p className="text-xs text-slate-600 leading-relaxed">
                            {req.description}
                          </p>

                          {/* Determination Reason / Expected Document Tag */}
                          <div className="flex items-center gap-2 text-[11px] text-slate-500 pt-0.5 flex-wrap">
                            {req.expected_document_type_code && (
                              <span className="font-mono text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200 flex items-center gap-1">
                                <FileText className="size-3 text-slate-400" />
                                Expected: {req.expected_document_type_code}
                              </span>
                            )}
                            {req.determination_reason && (
                              <span className="text-slate-600 italic">
                                Determination: {req.determination_reason}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Right: Submission Status Badge & Action */}
                        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 shrink-0 pt-1 sm:pt-0">
                          <StatusBadge status={req.status} />

                          <div className="flex items-center gap-1.5 flex-wrap justify-end">
                            {req.applicability_status === 'APPLICABLE' && (
                              <>
                                <Button
                                  variant={req.status === 'UPLOADED' ? 'outline' : 'default'}
                                  size="xs"
                                  onClick={() => {
                                    setSelectedReqForUpload(req);
                                    setUploadModalOpen(true);
                                  }}
                                  className={`h-7 text-xs px-2.5 gap-1 shadow-2xs ${
                                    req.status === 'UPLOADED'
                                      ? 'border-indigo-200 text-indigo-700 hover:bg-indigo-50'
                                      : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                  }`}
                                >
                                  <UploadCloud className="size-3" />
                                  <span>{req.status === 'UPLOADED' ? 'Replace' : 'Upload'}</span>
                                </Button>

                                <Button
                                  variant="outline"
                                  size="xs"
                                  onClick={() => {
                                    setSelectedReqForHistory(req);
                                    setHistoryModalOpen(true);
                                  }}
                                  className="h-7 text-xs px-2 gap-1 border-slate-200 text-slate-700 hover:text-indigo-600 hover:bg-slate-50 shadow-2xs"
                                >
                                  <History className="size-3" />
                                  <span>History</span>
                                </Button>
                              </>
                            )}

                            <Button
                              variant="outline"
                              size="xs"
                              onClick={() => setSelectedReq(req)}
                              className="h-7 text-xs px-2 gap-1 border-slate-200 text-slate-600 hover:text-indigo-600 hover:bg-slate-50"
                            >
                              <Eye className="size-3" />
                              <span>Details</span>
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Applicant Regulatory Boundary Notice */}
      <div className="p-4 rounded-xl border border-slate-200 bg-white text-xs text-slate-600 shadow-2xs space-y-1">
        <div className="flex items-center gap-1.5 font-semibold text-slate-800">
          <Info className="size-4 text-indigo-600 shrink-0" />
          <span>Regulatory Security & Applicant Privacy Boundary:</span>
        </div>
        <p className="leading-relaxed text-[11px] text-slate-500 pl-5">
          Under AICTE regulatory guidelines and AIC-Flow data isolation boundaries, applicant
          portal displays are restricted to formal deficiency instructions, requirement compliance
          statuses, and submission receipts. Internal auditor deliberation notes, anomaly severity
          ratings, and investigation logs remain private to authorized regulatory review personnel.
          Final statutory determinations remain with competent AICTE authorities.
        </p>
      </div>

      {/* Requirement Details Dialog */}
      <Dialog open={!!selectedReq} onOpenChange={(open) => !open && setSelectedReq(null)}>
        <DialogContent className="max-w-lg text-slate-900">
          <DialogHeader>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-200">
                    {selectedReq?.item_code}
                  </span>
                  <DialogTitle className="text-sm font-semibold">
                    {selectedReq?.title}
                  </DialogTitle>
                </div>
                <DialogDescription className="text-xs text-slate-500">
                  Application: {application?.application_number} • Your institution
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedReq && (
            <div className="space-y-3 py-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                  Annexure 2.1 Specification:
                </span>
                <p className="text-slate-700 leading-relaxed">{selectedReq.description}</p>
              </div>

              <div className="p-3 rounded-lg border border-slate-200 space-y-1 bg-white">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                  Expected Evidence Document Type:
                </span>
                <span className="font-mono text-xs text-slate-800 font-semibold">
                  {selectedReq.expected_document_type_code || 'Not defined'}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-indigo-100 bg-indigo-50/50 text-[11px] text-slate-700 space-y-1">
                <span className="font-semibold text-indigo-900 block">
                  Applicability Determination:
                </span>
                <p>
                  Status:{' '}
                  <strong>{selectedReq.applicability_status.replace(/_/g, ' ')}</strong>
                </p>
                {selectedReq.determination_reason && (
                  <p className="text-slate-600 italic">
                    Reason: {selectedReq.determination_reason}
                  </p>
                )}
              </div>
            </div>
          )}

          <DialogFooter className="border-t border-slate-100 pt-3 flex flex-row items-center justify-between sm:justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedReq(null)}
              className="text-xs border-slate-200"
            >
              Close
            </Button>

            {selectedReq && selectedReq.applicability_status === 'APPLICABLE' && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const r = selectedReq;
                    setSelectedReq(null);
                    setSelectedReqForHistory(r);
                    setHistoryModalOpen(true);
                  }}
                  className="text-xs border-slate-200 text-slate-700 gap-1.5"
                >
                  <History className="size-3.5" />
                  <span>Version History</span>
                </Button>

                <Button
                  size="sm"
                  onClick={() => {
                    const r = selectedReq;
                    setSelectedReq(null);
                    setSelectedReqForUpload(r);
                    setUploadModalOpen(true);
                  }}
                  className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5"
                >
                  <UploadCloud className="size-3.5" />
                  <span>{selectedReq.status === 'UPLOADED' ? 'Replace' : 'Upload'}</span>
                </Button>
              </div>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Self-Disclosure Declarations Dialog */}
      <Dialog open={declarationsOpen} onOpenChange={setDeclarationsOpen}>
        <DialogContent className="max-w-lg text-slate-900">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Update Self-Disclosure Declarations
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Modifying baseline declarations triggers service-derived recalculation of Annexure
              2.1 requirement applicability rules.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            {/* Completion Certificate Date */}
            <div className="space-y-2 p-3 rounded-lg bg-slate-50 border border-slate-200">
              <Label htmlFor="editCompletionDate" className="text-xs font-semibold text-slate-800">
                Building Completion Certificate Issue Date (EOA-SD-04)
              </Label>
              <Input
                id="editCompletionDate"
                type="date"
                value={completionDate}
                onChange={(e) => setCompletionDate(e.target.value)}
                className="bg-white text-xs border-slate-300 font-mono"
              />
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Evaluated against prototype reference date <code>2026-07-01</code> (evaluation baseline, not a statutory filing deadline). If &gt;30 years elapsed
                &rarr; Applicable. If &le;30 years &rarr; Not Applicable. If empty &rarr; Pending
                Determination.
              </p>
              {/* Quick Fill Test Presets */}
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  onClick={() => setCompletionDate('1990-05-15')}
                  className="text-[10px] h-5 px-1.5 border-slate-200 text-slate-700"
                >
                  1990-05-15 (&gt;30y)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  onClick={() => setCompletionDate('1996-07-01')}
                  className="text-[10px] h-5 px-1.5 border-slate-200 text-slate-700"
                >
                  1996-07-01 (=30y)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  onClick={() => setCompletionDate('2008-01-10')}
                  className="text-[10px] h-5 px-1.5 border-slate-200 text-slate-700"
                >
                  2008-01-10 (&lt;30y)
                </Button>
                {completionDate && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="xs"
                    onClick={() => setCompletionDate('')}
                    className="text-[10px] h-5 px-1.5 text-rose-600"
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>

            {/* Payment Declaration */}
            <div className="space-y-2 p-3 rounded-lg bg-slate-50 border border-slate-200">
              <Label className="text-xs font-semibold text-slate-800">
                Payment Receipt Declaration (EOA-SD-02)
              </Label>
              <RadioGroup
                value={paymentStatus}
                onValueChange={(val) => setPaymentStatus(val as 'true' | 'false' | 'pending')}
                className="space-y-1.5"
              >
                <div
                  className="flex items-center space-x-2 cursor-pointer"
                  onClick={() => setPaymentStatus('true')}
                >
                  <RadioGroupItem value="true" id="edit-pay-true" />
                  <Label htmlFor="edit-pay-true" className="text-xs font-normal cursor-pointer">
                    Applicable (fee paid / receipt required)
                  </Label>
                </div>
                <div
                  className="flex items-center space-x-2 cursor-pointer"
                  onClick={() => setPaymentStatus('false')}
                >
                  <RadioGroupItem value="false" id="edit-pay-false" />
                  <Label htmlFor="edit-pay-false" className="text-xs font-normal cursor-pointer">
                    Not Applicable (fee exempt / zero fee)
                  </Label>
                </div>
                <div
                  className="flex items-center space-x-2 cursor-pointer"
                  onClick={() => setPaymentStatus('pending')}
                >
                  <RadioGroupItem value="pending" id="edit-pay-pending" />
                  <Label htmlFor="edit-pay-pending" className="text-xs font-normal cursor-pointer">
                    Pending Determination (to be determined)
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Remarks */}
            <div className="space-y-1.5">
              <Label htmlFor="editRemarks" className="text-xs font-semibold text-slate-700">
                Application Remarks
              </Label>
              <Textarea
                id="editRemarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={2}
                className="text-xs resize-none border-slate-300"
              />
            </div>
          </div>

          <DialogFooter className="border-t border-slate-100 pt-3 gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeclarationsOpen(false)}
              disabled={savingDeclarations}
              className="text-xs border-slate-200"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSaveDeclarations}
              disabled={savingDeclarations}
              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {savingDeclarations ? 'Recalculating...' : 'Save & Recalculate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Upload Modal */}
      <DocumentUploadModal
        open={uploadModalOpen}
        onOpenChange={(open) => {
          setUploadModalOpen(open);
          if (!open) setSelectedReqForUpload(null);
        }}
        requirement={selectedReqForUpload}
        onUploadSuccess={() => {
          loadApplication(true);
        }}
      />

      {/* Document Version History Modal */}
      <DocumentVersionHistoryModal
        open={historyModalOpen}
        onOpenChange={(open) => {
          setHistoryModalOpen(open);
          if (!open) setSelectedReqForHistory(null);
        }}
        requirement={selectedReqForHistory}
        onOpenUpload={(req) => {
          setSelectedReqForUpload(req);
          setUploadModalOpen(true);
        }}
      />
    </div>
  );
}
