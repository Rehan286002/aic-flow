import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { SYNTHETIC_PENDING_WORK_ITEMS } from '@/features/dashboard/fixtures/auditor-dashboard-fixture';
import type { PendingWorkItem } from '@/types/dashboard';
import { AlertCircle, ChevronRight, CheckCircle2, ArrowUpRight, MessageSquareQuote } from 'lucide-react';
import { toast } from 'sonner';

export function PendingWorkList() {
  const [items, setItems] = useState<PendingWorkItem[]>(SYNTHETIC_PENDING_WORK_ITEMS);
  const [selectedItem, setSelectedItem] = useState<PendingWorkItem | null>(null);

  const handleInspect = (item: PendingWorkItem) => {
    setSelectedItem(item);
  };

  const handleResolveAction = (actionType: 'accept' | 'dismiss' | 'rectify' | 'escalate') => {
    if (!selectedItem) return;

    if (actionType === 'accept') {
      toast.success(`Flag Accepted: ${selectedItem.ruleCode}`, {
        description: `Discrepancy confirmed for ${selectedItem.applicationNumber}. Added to formal deficiency report.`,
      });
    } else if (actionType === 'dismiss') {
      toast.info(`Flag Dismissed: ${selectedItem.ruleCode}`, {
        description: `Discrepancy waived with auditor observation rationale.`,
      });
    } else if (actionType === 'rectify') {
      toast.warning(`Rectification Requested: ${selectedItem.ruleCode}`, {
        description: `Correction notice dispatched to ${selectedItem.institutionName}.`,
      });
    } else {
      toast.info(`Escalated to Lead Auditor: ${selectedItem.ruleCode}`, {
        description: `Case ${selectedItem.applicationNumber} forwarded to Dr. Sunita Kulkarni.`,
      });
    }

    setItems((prev) => prev.filter((i) => i.id !== selectedItem.id));
    setSelectedItem(null);
  };

  return (
    <Card className="bg-white border-slate-200/90 shadow-2xs">
      <CardHeader className="p-4 sm:p-5 pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
              <AlertCircle className="size-4 text-amber-600" />
              <span>Priority Triage Queue</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Unresolved rule findings requiring auditor assessment
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-[10px] font-bold text-amber-800 bg-amber-50 border-amber-300">
            {items.length} Pending
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 pt-0">
        {items.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500">
            <CheckCircle2 className="size-8 text-emerald-500 mx-auto mb-2 opacity-80" />
            <p className="font-semibold text-slate-800">Triage Queue Cleared</p>
            <p className="text-[11px] text-slate-400 mt-1">All prioritized Annexure 2.1 flags have been evaluated.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((item) => (
              <div
                key={item.id}
                className="py-3 first:pt-1 last:pb-1 flex flex-col gap-1.5 group hover:bg-slate-50/50 rounded-lg p-2 transition-colors -mx-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[11px] font-bold bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200/70">
                      {item.ruleCode}
                    </span>
                    <span className="text-xs font-semibold text-slate-800 truncate">
                      {item.ruleTitle}
                    </span>
                  </div>

                  <span
                    className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                      item.severity === 'high'
                        ? 'bg-rose-100 text-rose-800'
                        : item.severity === 'medium'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {item.severity}
                  </span>
                </div>

                <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                  {item.summary}
                </p>

                <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400">
                  <span className="truncate max-w-[190px]">
                    {item.institutionName} • <span className="font-mono">{item.applicationNumber}</span>
                  </span>

                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => handleInspect(item)}
                    className="h-6 text-[11px] font-medium text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 px-1.5 gap-0.5"
                  >
                    <span>Inspect</span>
                    <ChevronRight className="size-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      {/* Inspect Finding Dialog */}
      <Dialog open={!!selectedItem} onOpenChange={(open) => !open && setSelectedItem(null)}>
        <DialogContent className="max-w-lg text-slate-900">
          <DialogHeader>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">
                    {selectedItem?.ruleCode}
                  </span>
                  <DialogTitle className="text-sm font-semibold">
                    {selectedItem?.ruleTitle}
                  </DialogTitle>
                </div>
                <DialogDescription className="text-xs text-slate-500">
                  {selectedItem?.applicationNumber} • {selectedItem?.institutionName}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedItem && (
            <div className="space-y-3 py-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                  Automated Finding Assessment:
                </span>
                <p className="text-slate-800 leading-relaxed font-medium">
                  {selectedItem.summary}
                </p>
                <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
                  <span>Source Document: {selectedItem.documentType}</span>
                  <span className="font-mono text-slate-400">AY 2026-27 Rule v4.2</span>
                </div>
              </div>

              <div className="p-3 rounded-lg border border-indigo-100 bg-indigo-50/50">
                <span className="text-[11px] font-semibold text-indigo-900 block mb-1">
                  Auditor Decision Requirement:
                </span>
                <p className="text-slate-600 leading-relaxed text-[11px]">
                  Under AICTE regulatory guidelines, discrepancies must be verified against original document text layers and issuer registries. Select an adjudication action below:
                </p>
              </div>
            </div>
          )}

          <DialogFooter className="flex-col sm:flex-row gap-2 border-t border-slate-100 pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleResolveAction('dismiss')}
              className="text-xs text-slate-700 border-slate-200"
            >
              Dismiss Flag (Valid)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleResolveAction('rectify')}
              className="text-xs text-amber-700 border-amber-200 hover:bg-amber-50"
            >
              <MessageSquareQuote className="size-3.5 mr-1" />
              Request Rectification
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleResolveAction('escalate')}
              className="text-xs text-purple-700 border-purple-200 hover:bg-purple-50"
            >
              <ArrowUpRight className="size-3.5 mr-1" />
              Escalate to Lead
            </Button>
            <Button
              size="sm"
              onClick={() => handleResolveAction('accept')}
              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              Confirm Discrepancy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
