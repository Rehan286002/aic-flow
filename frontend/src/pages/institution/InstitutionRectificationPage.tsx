import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  FileCheck2,
  Upload,
  CheckCircle2,
  Clock,
  Building2,
  ArrowRight,
  ShieldCheck,
  FileText,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { useDemoScenario } from '@/features/demo/demoContext';
import { computeFileSha256 } from '@/features/demo/cryptoUtils';
import type { ReplacementDocMeta } from '@/features/demo/demoStore';
import { InstitutionWorkflowProgress } from '@/components/institution/InstitutionWorkflowProgress';

export const InstitutionRectificationPage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState, submitRectification, resetDemo } = useDemoScenario();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileSha256, setFileSha256] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [hashingProgress, setHashingProgress] = useState<number>(0);
  const [isHashing, setIsHashing] = useState<boolean>(false);
  const [clarificationText, setClarificationText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submissionSuccess, setSubmissionSuccess] = useState<boolean>(
    demoState.rectification.status === 'RECTIFICATION_SUBMITTED'
  );

  const isAlreadyRectified = demoState.rectification.status === 'RECTIFICATION_SUBMITTED';

  const handleFileChange = async (file: File) => {
    setFileError(null);
    if (!file || file.size === 0) {
      setSelectedFile(null);
      setFileSha256(null);
      setFileError('The selected file is empty (0 bytes). Regulatory submissions require a valid, non-empty document.');
      return;
    }
    setSelectedFile(file);
    setIsHashing(true);
    setHashingProgress(10);
    try {
      const hash = await computeFileSha256(file, (p) => setHashingProgress(p));
      setFileSha256(hash);
    } catch (err: unknown) {
      console.error('Failed to compute file SHA-256:', err);
      const msg = err instanceof Error ? err.message : 'Cryptographic hash calculation failed.';
      setFileError(msg);
      setSelectedFile(null);
      setFileSha256(null);
    } finally {
      setIsHashing(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      void handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !fileSha256 || clarificationText.trim().length < 10) {
      return;
    }

    setIsSubmitting(true);

    const docMeta: ReplacementDocMeta = {
      filename: selectedFile.name,
      byteSize: selectedFile.size,
      mimeType: selectedFile.type || 'application/pdf',
      sha256Digest: fileSha256,
      uploadedAt: new Date().toISOString(),
      versionLabel: 'v2 (Replacement)',
    };

    setTimeout(() => {
      submitRectification(docMeta, clarificationText.trim());
      setIsSubmitting(false);
      setSubmissionSuccess(true);
    }, 600);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Institution</span>
            <span>/</span>
            <span>Compliance Rectification Center</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Building2 className="w-6 h-6 text-primary" />
            Deficiency Resolution &amp; Revision Ingest
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Application: <span className="font-semibold text-foreground">{demoState.applicationNumber}</span> | Institution: <span className="font-semibold text-foreground">{demoState.institutionName}</span> | Academic Year: <span className="font-semibold text-foreground">{demoState.academicYear}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant={isAlreadyRectified ? 'default' : 'outline'}
            className={
              isAlreadyRectified
                ? 'bg-emerald-600 text-white font-medium text-xs py-1 px-2.5'
                : 'border-amber-500 text-amber-700 bg-amber-50 font-medium text-xs py-1 px-2.5'
            }
          >
            {isAlreadyRectified ? 'Active Revision: #2 (Rectified)' : 'Active Revision: #1 (Action Required)'}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={resetDemo}
            className="text-xs text-muted-foreground hover:text-foreground"
            title="Reset demonstration scenario to baseline Revision 1"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Demo
          </Button>
        </div>
      </div>

      {/* Lifecycle Progress Stepper */}
      <InstitutionWorkflowProgress />

      {/* Success Notification if already submitted */}
      {(submissionSuccess || isAlreadyRectified) && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50/80 p-5 shadow-xs">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-emerald-100 p-2 text-emerald-700">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-emerald-950">
                  Rectification Successfully Submitted as Revision #2
                </h3>
                <span className="text-xs text-emerald-700 font-mono">
                  {demoState.rectification.rectifiedAt ? new Date(demoState.rectification.rectifiedAt).toLocaleString() : 'Just now'}
                </span>
              </div>
              <p className="text-sm text-emerald-900 leading-relaxed">
                Replacement document <span className="font-semibold font-mono">{demoState.rectification.replacementDocument?.filename || 'Structural_Stability_Certificate_2026.pdf'}</span> was securely ingested and cryptographic SHA-256 digest recorded. Simulated regulatory re-validation completed: Requirement <span className="font-semibold">EOA-SD-04</span> shifted to <span className="font-semibold text-emerald-800">SATISFIED</span>.
              </p>
              <div className="pt-2 flex flex-wrap gap-3">
                <Button
                  size="sm"
                  className="bg-emerald-700 hover:bg-emerald-800 text-white"
                  onClick={() => navigate('/institution/reports')}
                >
                  <FileCheck2 className="w-4 h-4 mr-1.5" />
                  View Updated Compliance Report
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-emerald-300 text-emerald-900 hover:bg-emerald-100/60"
                  onClick={() => navigate('/institution/documents')}
                >
                  <FileText className="w-4 h-4 mr-1.5" />
                  Inspect Documents Evidence Vault
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Clarification Request Banner */}
      <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-5 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="rounded-full bg-amber-100 p-2 text-amber-700 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-900">
                Regulatory Action Required &bull; Requirement {demoState.rectification.requirementCode}
              </span>
              <span className="text-xs text-amber-700 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Response Window: 15 Working Days
              </span>
            </div>
            <h2 className="text-base font-semibold text-amber-950">
              {demoState.rectification.deficiencyTitle}
            </h2>
            <div className="bg-white/80 rounded-md border border-amber-200 p-3 mt-2 text-sm text-amber-950 leading-relaxed font-sans">
              <p className="font-medium text-xs text-amber-800 uppercase tracking-wide mb-1">
                Auditor Review Notice:
              </p>
              &ldquo;{demoState.rectification.auditorInstruction}&rdquo;
            </div>
          </div>
        </div>
      </div>

      {/* Rectification Form */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Submit Replacement Evidence &amp; Explanation
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Provide the required official documentation to resolve the flagged deficiency. This will generate Revision #2 of your EoA self-disclosure application.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* File Upload Zone */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              1. Replacement Document Upload (PDF only, max 25MB)
            </label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                selectedFile
                  ? 'border-emerald-400 bg-emerald-50/30'
                  : 'border-muted-foreground/30 hover:border-primary/60 hover:bg-muted/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    void handleFileChange(e.target.files[0]);
                  }
                }}
              />
              <div className="flex flex-col items-center justify-center gap-2">
                <div className="rounded-full bg-primary/10 p-3 text-primary">
                  <Upload className="w-6 h-6" />
                </div>
                {selectedFile ? (
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; {selectedFile.type || 'application/pdf'}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-foreground">
                      Click to browse or drag and drop your certificate PDF here
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Must be signed by a registered Chartered / Structural Engineer
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* File Error Notice */}
            {fileError && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{fileError}</span>
              </div>
            )}

            {/* Quick Demo Pre-fill button for seamless demonstration */}
            {!selectedFile && (
              <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                <span>Or use the prepared demonstration certificate:</span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    const mockFile = new File(
                      ['%PDF-1.4 Demonstration Structural Stability Certificate 2026 - Apex Institute'],
                      'Structural_Stability_Certificate_2026.pdf',
                      { type: 'application/pdf' }
                    );
                    void handleFileChange(mockFile);
                    setClarificationText(
                      'Enclosed please find the Structural Stability Certificate issued on 12-Jan-2026 by Er. K. V. Deshmukh (Registered Structural Engineer, Lic #SE-98442). The inspection confirms the educational building structure is sound and compliant with NBC 2016 safety norms through 2031.'
                    );
                  }}
                >
                  <FileCheck2 className="w-3.5 h-3.5 mr-1 text-primary" />
                  Pre-fill Demo Stability Certificate
                </Button>
              </div>
            )}

            {/* Live Cryptographic SHA-256 Digest Bar */}
            {isHashing && (
              <div className="space-y-1.5 p-3 rounded-md bg-muted/50 border text-xs">
                <div className="flex justify-between font-mono text-muted-foreground">
                  <span>Computing Client-Side WebCrypto SHA-256...</span>
                  <span>{hashingProgress}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-primary h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${hashingProgress}%` }}
                  />
                </div>
              </div>
            )}

            {fileSha256 && !isHashing && (
              <div className="flex items-center gap-2 p-2.5 rounded-md bg-muted/60 border text-xs font-mono text-foreground break-all">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="text-muted-foreground select-none">SHA-256:</span>
                <span className="font-semibold text-emerald-700">{fileSha256}</span>
              </div>
            )}
          </div>

          {/* Clarification Explanation */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              2. Institution Statement &amp; Reference Notes (Required, min 10 chars)
            </label>
            <Textarea
              rows={4}
              placeholder="State the engineer's registration details, inspection date, and any relevant certificate reference numbers..."
              value={clarificationText}
              onChange={(e) => setClarificationText(e.target.value)}
              className="font-sans text-sm"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Characters: {clarificationText.trim().length} / 10 minimum</span>
              <span>All submissions are recorded with an immutable audit hash</span>
            </div>
          </div>

          {/* Form Actions */}
          <div className="pt-2 flex items-center justify-between border-t">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/institution/reports')}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              disabled={
                !selectedFile ||
                !fileSha256 ||
                clarificationText.trim().length < 10 ||
                isSubmitting
              }
              className="bg-primary hover:bg-primary/90 text-primary-foreground min-w-[220px]"
            >
              {isSubmitting ? (
                <span>Generating Revision #2...</span>
              ) : (
                <span className="flex items-center gap-1.5">
                  Submit Rectification &amp; Create Rev #2
                  <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
export default InstitutionRectificationPage;

