import { useEffect, useState, useCallback, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { documentsApi } from '@/features/documents/api';
import type { ApplicationRequirementItem } from '@/types/application';
import type { DocumentHistoryResponse, DocumentVersion } from '@/types/document';
import {
  Download,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  Clock,
  FileText,
  CheckCircle2,
  Lock,
  PlusCircle,
  Copy,
  Check,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import { toast } from 'sonner';
import { DocumentExtractionModal } from './DocumentExtractionModal';
import { DocumentTextExtractionModal } from './DocumentTextExtractionModal';

interface DocumentVersionHistoryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  requirement: ApplicationRequirementItem | null;
  onOpenUpload: (requirement: ApplicationRequirementItem) => void;
}

export function DocumentVersionHistoryModal({
  open,
  onOpenChange,
  requirement,
  onOpenUpload,
}: DocumentVersionHistoryModalProps) {
  const [history, setHistory] = useState<DocumentHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [retryingScanId, setRetryingScanId] = useState<string | null>(null);
  const [processingVersionId, setProcessingVersionId] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Modals for inspection
  const [selectedVersionForExtraction, setSelectedVersionForExtraction] = useState<DocumentVersion | null>(null);
  const [extractionModalOpen, setExtractionModalOpen] = useState(false);
  const [selectedVersionForText, setSelectedVersionForText] = useState<DocumentVersion | null>(null);
  const [textExtractionModalOpen, setTextExtractionModalOpen] = useState(false);

  // Polling management (bounded to max 12 cycles / ~30 seconds)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef<number>(0);
  const loadHistoryRef = useRef<((isPolling?: boolean) => Promise<void>) | null>(null);

  const clearPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    pollCountRef.current = 0;
  }, []);

  const loadHistory = useCallback(async (isPolling = false) => {
    if (!requirement) return;
    if (!isPolling) setLoading(true);
    try {
      const data = await documentsApi.getHistory(
        requirement.application_requirement_id
      );
      setHistory(data);

      // Check if any version is actively PROCESSING or newly QUEUED
      const hasInFlightJob = data.versions.some(
        (v) =>
          v.is_clean &&
          (v.processing_job?.processing_status === 'PROCESSING' ||
            v.processing_job?.processing_status === 'QUEUED')
      );

      if (hasInFlightJob && pollCountRef.current < 12) {
        pollCountRef.current += 1;
        pollTimerRef.current = setTimeout(() => {
          void loadHistoryRef.current?.(true);
        }, 2500);
      } else {
        clearPolling();
      }
    } catch (err: any) {
      if (!isPolling) {
        toast.error('Failed to load version history', {
          description: err?.detail || err?.message || 'Network error',
        });
      }
      clearPolling();
    } finally {
      if (!isPolling) setLoading(false);
    }
  }, [requirement, clearPolling]);

  useEffect(() => {
    loadHistoryRef.current = loadHistory;
  }, [loadHistory]);

  useEffect(() => {
    if (open && requirement) {
      pollCountRef.current = 0;
      void loadHistory(false);
    } else {
      clearPolling();
      setHistory(null);
      setSelectedVersionForExtraction(null);
      setExtractionModalOpen(false);
      setSelectedVersionForText(null);
      setTextExtractionModalOpen(false);
    }
    return () => clearPolling();
  }, [open, requirement, loadHistory, clearPolling]);

  const handleRetryScan = async (versionId: string) => {
    if (!requirement) return;
    setRetryingScanId(versionId);
    try {
      const res = await documentsApi.retryScan(
        requirement.application_requirement_id,
        versionId
      );
      toast.success('Scan re-evaluated', { description: res.message });
      await loadHistory();
    } catch (err: any) {
      toast.error('Retry Scan Failed', {
        description: err?.detail || err?.message,
      });
    } finally {
      setRetryingScanId(null);
    }
  };

  const handleProcessDocument = async (versionId: string) => {
    if (!requirement) return;
    setProcessingVersionId(versionId);
    try {
      const job = await documentsApi.process(
        requirement.application_requirement_id,
        versionId
      );
      toast.success('Content extraction initiated', {
        description: `Authoritative status: ${job.processing_status}. Processing in background.`,
      });

      // Reset poll counter and immediately refresh history
      clearPolling();
      await loadHistory(false);
    } catch (err: any) {
      toast.error('Content Extraction Failed', {
        description: err?.detail || err?.message || 'Could not schedule extraction job.',
      });
    } finally {
      setProcessingVersionId(null);
    }
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    toast.success('SHA-256 copied to clipboard');
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (!requirement) return null;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-3xl bg-white p-6 max-h-[90vh] flex flex-col">
          <DialogHeader className="space-y-1 pb-3 border-b border-slate-100 shrink-0">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {requirement.item_code}
                </span>
                <DialogTitle className="text-base font-semibold text-slate-900">
                  Document Version History & Integrity
                </DialogTitle>
              </div>
              <Button
                variant="outline"
                size="xs"
                onClick={() => {
                  clearPolling();
                  void loadHistory(false);
                }}
                disabled={loading}
                className="h-7 text-xs gap-1 border-slate-200"
              >
                <RefreshCw className={`size-3 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </Button>
            </div>
            <DialogDescription className="text-xs text-slate-500">
              {requirement.title}
            </DialogDescription>
          </DialogHeader>

          {/* Scrollable Versions List */}
          <div className="flex-1 overflow-y-auto py-3 space-y-3 min-h-[220px]">
            {loading && !history && (
              <div className="flex items-center justify-center py-12 text-slate-400 gap-2 text-xs">
                <RefreshCw className="size-4 animate-spin text-indigo-600" />
                <span>Retrieving immutable version audit trail...</span>
              </div>
            )}

            {history && history.versions.length === 0 && (
              <div className="text-center py-10 space-y-3 bg-slate-50/70 border border-slate-200 rounded-xl p-6">
                <FileText className="size-8 text-slate-400 mx-auto" />
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-slate-700">
                    No documents have been uploaded yet
                  </p>
                  <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                    Upload an authentic evidence file (.pdf, .jpg, .jpeg, .png) to establish the
                    initial Version 1 record.
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    onOpenChange(false);
                    onOpenUpload(requirement);
                  }}
                  className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5"
                >
                  <PlusCircle className="size-3.5" />
                  <span>Upload First Version</span>
                </Button>
              </div>
            )}

            {history &&
              history.versions.map((ver: DocumentVersion) => {
                const isActiveClean = history.active_version_id === ver.document_version_id;
                const scanStatus = ver.security_scan?.scan_status || 'NOT_SCANNED';
                const procJob = ver.processing_job;
                const procStatus = procJob?.processing_status;
                const isProcessingThis = processingVersionId === ver.document_version_id;

                return (
                  <div
                    key={ver.document_version_id}
                    className={`p-4 rounded-xl border transition-colors ${
                      isActiveClean
                        ? 'bg-emerald-50/20 border-emerald-300 shadow-2xs'
                        : scanStatus === 'DETECTED'
                        ? 'bg-rose-50/30 border-rose-200'
                        : 'bg-white border-slate-200'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      {/* Left: Version Meta */}
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-xs font-mono bg-slate-800 text-white px-2 py-0.5 rounded">
                            v{ver.version_number}
                          </span>
                          <span className="font-semibold text-xs text-slate-900 truncate max-w-xs">
                            {ver.original_filename}
                          </span>

                          {isActiveClean && (
                            <Badge
                              variant="outline"
                              className="text-[10px] h-4.5 px-1.5 bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold gap-1"
                            >
                              <CheckCircle2 className="size-3 text-emerald-600" />
                              <span>Active Accepted Evidence</span>
                            </Badge>
                          )}

                          {/* 1. Separate Antivirus Status Badge */}
                          {scanStatus === 'CLEAN' ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] h-4.5 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200 gap-1 font-medium"
                              title="Verified by ClamAV scanner"
                            >
                              <ShieldCheck className="size-3 text-emerald-600" />
                              <span>CLEAN</span>
                            </Badge>
                          ) : scanStatus === 'DETECTED' ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] h-4.5 px-1.5 bg-rose-100 text-rose-800 border-rose-300 gap-1 font-bold"
                              title="Malware detected by ClamAV scanner"
                            >
                              <ShieldAlert className="size-3 text-rose-600" />
                              <span>INFECTED / DETECTED</span>
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="text-[10px] h-4.5 px-1.5 bg-amber-50 text-amber-800 border-amber-300 gap-1 font-medium"
                              title="Malware scan error"
                            >
                              <AlertTriangle className="size-3 text-amber-600" />
                              <span>SCAN ERROR</span>
                            </Badge>
                          )}

                          {/* 2. Separate Content Extraction Status Badge */}
                          {ver.is_clean && (
                            <>
                              {procStatus === 'COMPLETED' ? (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] h-4.5 px-1.5 bg-indigo-50 text-indigo-700 border-indigo-200 gap-1 font-medium"
                                  title="OCR and structured content extraction completed"
                                >
                                  <Sparkles className="size-3 text-indigo-600" />
                                  <span>Extracted</span>
                                </Badge>
                              ) : procStatus === 'PROCESSING' ? (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] h-4.5 px-1.5 bg-blue-50 text-blue-800 border-blue-200 gap-1 font-medium"
                                  title="Extraction pipeline in progress"
                                >
                                  <RefreshCw className="size-3 text-blue-600 animate-spin" />
                                  <span>Extracting...</span>
                                </Badge>
                              ) : procStatus === 'QUEUED' ? (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] h-4.5 px-1.5 bg-slate-100 text-slate-700 border-slate-200 gap-1 font-medium"
                                  title="Document clean and ready for content extraction"
                                >
                                  <Clock className="size-3 text-slate-500" />
                                  <span>Queued (Ready)</span>
                                </Badge>
                              ) : procStatus === 'FAILED' ? (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] h-4.5 px-1.5 bg-rose-50 text-rose-800 border-rose-200 gap-1 font-medium"
                                  title={procJob?.error_message || 'Content extraction failed'}
                                >
                                  <AlertTriangle className="size-3 text-rose-600" />
                                  <span>Extraction Failed</span>
                                </Badge>
                              ) : (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] h-4.5 px-1.5 bg-slate-100 text-slate-600 border-slate-200 gap-1"
                                >
                                  <span>Not Extracted</span>
                                </Badge>
                              )}
                            </>
                          )}
                        </div>

                        {/* Detected Threat Detail */}
                        {scanStatus === 'DETECTED' && ver.security_scan?.threat_name && (
                          <div className="text-[11px] text-rose-700 bg-rose-100/70 p-2 rounded border border-rose-200 space-y-0.5">
                            <p className="font-semibold">
                              Malware Detected: {ver.security_scan.threat_name}
                            </p>
                            <p className="text-[10px] text-rose-600">
                              This replacement file was rejected by ClamAV. Download and content extraction are strictly prohibited.
                              The previous clean version remains active evidence.
                            </p>
                          </div>
                        )}

                        {/* Extraction Failure Detail */}
                        {ver.is_clean && procStatus === 'FAILED' && procJob?.error_message && (
                          <div className="text-[11px] text-rose-700 bg-rose-50/70 p-2 rounded border border-rose-200 space-y-0.5">
                            <p className="font-semibold">Extraction Error:</p>
                            <p className="text-[10px] text-rose-600 font-mono">
                              {procJob.error_message}
                            </p>
                          </div>
                        )}

                        {/* File Details: Size, Date, Mime, Scanner */}
                        <div className="flex items-center gap-3 text-[11px] text-slate-500 flex-wrap">
                          <span>{(ver.file_size_bytes / 1024).toFixed(1)} KB</span>
                          <span>•</span>
                          <span>{ver.mime_type}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="size-3 text-slate-400" />
                            {new Date(ver.uploaded_at).toLocaleString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                          {ver.security_scan?.scanner_name && (
                            <>
                              <span>•</span>
                              <span className="font-mono text-[10px] text-slate-400">
                                {ver.security_scan.scanner_name}
                                {ver.security_scan.scanner_version ? ` ${ver.security_scan.scanner_version}` : ''}
                              </span>
                            </>
                          )}
                        </div>

                        {/* Cryptographic SHA-256 fingerprint */}
                        <div className="flex items-center gap-2 pt-0.5">
                          <span className="text-[10px] font-mono text-slate-400 uppercase">SHA-256:</span>
                          <code className="text-[10px] font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 truncate max-w-sm">
                            {ver.sha256_hex}
                          </code>
                          <Button
                            type="button"
                            variant="ghost"
                            size="xs"
                            onClick={() => copyHash(ver.sha256_hex)}
                            className="h-5 px-1.5 text-slate-400 hover:text-slate-700"
                          >
                            {copiedHash === ver.sha256_hex ? (
                              <Check className="size-3 text-emerald-600" />
                            ) : (
                              <Copy className="size-3" />
                            )}
                          </Button>
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center sm:flex-col gap-2 shrink-0 pt-1 sm:pt-0">
                        {/* Download button */}
                        {ver.is_downloadable ? (
                          <a
                            href={documentsApi.getDownloadUrl(
                              requirement.application_requirement_id,
                              ver.document_version_id
                            )}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center gap-1.5 h-7 px-2.5 text-xs font-medium rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-indigo-600 transition-colors shadow-2xs w-full"
                          >
                            <Download className="size-3" />
                            <span>Download</span>
                          </a>
                        ) : (
                          <div className="flex items-center gap-1 text-[11px] text-rose-600 font-medium bg-rose-50 px-2 py-1 rounded border border-rose-200">
                            <Lock className="size-3 text-rose-500" />
                            <span>Download Blocked</span>
                          </div>
                        )}

                        {/* Antivirus retry scan button */}
                        {scanStatus === 'ERROR' && (
                          <Button
                            variant="outline"
                            size="xs"
                            onClick={() => handleRetryScan(ver.document_version_id)}
                            disabled={retryingScanId === ver.document_version_id}
                            className="h-7 text-xs border-amber-300 text-amber-800 hover:bg-amber-50 w-full"
                          >
                            <RefreshCw
                              className={`size-3 mr-1 ${
                                retryingScanId === ver.document_version_id ? 'animate-spin' : ''
                              }`}
                            />
                            <span>Retry Scan</span>
                          </Button>
                        )}

                        {/* Content Extraction Actions (Clean Files Only) */}
                        {ver.is_clean && (
                          <>
                            {/* Case A: COMPLETED -> View Extracted Fields and Raw Text */}
                            {procStatus === 'COMPLETED' && (
                              <div className="flex flex-col gap-1.5 w-full">
                                <Button
                                  variant="outline"
                                  size="xs"
                                  onClick={() => {
                                    setSelectedVersionForExtraction(ver);
                                    setExtractionModalOpen(true);
                                  }}
                                  className="h-7 text-xs border-indigo-200 bg-indigo-50/50 text-indigo-700 hover:bg-indigo-100/70 gap-1 w-full font-medium"
                                >
                                  <Sparkles className="size-3 text-indigo-600" />
                                  <span>View Fields</span>
                                </Button>

                                <Button
                                  variant="outline"
                                  size="xs"
                                  onClick={() => {
                                    setSelectedVersionForText(ver);
                                    setTextExtractionModalOpen(true);
                                  }}
                                  className="h-7 text-xs border-slate-200 text-slate-700 hover:bg-slate-50 gap-1 w-full"
                                >
                                  <BookOpen className="size-3 text-slate-400" />
                                  <span>View Text</span>
                                </Button>
                              </div>
                            )}

                            {/* Case B: QUEUED or unstarted -> Explicit "Extract Content" trigger */}
                            {(procStatus === 'QUEUED' || !procStatus) && (
                              <Button
                                size="xs"
                                onClick={() => handleProcessDocument(ver.document_version_id)}
                                disabled={isProcessingThis}
                                className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1 w-full shadow-2xs font-medium"
                              >
                                <Sparkles className={`size-3 ${isProcessingThis ? 'animate-spin' : ''}`} />
                                <span>{isProcessingThis ? 'Starting...' : 'Extract Content'}</span>
                              </Button>
                            )}

                            {/* Case C: PROCESSING -> Disabled indicator */}
                            {procStatus === 'PROCESSING' && (
                              <Button
                                size="xs"
                                disabled
                                className="h-7 text-xs bg-slate-100 text-slate-500 border border-slate-200 gap-1 w-full"
                              >
                                <RefreshCw className="size-3 animate-spin text-slate-500" />
                                <span>Extracting...</span>
                              </Button>
                            )}

                            {/* Case D: FAILED -> Safe Retry Extraction trigger */}
                            {procStatus === 'FAILED' && (
                              <Button
                                variant="outline"
                                size="xs"
                                onClick={() => handleProcessDocument(ver.document_version_id)}
                                disabled={isProcessingThis}
                                className="h-7 text-xs border-rose-300 text-rose-700 hover:bg-rose-50 gap-1 w-full font-medium"
                              >
                                <RefreshCw className={`size-3 ${isProcessingThis ? 'animate-spin' : ''}`} />
                                <span>Retry Extraction</span>
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>

          <DialogFooter className="border-t border-slate-100 pt-3 flex flex-row items-center justify-between sm:justify-between shrink-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs"
            >
              Close
            </Button>

            {requirement.applicability_status === 'APPLICABLE' && (
              <Button
                type="button"
                size="sm"
                onClick={() => {
                  onOpenChange(false);
                  onOpenUpload(requirement);
                }}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5"
              >
                <PlusCircle className="size-3.5" />
                <span>Upload Replacement Version</span>
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Submodal 1: Structured Candidate Fields Viewer */}
      <DocumentExtractionModal
        open={extractionModalOpen}
        onOpenChange={setExtractionModalOpen}
        requirementId={requirement.application_requirement_id}
        requirementCode={requirement.item_code}
        requirementTitle={requirement.title}
        version={selectedVersionForExtraction}
        onOpenTextExtraction={() => {
          setSelectedVersionForText(selectedVersionForExtraction);
          setExtractionModalOpen(false);
          setTextExtractionModalOpen(true);
        }}
      />

      {/* Submodal 2: Page-by-Page Extracted Text Reader */}
      <DocumentTextExtractionModal
        open={textExtractionModalOpen}
        onOpenChange={setTextExtractionModalOpen}
        requirementId={requirement.application_requirement_id}
        requirementCode={requirement.item_code}
        requirementTitle={requirement.title}
        version={selectedVersionForText}
        onOpenFields={() => {
          setSelectedVersionForExtraction(selectedVersionForText);
          setTextExtractionModalOpen(false);
          setExtractionModalOpen(true);
        }}
      />
    </>
  );
}
