import { useEffect, useState, useCallback, useMemo } from 'react';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/hooks/useAuth';
import { documentsApi } from '@/features/documents/api';
import type {
  DocumentExtraction,
  DocumentVersion,
  ExtractedField,
  ExtractedFieldReview,
} from '@/types/document';
import {
  FileText,
  RefreshCw,
  Search,
  Cpu,
  Clock,
  Layers,
  Sparkles,
  Info,
  SlidersHorizontal,
  CheckCircle2,
  AlertTriangle,
  History,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Edit3,
  X,
  Check,
} from 'lucide-react';
import { toast } from 'sonner';

interface DocumentExtractionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  requirementId: string;
  requirementCode: string;
  requirementTitle: string;
  version: DocumentVersion | null;
  onOpenTextExtraction?: () => void;
}

interface FieldCardProps {
  field: ExtractedField;
  requirementId: string;
  versionId: string;
  isAuditor: boolean;
  onFieldUpdated: (updatedField: ExtractedField) => void;
}

function FieldCard({
  field,
  requirementId,
  versionId,
  isAuditor,
  onFieldUpdated,
}: FieldCardProps) {
  const [mode, setMode] = useState<'NONE' | 'ACCEPT' | 'CORRECT'>('NONE');
  const [submitting, setSubmitting] = useState(false);
  const [acceptRemarks, setAcceptRemarks] = useState('');
  const [correctedVal, setCorrectedVal] = useState('');
  const [correctionNote, setCorrectionNote] = useState('');

  // History drawer state
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<ExtractedFieldReview[] | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const hasRawValue = field.raw_value !== null && field.raw_value !== '';
  const matchingPct =
    field.matching_strength !== null
      ? Math.round(field.matching_strength * 100)
      : field.confidence !== null
      ? Math.round(field.confidence * 100)
      : null;

  const ocrPct =
    field.ocr_confidence !== null
      ? Math.round(field.ocr_confidence * 100)
      : null;

  const nonWsCount = useMemo(
    () => correctionNote.replace(/\s/g, '').length,
    [correctionNote]
  );

  const handleAcceptSubmit = async () => {
    try {
      setSubmitting(true);
      const review = await documentsApi.createFieldReview(
        requirementId,
        versionId,
        field.extracted_field_id,
        {
          accepted_as_extracted: true,
          review_note: acceptRemarks.trim() || undefined,
        }
      );
      toast.success('Field accepted as extracted', {
        description: 'Your regulatory verification has been recorded immutably.',
      });
      setMode('NONE');
      setAcceptRemarks('');
      setHistory(null);
      onFieldUpdated({ ...field, latest_review: review });
    } catch (err: any) {
      toast.error('Failed to submit review', {
        description:
          err?.detail || err?.message || 'Error recording verification.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCorrectSubmit = async () => {
    if (!correctedVal.trim()) {
      toast.error('Corrected value is required');
      return;
    }
    if (nonWsCount < 5) {
      toast.error('Justification note requires at least 5 non-whitespace characters');
      return;
    }

    try {
      setSubmitting(true);
      let parsedVal: any = correctedVal.trim();
      try {
        parsedVal = JSON.parse(correctedVal);
      } catch {
        parsedVal = correctedVal.trim();
      }

      const review = await documentsApi.createFieldReview(
        requirementId,
        versionId,
        field.extracted_field_id,
        {
          accepted_as_extracted: false,
          corrected_value: parsedVal,
          review_note: correctionNote.trim(),
        }
      );
      toast.success('Authoritative correction recorded', {
        description: 'Your correction and regulatory note have been persisted.',
      });
      setMode('NONE');
      setCorrectedVal('');
      setCorrectionNote('');
      setHistory(null);
      onFieldUpdated({ ...field, latest_review: review });
    } catch (err: any) {
      toast.error('Failed to submit correction', {
        description:
          err?.detail || err?.message || 'Error recording correction.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const toggleHistory = async () => {
    if (!historyOpen) {
      setHistoryOpen(true);
      if (!history) {
        setHistoryLoading(true);
        try {
          const data = await documentsApi.getFieldReviews(
            requirementId,
            versionId,
            field.extracted_field_id
          );
          setHistory(data);
        } catch (err: any) {
          toast.error('Could not load review history', {
            description: err?.detail || 'Failed to fetch audit log.',
          });
        } finally {
          setHistoryLoading(false);
        }
      }
    } else {
      setHistoryOpen(false);
    }
  };

  return (
    <div className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors space-y-3 shadow-2xs">
      {/* Field Top Row: Label, Code, Category Badge, Confidence Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-xs text-slate-900">
            {field.field_label || field.field_code}
          </span>
          <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
            {field.field_code}
          </span>

          {/* Review Tier Badge */}
          {field.review_category === 'HIGH' && (
            <Badge
              variant="outline"
              className="text-[9px] h-4 px-1.5 bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold"
            >
              HIGH TIER
            </Badge>
          )}
          {field.review_category === 'MEDIUM_REVIEW' && (
            <Badge
              variant="outline"
              className="text-[9px] h-4 px-1.5 bg-amber-50 text-amber-800 border-amber-300 font-medium"
            >
              MEDIUM REVIEW
            </Badge>
          )}
          {field.review_category === 'LOW_UNCERTAIN' && (
            <Badge
              variant="outline"
              className="text-[9px] h-4 px-1.5 bg-rose-50 text-rose-800 border-rose-300 font-medium"
            >
              UNCERTAIN
            </Badge>
          )}
        </div>

        {/* Right: Heuristic Matching vs OCR Confidence Badges */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {matchingPct !== null && (
            <Badge
              variant="outline"
              className="text-[10px] h-4.5 px-1.5 bg-indigo-50 text-indigo-700 border-indigo-200 font-medium gap-1"
              title="Rule-based heuristic pattern matching strength"
            >
              <Sparkles className="size-2.5 text-indigo-600" />
              <span>Match: {matchingPct}%</span>
            </Badge>
          )}

          {ocrPct !== null ? (
            <Badge
              variant="outline"
              className="text-[10px] h-4.5 px-1.5 bg-slate-100 text-slate-700 border-slate-200 font-mono"
              title="Raw OCR line recognition confidence"
            >
              OCR: {ocrPct}%
            </Badge>
          ) : field.extraction_method === 'NATIVE_TEXT' ? (
            <Badge
              variant="outline"
              className="text-[10px] h-4.5 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200 font-mono"
              title="Extracted from digital PDF text layer"
            >
              Native Text (100%)
            </Badge>
          ) : null}
        </div>
      </div>

      {/* Values Grid: Raw Value & Normalized Value */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
        <div className="p-2 rounded bg-slate-50 border border-slate-200/80 space-y-0.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">
            Raw Text as Identified
          </span>
          {hasRawValue ? (
            <p className="font-mono text-slate-800 break-words select-all text-xs">
              {field.raw_value}
            </p>
          ) : (
            <p className="text-slate-400 italic text-[11px]">
              Not detected in document content
            </p>
          )}
        </div>

        <div className="p-2 rounded bg-slate-50 border border-slate-200/80 space-y-0.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">
            Normalized Representation
          </span>
          {field.normalized_value !== null && field.normalized_value !== undefined ? (
            <p className="font-mono text-slate-800 break-words select-all text-xs">
              {typeof field.normalized_value === 'object'
                ? JSON.stringify(field.normalized_value)
                : String(field.normalized_value)}
            </p>
          ) : (
            <p className="text-slate-400 italic text-[11px]">None</p>
          )}
        </div>
      </div>

      {/* Contextual Source Snippet */}
      {field.source_snippet && (
        <div className="text-[11px] text-slate-600 bg-slate-50/70 p-2 rounded border border-slate-200/70 space-y-0.5">
          <span className="text-[10px] font-medium text-slate-400 block">
            Surrounding Context Snippet:
          </span>
          <p className="font-mono text-slate-700 italic select-all leading-relaxed">
            "{field.source_snippet}"
          </p>
        </div>
      )}

      {/* Latest Review Banner (if already reviewed) */}
      {field.latest_review && (
        <div
          className={`p-2.5 rounded-lg border text-xs space-y-1.5 ${
            field.latest_review.accepted_as_extracted
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
              : 'bg-amber-50/70 border-amber-200 text-amber-950'
          }`}
        >
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-1.5">
              {field.latest_review.accepted_as_extracted ? (
                <>
                  <CheckCircle2 className="size-3.5 text-emerald-600 shrink-0" />
                  <span className="font-semibold text-emerald-900">
                    Accepted as Extracted
                  </span>
                </>
              ) : (
                <>
                  <AlertTriangle className="size-3.5 text-amber-600 shrink-0" />
                  <span className="font-semibold text-amber-900">
                    Authoritative Correction Recorded
                  </span>
                </>
              )}
              {field.latest_review.reviewer_name && (
                <span className="text-[11px] text-slate-600">
                  by <span className="font-medium text-slate-800">{field.latest_review.reviewer_name}</span>{' '}
                  <span className="font-mono text-[10px] bg-white/80 px-1 py-0.2 rounded border border-slate-200">
                    {field.latest_review.reviewer_role}
                  </span>
                </span>
              )}
            </div>

            <span className="text-[10px] text-slate-500 font-mono">
              {new Date(field.latest_review.reviewed_at).toLocaleString('en-IN', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>

          {!field.latest_review.accepted_as_extracted && (
            <div className="p-1.5 rounded bg-white/80 border border-amber-200/80 text-[11px] font-mono text-slate-800">
              <span className="text-[10px] uppercase font-bold text-amber-800 mr-1.5">
                Corrected Value:
              </span>
              {typeof field.latest_review.corrected_value === 'object'
                ? JSON.stringify(field.latest_review.corrected_value)
                : String(field.latest_review.corrected_value)}
            </div>
          )}

          {field.latest_review.review_note && (
            <p className="text-[11px] italic text-slate-700 leading-relaxed bg-white/50 p-1.5 rounded">
              "{field.latest_review.review_note}"
            </p>
          )}
        </div>
      )}

      {/* Auditor Review Action Bar (Only for AUDITOR or LEAD_AUDITOR) */}
      {isAuditor && mode === 'NONE' && (
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={() => {
                setMode('ACCEPT');
                setAcceptRemarks('');
              }}
              className="h-7 text-xs gap-1 border-emerald-300 text-emerald-800 bg-emerald-50/50 hover:bg-emerald-100/60"
            >
              <Check className="size-3 text-emerald-600" />
              <span>Accept as Extracted</span>
            </Button>

            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={() => {
                setMode('CORRECT');
                setCorrectedVal(
                  field.normalized_value !== null && field.normalized_value !== undefined
                    ? typeof field.normalized_value === 'object'
                      ? JSON.stringify(field.normalized_value)
                      : String(field.normalized_value)
                    : field.raw_value || ''
                );
                setCorrectionNote('');
              }}
              className="h-7 text-xs gap-1 border-amber-300 text-amber-800 bg-amber-50/50 hover:bg-amber-100/60"
            >
              <Edit3 className="size-3 text-amber-600" />
              <span>Enter Correction</span>
            </Button>
          </div>

          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={toggleHistory}
            className="h-7 text-[11px] text-slate-500 hover:text-slate-800 gap-1"
          >
            <History className="size-3 text-slate-400" />
            <span>Audit History</span>
            {historyOpen ? (
              <ChevronUp className="size-3" />
            ) : (
              <ChevronDown className="size-3" />
            )}
          </Button>
        </div>
      )}

      {/* Inline Accept Panel */}
      {isAuditor && mode === 'ACCEPT' && (
        <div className="p-3 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-emerald-900 flex items-center gap-1.5">
              <ShieldCheck className="size-3.5 text-emerald-600" />
              Confirm Field Acceptance
            </span>
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => setMode('NONE')}
              className="h-6 w-6 p-0 text-slate-400 hover:text-slate-600"
            >
              <X className="size-3.5" />
            </Button>
          </div>
          <p className="text-[11px] text-emerald-800">
            Accepting certifies that the candidate value matches regulatory evidence.
            This action creates an immutable audit record.
          </p>
          <Input
            type="text"
            placeholder="Optional verification remarks (max 2000 chars)..."
            value={acceptRemarks}
            maxLength={2000}
            onChange={(e) => setAcceptRemarks(e.target.value)}
            className="h-8 text-xs bg-white border-emerald-300 focus-visible:ring-emerald-400"
          />
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => setMode('NONE')}
              disabled={submitting}
              className="h-7 text-xs"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="xs"
              onClick={handleAcceptSubmit}
              disabled={submitting}
              className="h-7 text-xs bg-emerald-700 hover:bg-emerald-800 text-white gap-1"
            >
              {submitting ? (
                <RefreshCw className="size-3 animate-spin" />
              ) : (
                <Check className="size-3" />
              )}
              <span>Confirm Acceptance</span>
            </Button>
          </div>
        </div>
      )}

      {/* Inline Correction Panel */}
      {isAuditor && mode === 'CORRECT' && (
        <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-200 text-xs space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-amber-950 flex items-center gap-1.5">
              <Edit3 className="size-3.5 text-amber-700" />
              Submit Regulatory Field Correction
            </span>
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => setMode('NONE')}
              className="h-6 w-6 p-0 text-slate-400 hover:text-slate-600"
            >
              <X className="size-3.5" />
            </Button>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-amber-900 block">
              Authoritative Corrected Value <span className="text-rose-600">*</span>
            </label>
            <Input
              type="text"
              placeholder="Enter verified value..."
              value={correctedVal}
              onChange={(e) => setCorrectedVal(e.target.value)}
              className="h-8 text-xs bg-white border-amber-300 focus-visible:ring-amber-400 font-mono"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <label className="font-medium text-amber-900">
                Regulatory Justification Note <span className="text-rose-600">*</span>
              </label>
              <span
                className={`text-[10px] font-mono ${
                  nonWsCount >= 5 ? 'text-emerald-700 font-semibold' : 'text-rose-600'
                }`}
              >
                {nonWsCount} / 5 non-whitespace chars (min)
              </span>
            </div>
            <Textarea
              placeholder="Explain rationale for overriding extracted candidate (e.g. OCR misread, official amendment, annexure discrepancy)..."
              value={correctionNote}
              maxLength={2000}
              onChange={(e) => setCorrectionNote(e.target.value)}
              className="min-h-16 text-xs bg-white border-amber-300 focus-visible:ring-amber-400 leading-relaxed"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => setMode('NONE')}
              disabled={submitting}
              className="h-7 text-xs"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="xs"
              onClick={handleCorrectSubmit}
              disabled={submitting || !correctedVal.trim() || nonWsCount < 5}
              className="h-7 text-xs bg-amber-700 hover:bg-amber-800 text-white gap-1 disabled:opacity-50"
            >
              {submitting ? (
                <RefreshCw className="size-3 animate-spin" />
              ) : (
                <ShieldCheck className="size-3" />
              )}
              <span>Record Immutable Correction</span>
            </Button>
          </div>
        </div>
      )}

      {/* Non-Auditor History Toggle */}
      {!isAuditor && (
        <div className="flex items-center justify-end pt-1 border-t border-slate-100">
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={toggleHistory}
            className="h-6 text-[11px] text-slate-500 hover:text-slate-800 gap-1"
          >
            <History className="size-3 text-slate-400" />
            <span>Audit History</span>
            {historyOpen ? (
              <ChevronUp className="size-3" />
            ) : (
              <ChevronDown className="size-3" />
            )}
          </Button>
        </div>
      )}

      {/* Collapsible Chronological Audit History */}
      {historyOpen && (
        <div className="pt-2 border-t border-slate-200/80 space-y-2">
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-semibold px-1">
            <span>Regulatory Review Audit Trail</span>
            <span className="text-[10px] text-slate-400 font-normal">
              Append-only immutable record
            </span>
          </div>

          {historyLoading && (
            <div className="flex items-center justify-center py-4 text-xs text-slate-400 gap-2">
              <RefreshCw className="size-3 animate-spin text-indigo-600" />
              <span>Loading review log...</span>
            </div>
          )}

          {!historyLoading && Array.isArray(history) && history.length === 0 && (
            <p className="text-[11px] text-slate-400 italic py-2 text-center bg-slate-50 rounded">
              No audit reviews recorded for this field yet.
            </p>
          )}

          {!historyLoading &&
            Array.isArray(history) &&
            history.map((rev) => (
              <div
                key={rev.extracted_field_review_id}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/80 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5">
                    {rev.accepted_as_extracted ? (
                      <Badge
                        variant="outline"
                        className="text-[9px] h-4 px-1.5 bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold"
                      >
                        ACCEPTED
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-[9px] h-4 px-1.5 bg-amber-50 text-amber-800 border-amber-300 font-semibold"
                      >
                        CORRECTED
                      </Badge>
                    )}

                    {rev.reviewer_name && (
                      <span className="text-[11px] text-slate-700">
                        <span className="font-medium text-slate-900">{rev.reviewer_name}</span>{' '}
                        <span className="font-mono text-[10px] bg-white px-1 rounded border border-slate-200 text-slate-600">
                          {rev.reviewer_role}
                        </span>
                      </span>
                    )}
                  </div>

                  <span className="font-mono text-[10px] text-slate-400">
                    {new Date(rev.reviewed_at).toLocaleString('en-IN', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>

                {!rev.accepted_as_extracted && rev.corrected_value !== undefined && (
                  <div className="text-[11px] font-mono text-slate-800 bg-white p-1 rounded border border-slate-200">
                    <span className="text-[10px] uppercase font-bold text-amber-800 mr-1.5">
                      Value:
                    </span>
                    {typeof rev.corrected_value === 'object'
                      ? JSON.stringify(rev.corrected_value)
                      : String(rev.corrected_value)}
                  </div>
                )}

                {rev.review_note && (
                  <p className="text-[11px] text-slate-700 italic bg-white/60 p-1.5 rounded border border-slate-100">
                    "{rev.review_note}"
                  </p>
                )}
              </div>
            ))}
        </div>
      )}

      {/* Provenance & Spatial Coordinates Footer */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100 flex-wrap gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          {field.page_number && (
            <span className="font-medium text-slate-600">
              Page {field.page_number}
            </span>
          )}

          {field.bounding_box && (
            <span className="font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              Box: [x:{Math.round(field.bounding_box.x ?? 0)}, y:{Math.round(field.bounding_box.y ?? 0)}, w:{Math.round(field.bounding_box.width ?? 0)}, h:{Math.round(field.bounding_box.height ?? 0)}]
            </span>
          )}

          {field.extraction_method && (
            <span className="font-mono text-slate-500">
              Method: {field.extraction_method}
            </span>
          )}
        </div>

        {field.notes && (
          <span className="text-slate-500 italic max-w-xs truncate" title={field.notes}>
            Note: {field.notes}
          </span>
        )}
      </div>
    </div>
  );
}

export function DocumentExtractionModal({
  open,
  onOpenChange,
  requirementId,
  requirementCode,
  requirementTitle,
  version,
  onOpenTextExtraction,
}: DocumentExtractionModalProps) {
  const { activeContext } = useAuth();
  const [extraction, setExtraction] = useState<DocumentExtraction | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM_REVIEW' | 'LOW_UNCERTAIN'>('ALL');

  const isAuditor =
    activeContext?.role_code === 'AUDITOR' ||
    activeContext?.role_code === 'LEAD_AUDITOR';

  const loadExtraction = useCallback(async () => {
    if (!version) return;
    setLoading(true);
    try {
      const data = await documentsApi.getExtraction(
        requirementId,
        version.document_version_id
      );
      setExtraction(data);
    } catch (err: any) {
      toast.error('Failed to load candidate field extractions', {
        description:
          err?.detail ||
          err?.message ||
          'Extraction record may not be completed yet.',
      });
      setExtraction(null);
    } finally {
      setLoading(false);
    }
  }, [requirementId, version]);

  useEffect(() => {
    if (open && version) {
      void loadExtraction();
    } else {
      setExtraction(null);
      setSearchQuery('');
      setCategoryFilter('ALL');
    }
  }, [open, version, loadExtraction]);

  const handleFieldUpdated = (updatedField: ExtractedField) => {
    setExtraction((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        fields: prev.fields.map((f) =>
          f.extracted_field_id === updatedField.extracted_field_id
            ? updatedField
            : f
        ),
      };
    });
  };

  const filteredFields = useMemo(() => {
    if (!extraction) return [];
    return extraction.fields.filter((field) => {
      const matchesSearch =
        searchQuery === '' ||
        (field.field_label || '')
          .toLowerCase()
          .includes(searchQuery.toLowerCase()) ||
        field.field_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (field.raw_value || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (field.source_snippet || '')
          .toLowerCase()
          .includes(searchQuery.toLowerCase());

      const matchesCat =
        categoryFilter === 'ALL' || field.review_category === categoryFilter;

      return matchesSearch && matchesCat;
    });
  }, [extraction, searchQuery, categoryFilter]);

  if (!version) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl bg-white p-6 max-h-[92vh] flex flex-col">
        {/* Header */}
        <DialogHeader className="space-y-1 pb-3 border-b border-slate-100 shrink-0">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {requirementCode}
              </span>
              <span className="font-mono text-xs font-semibold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-200">
                v{version.version_number}
              </span>
              <DialogTitle className="text-base font-semibold text-slate-900">
                Structured Candidate Fields & Provenance
              </DialogTitle>
            </div>

            <div className="flex items-center gap-2">
              {onOpenTextExtraction && (
                <Button
                  variant="outline"
                  size="xs"
                  onClick={onOpenTextExtraction}
                  className="h-7 text-xs gap-1 border-slate-200 text-slate-700 hover:text-indigo-600"
                >
                  <FileText className="size-3 text-slate-400" />
                  <span>View Raw Text</span>
                </Button>
              )}
              <Button
                variant="outline"
                size="xs"
                onClick={loadExtraction}
                disabled={loading}
                className="h-7 text-xs gap-1 border-slate-200"
              >
                <RefreshCw
                  className={`size-3 text-slate-500 ${
                    loading ? 'animate-spin' : ''
                  }`}
                />
                <span>Refresh</span>
              </Button>
            </div>
          </div>
          <DialogDescription className="text-xs text-slate-500 truncate max-w-2xl">
            {requirementTitle} • File:{' '}
            <span className="font-medium text-slate-700">
              {version.original_filename}
            </span>
          </DialogDescription>
        </DialogHeader>

        {/* Statutory Regulatory Disclaimer Banner */}
        <div className="mt-2.5 p-3 rounded-lg bg-amber-50/80 border border-amber-200/90 text-amber-900 text-xs shrink-0 flex items-start gap-2">
          <Info className="size-4 text-amber-700 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold text-amber-950">
              Statutory Regulatory Disclaimer
            </p>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              Treat metadata, OCR and document-integrity outputs as evidence
              signals, not proof of forgery or statutory compliance. Extracted
              fields are candidate values identified through rule-based
              heuristics. Final statutory regulatory decisions remain exclusively
              with competent authorities.
            </p>
          </div>
        </div>

        {/* Engine Metadata Ribbon */}
        {extraction && (
          <div className="mt-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 flex flex-wrap items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <Cpu className="size-3 text-indigo-600" />
                Pipeline Engine:
              </span>
              <span className="font-mono text-slate-700 bg-white px-1.5 py-0.5 rounded border border-slate-200">
                {extraction.engine_version || extraction.extraction_engine}
              </span>
            </div>
            <div className="flex items-center gap-3 text-slate-500">
              <span className="flex items-center gap-1">
                <Clock className="size-3 text-slate-400" />
                {new Date(extraction.created_at).toLocaleString('en-IN', {
                  day: '2-digit',
                  month: 'short',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
              <span>•</span>
              <span className="font-medium text-slate-700">
                {extraction.fields.length} candidate{' '}
                {extraction.fields.length === 1 ? 'field' : 'fields'}
              </span>
            </div>
          </div>
        )}

        {/* Search & Filter Bar */}
        <div className="mt-2.5 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 shrink-0">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 size-3.5 text-slate-400" />
            <Input
              type="text"
              placeholder="Search candidate fields, values, or snippets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 text-xs bg-slate-50/50 border-slate-200"
            />
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-[11px] text-slate-400 flex items-center gap-1 pl-1">
              <SlidersHorizontal className="size-3 text-slate-400" /> Tier:
            </span>
            {(['ALL', 'HIGH', 'MEDIUM_REVIEW', 'LOW_UNCERTAIN'] as const).map(
              (cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategoryFilter(cat)}
                  className={`text-[10px] px-2 py-1 rounded font-medium transition-colors ${
                    categoryFilter === cat
                      ? 'bg-slate-800 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {cat === 'ALL'
                    ? 'All'
                    : cat === 'HIGH'
                    ? 'High'
                    : cat === 'MEDIUM_REVIEW'
                    ? 'Medium'
                    : 'Uncertain'}
                </button>
              )
            )}
          </div>
        </div>

        {/* Scrollable Fields List */}
        <div className="flex-1 overflow-y-auto py-3 space-y-3 min-h-[240px]">
          {loading && !extraction && (
            <div className="flex items-center justify-center py-16 text-slate-400 gap-2 text-xs">
              <RefreshCw className="size-4 animate-spin text-indigo-600" />
              <span>Retrieving candidate fields and spatial coordinates...</span>
            </div>
          )}

          {!loading && extraction && filteredFields.length === 0 && (
            <div className="text-center py-12 space-y-2 bg-slate-50/60 border border-slate-200 rounded-xl p-6">
              <Layers className="size-7 text-slate-400 mx-auto" />
              <p className="text-xs font-semibold text-slate-700">
                {searchQuery || categoryFilter !== 'ALL'
                  ? 'No candidate fields match your filters'
                  : 'No candidate fields extracted'}
              </p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                {searchQuery || categoryFilter !== 'ALL'
                  ? 'Try clearing the search query or changing the review category filter.'
                  : 'The extraction engine did not locate specific candidate keys for this document type.'}
              </p>
            </div>
          )}

          {filteredFields.map((field: ExtractedField) => (
            <FieldCard
              key={field.extracted_field_id}
              field={field}
              requirementId={requirementId}
              versionId={version.document_version_id}
              isAuditor={isAuditor}
              onFieldUpdated={handleFieldUpdated}
            />
          ))}
        </div>

        {/* Footer */}
        <DialogFooter className="border-t border-slate-100 pt-3 flex flex-row items-center justify-between sm:justify-between shrink-0">
          <span className="text-[11px] text-slate-400">
            {extraction
              ? `Showing ${filteredFields.length} of ${extraction.fields.length} candidate fields`
              : ''}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="text-xs"
          >
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
