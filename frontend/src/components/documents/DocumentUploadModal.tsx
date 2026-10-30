import React, { useState, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { documentsApi } from '@/features/documents/api';
import { workflowApi } from '@/features/workflow/api';
import type { ApplicationRequirementItem } from '@/types/application';
import type { DocumentUploadResponse } from '@/types/document';
import {
  UploadCloud,
  FileCheck2,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  FileText,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

interface DocumentUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  requirement: ApplicationRequirementItem | null;
  obligationId?: string | null;
  onUploadSuccess: (response: DocumentUploadResponse) => void;
}

export function DocumentUploadModal({
  open,
  onOpenChange,
  requirement,
  obligationId = null,
  onUploadSuccess,
}: DocumentUploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [scanResult, setScanResult] = useState<DocumentUploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [evidenceNote, setEvidenceNote] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const resetState = () => {
    setSelectedFile(null);
    setUploading(false);
    setScanResult(null);
    setErrorMessage(null);
    setEvidenceNote('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (!uploading) {
      resetState();
      onOpenChange(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMessage(null);
    setScanResult(null);
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      // Basic client-side pre-validation
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!['pdf', 'jpg', 'jpeg', 'png'].includes(ext || '')) {
        setErrorMessage('Allowed formats are PDF, JPEG, and PNG.');
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        setErrorMessage('File size exceeds the 20 MB limit.');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setScanResult(null);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!['pdf', 'jpg', 'jpeg', 'png'].includes(ext || '')) {
        setErrorMessage('Allowed formats are PDF, JPEG, and PNG.');
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        setErrorMessage('File size exceeds the 20 MB limit.');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleSubmit = async () => {
    if (!requirement || !selectedFile) return;
    if (obligationId && evidenceNote.trim().length < 5) {
      setErrorMessage('Add a short note describing the condition evidence.');
      return;
    }

    setUploading(true);
    setErrorMessage(null);
    setScanResult(null);

    try {
      const res = obligationId
        ? await workflowApi.uploadObligationEvidence(
            obligationId,
            requirement.application_requirement_id,
            selectedFile,
            evidenceNote.trim(),
          )
        : await documentsApi.upload(
            requirement.application_requirement_id,
            selectedFile
          );
      setScanResult(res);

      if (res.document_version.is_clean) {
        toast.success(obligationId ? 'Condition evidence submitted' : 'Document uploaded successfully', {
          description: obligationId ? 'The clean document version is linked to the selected approval condition.' : `Version ${res.document_version.version_number} passed the file safety and integrity checks.`,
        });
        onUploadSuccess(res);
      } else if (res.document_version.security_scan?.scan_status === 'DETECTED') {
        toast.error('File could not be accepted', {
          description: `The file did not pass the security check and was not added to the application.`,
        });
        onUploadSuccess(res);
      } else {
        toast.warning('File safety check needs attention', {
          description: 'The required safety check could not be completed. The file has not been added to application evidence.',
        });
        onUploadSuccess(res);
      }
    } catch (err: any) {
      const msg = err?.detail || err?.message || 'Failed to upload document.';
      setErrorMessage(msg);
      toast.error('Upload Failed', { description: msg });
    } finally {
      setUploading(false);
    }
  };

  if (!requirement) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-xl bg-white p-6">
        <DialogHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              {requirement.item_code}
            </span>
            <DialogTitle className="text-base font-semibold text-slate-900">
              Upload Evidence Document
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-slate-500">
            {requirement.title}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {obligationId && <label className="grid gap-1 text-xs font-medium text-slate-700">Condition evidence note
            <textarea value={evidenceNote} onChange={(e) => setEvidenceNote(e.target.value)} rows={2} placeholder="Describe how this document addresses the approval condition" className="rounded-lg border border-slate-200 px-3 py-2 text-xs"/>
          </label>}
          {/* Regulatory Guidelines Notice */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-600 space-y-1">
            <div className="font-medium text-slate-800 flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-indigo-600" />
              <span>File Safety Check</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Your document is checked for file safety and integrity before it is added to the application. Accepted formats: PDF, JPEG, PNG (max 20 MB).
            </p>
          </div>

          {/* Drag & Drop Upload Zone */}
          {!scanResult && (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
                selectedFile
                  ? 'border-indigo-400 bg-indigo-50/20'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                disabled={uploading}
              />

              {selectedFile ? (
                <div className="space-y-2">
                  <div className="size-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center mx-auto">
                    <FileText className="size-5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-900">{selectedFile.name}</p>
                    <p className="text-[11px] text-slate-500">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to scan & upload
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      resetState();
                    }}
                    className="h-6 text-[11px] text-slate-500 hover:text-rose-600 gap-1"
                  >
                    <X className="size-3" />
                    <span>Choose a different file</span>
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="size-10 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center mx-auto">
                    <UploadCloud className="size-5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-800">
                      Click to browse or drag and drop document
                    </p>
                    <p className="text-[11px] text-slate-500">
                      PDF, JPEG, or PNG up to 20 MB
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 flex items-start gap-2.5 text-xs">
              <AlertTriangle className="size-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="space-y-0.5 flex-1">
                <p className="font-semibold text-rose-900">Upload Rejected</p>
                <p className="text-rose-700 text-[11px] leading-relaxed">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Real-time Scan Result Banner */}
          {scanResult && (
            <div className="space-y-3">
              {scanResult.document_version.is_clean ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 space-y-2 text-xs">
                  <div className="flex items-center gap-2 font-semibold text-emerald-900">
                    <ShieldCheck className="size-5 text-emerald-600" />
                    <span>File safety check passed</span>
                  </div>
                  <p className="text-emerald-800 text-[11px]">
                    The document passed the required safety and integrity checks. Version {scanResult.document_version.version_number} is now active evidence.
                  </p>
                  <div className="pt-1 text-[11px] font-medium text-emerald-800">
                    File integrity: Verified
                  </div>
                </div>
              ) : scanResult.document_version.security_scan?.scan_status === 'DETECTED' ? (
                <div className="rounded-xl border border-rose-300 bg-rose-50 p-4 space-y-2 text-xs">
                  <div className="flex items-center gap-2 font-semibold text-rose-900">
                    <ShieldAlert className="size-5 text-rose-600" />
                    <span>File safety check not passed</span>
                  </div>
                  <p className="text-rose-800 text-[11px]">
                    The file did not pass the security check and has not been added to the application. Please choose a different file.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 space-y-2 text-xs">
                  <div className="flex items-center gap-2 font-semibold text-amber-900">
                    <AlertTriangle className="size-5 text-amber-600" />
                    <span>File check pending</span>
                  </div>
                  <p className="text-amber-800 text-[11px]">
                    The file could not complete the required safety check and has not been added to application evidence. Please retry later or contact support.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleClose}
            disabled={uploading}
            className="text-xs"
          >
            {scanResult ? 'Done' : 'Cancel'}
          </Button>

          {!scanResult && (
            <Button
              type="button"
              size="sm"
              onClick={handleSubmit}
              disabled={!selectedFile || uploading}
              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5"
            >
              {uploading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Checking file safety…</span>
                </>
              ) : (
                <>
                  <FileCheck2 className="size-3.5" />
                  <span>Upload Document</span>
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
