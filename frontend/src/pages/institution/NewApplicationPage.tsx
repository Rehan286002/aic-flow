import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { useAuth } from '@/hooks/useAuth';
import { applicationsApi } from '@/features/applications/api';
import { ApiError } from '@/lib/api';
import {
  FilePlus,
  ArrowLeft,
  Calendar,
  AlertTriangle,
  Info,
  ShieldCheck,
} from 'lucide-react';
import { toast } from 'sonner';

export default function NewApplicationPage() {
  const navigate = useNavigate();
  const { activeContext } = useAuth();
  const institutionId = activeContext?.institution_id;

  const [academicYear] = useState('2026-27');
  const [processType, setProcessType] = useState<'EOA_SELF_DISCLOSURE' | 'INCREASE_INTAKE'>('EOA_SELF_DISCLOSURE');
  const [existingProcessTypes, setExistingProcessTypes] = useState<string[]>([]);
  const [checkingExisting, setCheckingExisting] = useState(true);
  const [applicationFamily] = useState<'EXISTING_INSTITUTION'>('EXISTING_INSTITUTION');
  const [completionDate, setCompletionDate] = useState<string>('');
  const [paymentStatus, setPaymentStatus] = useState<'true' | 'false' | 'pending'>('pending');
  const [remarks, setRemarks] = useState<string>('');

  const [submitting, setSubmitting] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!institutionId) {
      setCheckingExisting(false);
      return;
    }
    applicationsApi.list(institutionId)
      .then((items) => {
        if (!active) return;
        const existing = items
          .filter((item) => item.academic_year === academicYear)
          .map((item) => item.process_type);
        setExistingProcessTypes(existing);
        setProcessType((current) => {
          if (!existing.includes(current)) return current;
          return existing.includes('EOA_SELF_DISCLOSURE') ? 'INCREASE_INTAKE' : 'EOA_SELF_DISCLOSURE';
        });
      })
      .catch(() => {
        if (active) setGeneralError('Could not check existing applications. The server will still check for duplicate application types when you submit.');
      })
      .finally(() => { if (active) setCheckingExisting(false); });
    return () => { active = false; };
  }, [institutionId, academicYear]);

  const selectedTypeExists = existingProcessTypes.includes(processType);
  const bothTypesExist = existingProcessTypes.includes('EOA_SELF_DISCLOSURE')
    && existingProcessTypes.includes('INCREASE_INTAKE');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institutionId) {
      setGeneralError('Institution context missing. Please re-authenticate.');
      return;
    }

    if (selectedTypeExists) {
      setConflictError('An application of this type is already registered for AY ' + academicYear + '. Choose the other available application type.');
      return;
    }

    setSubmitting(true);
    setConflictError(null);
    setGeneralError(null);

    let paymentApplicable: boolean | null = null;
    if (paymentStatus === 'true') paymentApplicable = true;
    else if (paymentStatus === 'false') paymentApplicable = false;

    try {
      const createdApp = await applicationsApi.createDraft(institutionId, {
        academic_year: academicYear,
        process_type: processType,
        application_family: applicationFamily,
        completion_certificate_issue_date: completionDate.trim() ? completionDate.trim() : null,
        payment_applicable: paymentApplicable,
        application_remarks: remarks.trim() ? remarks.trim() : null,
      });

      toast.success('Application Draft Created', {
        description: `Application ${createdApp.application_number} created and added to the approval workflow.`,
      });
      navigate('/institution/overview');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflictError(
          err.detail ||
            'An application for AY 2026–27 already exists for this institution. Only one application of this category is permitted for the academic year.'
        );
      } else {
        setGeneralError(err instanceof Error ? err.message : 'Failed to create application draft.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="xs"
              onClick={() => navigate('/institution/applications')}
              className="text-xs text-slate-600 hover:text-slate-900 -ml-2"
            >
              <ArrowLeft className="size-3.5 mr-1" />
              Applications
            </Button>
            <span className="text-slate-300">/</span>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
              Create application
            </h1>
          </div>
          <p className="text-xs text-slate-500">
            Your authorised institution workspace • Academic Year 2026–27
          </p>
        </div>

        <Badge
          variant="outline"
          className="text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200"
        >
          Approval Application
        </Badge>
      </div>

      {/* 409 Conflict Banner if already exists */}
      {conflictError && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900 shadow-2xs space-y-2">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="size-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold text-amber-950 text-sm">Application Already Exists</p>
              <p className="text-amber-800 leading-relaxed text-[11px]">{conflictError}</p>
            </div>
          </div>
          <div className="pt-1 flex gap-2">
            <Button
              size="xs"
              onClick={() => navigate('/institution/overview')}
              className="text-xs bg-amber-800 hover:bg-amber-900 text-white"
            >
              Go to Active Application Overview
            </Button>
            <Button
              size="xs"
              variant="outline"
              onClick={() => navigate('/institution/applications')}
              className="text-xs border-amber-300 text-amber-900"
            >
              View Application Records
            </Button>
          </div>
        </div>
      )}

      {/* General Error Banner */}
      {generalError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-start gap-3">
          <AlertTriangle className="size-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-semibold text-rose-900">Unable to Submit Application Draft</p>
            <p className="text-rose-700 text-[11px]">{generalError}</p>
          </div>
        </div>
      )}

      {/* Form Card */}
      <form onSubmit={handleSubmit}>
        <Card className="bg-white border-slate-200/90 shadow-2xs">
          <CardHeader className="p-4 sm:p-5 border-b border-slate-100">
            <CardTitle className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <FilePlus className="size-4 text-indigo-600" />
              <span>Application details</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Choose the application type. The next steps depend on the selected type and the current approved processing rules.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-4 sm:p-5 space-y-6">
            <div className="space-y-2">
              <Label className="text-xs font-semibold text-slate-700">Application type</Label>
              <RadioGroup
                value={processType}
                onValueChange={(value) => setProcessType(value as 'EOA_SELF_DISCLOSURE' | 'INCREASE_INTAKE')}
                className="grid grid-cols-1 sm:grid-cols-2 gap-2"
              >
                <div className={`rounded-lg border p-3 ${processType === 'EOA_SELF_DISCLOSURE' ? 'border-indigo-300 bg-indigo-50/70' : 'border-slate-200 bg-white'}`}>
                  <div className="flex items-start gap-2">
                    <RadioGroupItem value="EOA_SELF_DISCLOSURE" id="process-eoa" disabled={existingProcessTypes.includes('EOA_SELF_DISCLOSURE')} />
                    <Label htmlFor="process-eoa" className="cursor-pointer space-y-1">
                      <span className="block text-xs font-semibold text-slate-900">Extension of Approval — Self Disclosure</span>
                      <span className="block text-[10px] font-normal leading-relaxed text-slate-500">{existingProcessTypes.includes('EOA_SELF_DISCLOSURE') ? 'Already registered for this academic year.' : 'For the annual self-disclosure and supporting documents.'}</span>
                    </Label>
                  </div>
                </div>
                <div className={`rounded-lg border p-3 ${processType === 'INCREASE_INTAKE' ? 'border-indigo-300 bg-indigo-50/70' : 'border-slate-200 bg-white'}`}>
                  <div className="flex items-start gap-2">
                    <RadioGroupItem value="INCREASE_INTAKE" id="process-increase" disabled={existingProcessTypes.includes('INCREASE_INTAKE')} />
                    <Label htmlFor="process-increase" className="cursor-pointer space-y-1">
                      <span className="block text-xs font-semibold text-slate-900">Increase in Intake</span>
                      <span className="block text-[10px] font-normal leading-relaxed text-slate-500">{existingProcessTypes.includes('INCREASE_INTAKE') ? 'Already registered for this academic year.' : 'For a request to increase approved student intake.'}</span>
                    </Label>
                  </div>
                </div>
              </RadioGroup>
              <p className="text-[11px] text-slate-500">You can register each supported application type once per academic year. An application type that is already registered cannot be submitted again.</p>
              {checkingExisting && <p className="text-[11px] text-indigo-700">Checking applications already registered for this year…</p>}
              {bothTypesExist && <p className="text-[11px] text-amber-800">Both supported application types are already registered for this academic year.</p>}
            </div>
            {/* Core Parameters Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-slate-700">Academic Year</Label>
                <Input
                  value={academicYear}
                  disabled
                  className="bg-slate-50 text-xs font-mono text-slate-700 border-slate-200 cursor-not-allowed"
                />
                <p className="text-[11px] text-slate-400">
                  Current application year.
                </p>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-slate-700">Institution type</Label>
                <Input
                  value="Existing technical institution"
                  disabled
                  className="bg-slate-50 text-xs font-mono text-slate-700 border-slate-200 cursor-not-allowed"
                />
                <p className="text-[11px] text-slate-400">
Application family for an existing technical institution.
                </p>
              </div>
            </div>

            {processType === 'EOA_SELF_DISCLOSURE' && (<>
            {/* Completion Certificate Date Declaration */}
            <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/50 space-y-3">
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label
                    htmlFor="completionDate"
                    className="text-xs font-bold text-slate-900 flex items-center gap-1.5"
                  >
                    <Calendar className="size-3.5 text-indigo-600" />
                    <span>Building Completion Certificate Issue Date</span>
                  </Label>
                  <span className="text-[10px] text-slate-500 font-mono">Optional on Draft</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Under the current demonstration checklist, a Structural Stability Certificate
                  is required when the building completion certificate is more than 30 years old.
                  The example assessment date for this academic year is 1 July 2026; this is not an
                  official filing deadline. If the date is not known yet, leave it blank and the
                  checklist will show that it still needs to be determined.
                </p>
              </div>

              <div className="max-w-xs">
                <Input
                  id="completionDate"
                  type="date"
                  value={completionDate}
                  onChange={(e) => setCompletionDate(e.target.value)}
                  className="bg-white text-xs border-slate-300 font-mono"
                />
              </div>

            </div>

            </>)}
            {processType === 'EOA_SELF_DISCLOSURE' && (<>
            {/* Payment Receipt Applicable Declaration */}
            <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/50 space-y-3">
              <div className="space-y-1">
                <Label className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  <ShieldCheck className="size-3.5 text-indigo-600" />
                  <span>Web-portal payment receipt</span>
                </Label>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  <strong>Annexure 2.1, Clause 2 rule:</strong> Copy of AICTE Web-Portal payment
                  receipt, <em>if any</em>. Declare whether portal payment is applicable for this
                  self-disclosure declaration.
                </p>
              </div>

              <RadioGroup
                value={paymentStatus}
                onValueChange={(val) => setPaymentStatus(val as 'true' | 'false' | 'pending')}
                className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1"
              >
                <div
                  className={`p-3 rounded-lg border flex items-center space-x-2.5 cursor-pointer transition-colors ${
                    paymentStatus === 'true'
                      ? 'bg-indigo-50/80 border-indigo-300'
                      : 'bg-white border-slate-200 hover:bg-slate-50'
                  }`}
                  onClick={() => setPaymentStatus('true')}
                >
                  <RadioGroupItem value="true" id="pay-true" />
                  <Label htmlFor="pay-true" className="text-xs font-medium cursor-pointer">
                    <span className="block text-slate-900 font-semibold">Payment Applicable</span>
                    <span className="text-[10px] text-slate-500">Requires EOA-SD-02 receipt</span>
                  </Label>
                </div>

                <div
                  className={`p-3 rounded-lg border flex items-center space-x-2.5 cursor-pointer transition-colors ${
                    paymentStatus === 'false'
                      ? 'bg-slate-100 border-slate-300'
                      : 'bg-white border-slate-200 hover:bg-slate-50'
                  }`}
                  onClick={() => setPaymentStatus('false')}
                >
                  <RadioGroupItem value="false" id="pay-false" />
                  <Label htmlFor="pay-false" className="text-xs font-medium cursor-pointer">
                    <span className="block text-slate-900 font-semibold">Exempt / Not Applicable</span>
                    <span className="text-[10px] text-slate-500">Nil fee filing condition</span>
                  </Label>
                </div>

                <div
                  className={`p-3 rounded-lg border flex items-center space-x-2.5 cursor-pointer transition-colors ${
                    paymentStatus === 'pending'
                      ? 'bg-amber-50/80 border-amber-300'
                      : 'bg-white border-slate-200 hover:bg-slate-50'
                  }`}
                  onClick={() => setPaymentStatus('pending')}
                >
                  <RadioGroupItem value="pending" id="pay-pending" />
                  <Label htmlFor="pay-pending" className="text-xs font-medium cursor-pointer">
                    <span className="block text-slate-900 font-semibold">Pending Determination</span>
                    <span className="text-[10px] text-slate-500">To be declared later</span>
                  </Label>
                </div>
              </RadioGroup>
            </div>

            </>)}
            {/* Application Remarks */}
            <div className="space-y-1.5">
              <Label htmlFor="remarks" className="text-xs font-semibold text-slate-700">
                Application Remarks (Optional)
              </Label>
              <Textarea
                id="remarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Add application-specific remarks..."
                rows={3}
                className="text-xs resize-none border-slate-300"
              />
            </div>
          </CardContent>

          <CardFooter className="p-4 sm:p-5 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-50/40">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Info className="size-3.5 text-slate-400 shrink-0" />
              <span>
                Creates your application and shows the next steps.
              </span>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => navigate('/institution/applications')}
                disabled={submitting}
                className="text-xs border-slate-200"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={submitting || checkingExisting || selectedTypeExists || bothTypesExist || !!conflictError}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs"
              >
                {submitting ? 'Creating application…' : 'Create application'}
              </Button>
            </div>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
