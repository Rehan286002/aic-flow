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
import { documentsApi } from '@/features/documents/api';
import type {
  DocumentExtractionTextResponse,
  DocumentVersion,
  ExtractionTextPage,
} from '@/types/document';
import {
  FileText,
  RefreshCw,
  Search,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from 'lucide-react';
import { toast } from 'sonner';

interface DocumentTextExtractionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  requirementId: string;
  requirementCode: string;
  requirementTitle: string;
  version: DocumentVersion | null;
  onOpenFields?: () => void;
}

export function DocumentTextExtractionModal({
  open,
  onOpenChange,
  requirementId,
  requirementCode,
  requirementTitle,
  version,
  onOpenFields,
}: DocumentTextExtractionModalProps) {
  const [data, setData] = useState<DocumentExtractionTextResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedPageIndex, setSelectedPageIndex] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);

  const loadText = useCallback(async () => {
    if (!version) return;
    setLoading(true);
    try {
      const res = await documentsApi.getExtractionText(
        requirementId,
        version.document_version_id
      );
      setData(res);
      setSelectedPageIndex(0);
    } catch (err: any) {
      toast.error('Failed to load extracted text', {
        description: err?.detail || err?.message || 'Text extraction may not be complete yet.',
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [requirementId, version]);

  useEffect(() => {
    if (open && version) {
      void loadText();
    } else {
      setData(null);
      setSearchQuery('');
      setSelectedPageIndex(0);
    }
  }, [open, version, loadText]);

  const currentPage: ExtractionTextPage | null = useMemo(() => {
    if (!data || data.pages.length === 0) return null;
    return data.pages[selectedPageIndex] || data.pages[0];
  }, [data, selectedPageIndex]);

  const copyCurrentText = () => {
    if (!currentPage) return;
    navigator.clipboard.writeText(currentPage.page_text);
    setCopied(true);
    toast.success(`Page ${currentPage.page_number} text copied to clipboard`);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyFullText = () => {
    if (!data || !data.full_text) return;
    navigator.clipboard.writeText(data.full_text);
    toast.success('Full document text copied to clipboard');
  };

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
                Extracted Text Inspection (Page-by-Page)
              </DialogTitle>
            </div>

            <div className="flex items-center gap-2">
              {onOpenFields && (
                <Button
                  variant="outline"
                  size="xs"
                  onClick={onOpenFields}
                  className="h-7 text-xs gap-1 border-slate-200 text-slate-700 hover:text-indigo-600"
                >
                  <BookOpen className="size-3 text-slate-400" />
                  <span>View Fields</span>
                </Button>
              )}
              <Button
                variant="outline"
                size="xs"
                onClick={loadText}
                disabled={loading}
                className="h-7 text-xs gap-1 border-slate-200"
              >
                <RefreshCw className={`size-3 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </Button>
            </div>
          </div>
          <DialogDescription className="text-xs text-slate-500 truncate max-w-2xl">
            {requirementTitle} • File: <span className="font-medium text-slate-700">{version.original_filename}</span>
          </DialogDescription>
        </DialogHeader>

        {/* Top Controls: Page Selector Tabs & Overall Method */}
        {data && data.pages.length > 0 && (
          <div className="mt-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b border-slate-100 shrink-0">
            {/* Page Buttons */}
            <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 max-w-full">
              <span className="text-[11px] font-semibold text-slate-500 mr-1 shrink-0">
                Pages ({data.total_pages}):
              </span>
              {data.pages.map((p, idx) => {
                const isSelected = idx === selectedPageIndex;
                return (
                  <button
                    key={p.page_number}
                    type="button"
                    onClick={() => setSelectedPageIndex(idx)}
                    className={`h-7 px-2.5 rounded-md text-xs font-medium transition-colors shrink-0 flex items-center gap-1 border ${
                      isSelected
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                        : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <span>P. {p.page_number}</span>
                    <span
                      className={`text-[9px] px-1 py-0.2 rounded font-mono ${
                        isSelected
                          ? 'bg-indigo-700 text-white'
                          : p.extraction_method === 'NATIVE_TEXT'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {p.extraction_method === 'NATIVE_TEXT' ? 'PDF text' : 'Scanned text'}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Overall Method Badge */}
            <div className="flex items-center gap-2 shrink-0">
              <Badge
                variant="outline"
                className="text-[10px] h-5 px-2 bg-slate-50 text-slate-700 border-slate-200 font-mono gap-1"
              >
                <span>Pipeline: {data.overall_method}</span>
              </Badge>
            </div>
          </div>
        )}

        {/* Search & Actions Bar */}
        {currentPage && (
          <div className="mt-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 shrink-0">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 size-3.5 text-slate-400" />
              <Input
                type="text"
                placeholder="Find in page text..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs bg-slate-50/50 border-slate-200"
              />
            </div>

            {/* Page Metadata & Copy Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="text-[11px] text-slate-500 flex items-center gap-2">
                <span>{currentPage.char_count} chars</span>
                <span>•</span>
                <span>{currentPage.line_count} lines</span>
                {currentPage.ocr_line_count > 0 && (
                  <>
                    <span>•</span>
                    <span className="text-amber-700 font-mono text-[10px]">
                      {currentPage.ocr_line_count} Recognised text lines
                    </span>
                  </>
                )}
              </div>

              <Button
                variant="outline"
                size="xs"
                onClick={copyCurrentText}
                className="h-8 text-xs gap-1 border-slate-200 text-slate-700"
              >
                {copied ? (
                  <Check className="size-3 text-emerald-600" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>Copy Page</span>
              </Button>

              {data?.full_text && (
                <Button
                  variant="outline"
                  size="xs"
                  onClick={copyFullText}
                  className="h-8 text-xs gap-1 border-slate-200 text-slate-700"
                >
                  <Copy className="size-3 text-slate-400" />
                  <span>Copy All</span>
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Page Content Display */}
        <div className="flex-1 overflow-y-auto mt-2 p-4 rounded-xl border border-slate-200 bg-slate-900 text-slate-100 font-mono text-xs leading-relaxed min-h-[300px]">
          {loading && !data && (
            <div className="flex items-center justify-center py-20 text-slate-400 gap-2 text-xs">
              <RefreshCw className="size-4 animate-spin text-indigo-400" />
              <span>Loading extracted document text layer...</span>
            </div>
          )}

          {!loading && (!data || data.pages.length === 0) && (
            <div className="text-center py-16 space-y-2 text-slate-400">
              <FileText className="size-8 mx-auto text-slate-500" />
              <p className="text-xs font-semibold text-slate-300">
                No text extracted for this document version
              </p>
              <p className="text-[11px] text-slate-500">
                Run "Extract Content" to process this document.
              </p>
            </div>
          )}

          {currentPage && (
            <div className="whitespace-pre-wrap select-all font-mono">
              {currentPage.page_text.trim() === '' ? (
                <span className="text-slate-500 italic">
                  [Page {currentPage.page_number} contains no extractable text]
                </span>
              ) : searchQuery ? (
                // Highlight matches in page text
                currentPage.page_text.split(new RegExp(`(${searchQuery.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi')).map((part, i) =>
                  part.toLowerCase() === searchQuery.toLowerCase() ? (
                    <mark key={i} className="bg-amber-400 text-slate-950 font-bold px-0.5 rounded">
                      {part}
                    </mark>
                  ) : (
                    <span key={i}>{part}</span>
                  )
                )
              ) : (
                currentPage.page_text
              )}
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <DialogFooter className="border-t border-slate-100 pt-3 flex flex-row items-center justify-between sm:justify-between shrink-0">
          <div className="flex items-center gap-2">
            {data && data.pages.length > 1 && (
              <>
                <Button
                  variant="outline"
                  size="xs"
                  onClick={() => setSelectedPageIndex((prev) => Math.max(0, prev - 1))}
                  disabled={selectedPageIndex === 0}
                  className="h-7 text-xs border-slate-200 gap-1"
                >
                  <ChevronLeft className="size-3" />
                  <span>Prev Page</span>
                </Button>
                <span className="text-xs text-slate-500 font-medium">
                  {selectedPageIndex + 1} / {data.pages.length}
                </span>
                <Button
                  variant="outline"
                  size="xs"
                  onClick={() => setSelectedPageIndex((prev) => Math.min(data.pages.length - 1, prev + 1))}
                  disabled={selectedPageIndex >= data.pages.length - 1}
                  className="h-7 text-xs border-slate-200 gap-1"
                >
                  <span>Next Page</span>
                  <ChevronRight className="size-3" />
                </Button>
              </>
            )}
          </div>

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
