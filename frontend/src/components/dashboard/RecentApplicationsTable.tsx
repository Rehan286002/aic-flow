import { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { StatusBadge } from './StatusBadge';
import { SYNTHETIC_RECENT_APPLICATIONS } from '@/features/dashboard/fixtures/auditor-dashboard-fixture';
import type { RecentApplication } from '@/types/dashboard';
import { Search, Eye, Filter, CheckCircle2, AlertTriangle, ShieldCheck, FileText } from 'lucide-react';
import { toast } from 'sonner';

export function RecentApplicationsTable() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedApp, setSelectedApp] = useState<RecentApplication | null>(null);

  const filteredApplications = useMemo(() => {
    return SYNTHETIC_RECENT_APPLICATIONS.filter((app) => {
      const matchesSearch =
        app.applicationNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.institutionName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.institutionCode.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.state.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        statusFilter === 'all' || app.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [searchQuery, statusFilter]);

  const handleOpenCase = (app: RecentApplication) => {
    setSelectedApp(app);
  };

  const handleAction = (actionName: string) => {
    toast.info(`Case Action: ${actionName}`, {
      description: `Action registered for ${selectedApp?.applicationNumber} in regulatory audit trail.`,
    });
    setSelectedApp(null);
  };

  return (
    <div className="rounded-xl border border-slate-200/90 bg-white shadow-2xs">
      {/* Table Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 sm:p-5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Recent Institutional Applications
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Active Academic Year 2026-27 self-disclosure submissions awaiting auditor verification
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-60">
            <Search className="absolute left-2.5 top-2.5 size-3.5 text-slate-400" />
            <Input
              type="text"
              placeholder="Search by ID, name, city..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 text-xs bg-slate-50/50 border-slate-200"
            />
          </div>

          <div className="w-36 shrink-0">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-8 text-xs bg-slate-50/50 border-slate-200">
                <Filter className="size-3 mr-1 text-slate-400" />
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent className="text-xs">
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="rectification">Rectification Notice</SelectItem>
                <SelectItem value="validated">Fully Validated</SelectItem>
                <SelectItem value="action_required">Action Required</SelectItem>
                <SelectItem value="escalated">Escalated</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-slate-50/70 text-[11px] uppercase tracking-wider text-slate-500">
            <TableRow className="hover:bg-transparent border-slate-100">
              <TableHead className="w-[170px] font-semibold">Application ID</TableHead>
              <TableHead className="font-semibold">Institution Name & State</TableHead>
              <TableHead className="font-semibold">Category</TableHead>
              <TableHead className="font-semibold">Submitted</TableHead>
              <TableHead className="font-semibold text-center">Evidence Progress</TableHead>
              <TableHead className="font-semibold">Review Status</TableHead>
              <TableHead className="text-right font-semibold">Action</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody className="text-xs divide-y divide-slate-100">
            {filteredApplications.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center gap-1">
                    <Search className="size-6 text-slate-300" />
                    <p className="font-medium text-slate-700">No applications match your criteria</p>
                    <p className="text-[11px] text-slate-400">Try adjusting your search terms or status filter.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredApplications.map((app) => (
                <TableRow
                  key={app.id}
                  className="hover:bg-slate-50/60 transition-colors border-slate-100"
                >
                  <TableCell className="font-mono font-medium text-slate-900">
                    <div className="flex items-center gap-1.5">
                      <FileText className="size-3.5 text-indigo-600" />
                      <span>{app.applicationNumber}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono block pl-5">
                      Code: {app.institutionCode}
                    </span>
                  </TableCell>

                  <TableCell>
                    <div className="font-medium text-slate-900">{app.institutionName}</div>
                    <div className="text-[11px] text-slate-500">{app.state}</div>
                  </TableCell>

                  <TableCell className="text-slate-600 whitespace-nowrap">
                    {app.category}
                  </TableCell>

                  <TableCell className="text-slate-500 whitespace-nowrap">
                    {app.submittedDate}
                  </TableCell>

                  <TableCell className="text-center">
                    <div className="inline-flex flex-col items-center">
                      <div className="flex items-center gap-1 font-mono font-medium text-slate-800">
                        <span>{app.verifiedCount}/{app.totalRequirements}</span>
                        <span className="text-[10px] text-slate-400 font-normal">rules</span>
                      </div>
                      {app.flagCount > 0 ? (
                        <span className="text-[10px] font-medium text-amber-700 flex items-center gap-0.5">
                          <AlertTriangle className="size-2.5" />
                          {app.flagCount} {app.flagCount === 1 ? 'flag' : 'flags'}
                        </span>
                      ) : (
                        <span className="text-[10px] font-medium text-emerald-700 flex items-center gap-0.5">
                          <CheckCircle2 className="size-2.5" />
                          clean
                        </span>
                      )}
                    </div>
                  </TableCell>

                  <TableCell>
                    <StatusBadge status={app.status} label={app.statusLabel} />
                  </TableCell>

                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenCase(app)}
                      className="h-7 text-xs px-2.5 gap-1.5 border-slate-200 text-slate-700 hover:text-indigo-600 hover:border-indigo-200 hover:bg-indigo-50/50"
                    >
                      <Eye className="size-3.5" />
                      <span>Review</span>
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Table Footer */}
      <div className="flex items-center justify-between p-3.5 px-4 sm:px-5 border-t border-slate-100 text-[11px] text-slate-500 bg-slate-50/40">
        <div>
          Showing <span className="font-semibold text-slate-800">{filteredApplications.length}</span> of{' '}
          <span className="font-semibold text-slate-800">{SYNTHETIC_RECENT_APPLICATIONS.length}</span> applications
        </div>
        <div className="font-mono text-slate-400">
          Academic Year 2026-27 • Extension of Approval
        </div>
      </div>

      {/* Case Preview Dialog */}
      <Dialog open={!!selectedApp} onOpenChange={(open) => !open && setSelectedApp(null)}>
        <DialogContent className="max-w-2xl text-slate-900">
          <DialogHeader>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <DialogTitle className="text-base font-semibold">
                    {selectedApp?.institutionName}
                  </DialogTitle>
                  <StatusBadge status={selectedApp?.status || ''} label={selectedApp?.statusLabel} size="sm" />
                </div>
                <DialogDescription className="text-xs text-slate-500">
                  {selectedApp?.applicationNumber} • Permanent Code: {selectedApp?.institutionCode} • {selectedApp?.state}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedApp && (
            <div className="space-y-4 py-2 text-xs">
              {/* Submission Metadata */}
              <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200/70">
                <div>
                  <span className="text-slate-500 block text-[11px]">Category:</span>
                  <span className="font-semibold text-slate-800">{selectedApp.category}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Academic Year:</span>
                  <span className="font-semibold text-slate-800">{selectedApp.academicYear}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Assigned Auditor:</span>
                  <span className="font-semibold text-slate-800">{selectedApp.assignedAuditor}</span>
                </div>
              </div>

              {/* Annexure 2.1 Verification Checklist Snapshot */}
              <div>
                <h4 className="font-semibold text-slate-800 mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="size-4 text-indigo-600" />
                  <span>Annexure 2.1 Evidence Signals Snapshot</span>
                </h4>

                <div className="border border-slate-200 rounded-lg divide-y divide-slate-100 text-xs">
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-01: Affidavit 2 Format & Notary</span>
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="size-3.5" /> Satisfied
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-02: Payment Receipt UTR Verification</span>
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="size-3.5" /> Reconciled
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-03: Land / Building Ownership Certificate</span>
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="size-3.5" /> 10.5 Acres Match
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-04: Structural Certificate (Age &gt;30 yrs)</span>
                    <span className="text-slate-500 font-medium">Not Applicable (Age: 18 yrs)</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-05: Fire Safety Certificate Validity</span>
                    {selectedApp.flagCount > 0 ? (
                      <span className="text-amber-700 font-semibold flex items-center gap-1">
                        <AlertTriangle className="size-3.5" /> Validity Expired (15-Sep-2026)
                      </span>
                    ) : (
                      <span className="text-emerald-700 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="size-3.5" /> Valid to 31-Dec-2027
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-06: Satellite GIS Coordinates (25m tolerance)</span>
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="size-3.5" /> Delta: 8.4 meters (Compliant)
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-white">
                    <span className="font-medium text-slate-700">EOA-SD-07: Audited Financial Statements (FY 2024-25)</span>
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="size-3.5" /> CA UDIN Verified
                    </span>
                  </div>
                </div>
              </div>

              {/* Case Document Reference */}
              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[11px] text-slate-600">
                Primary PDF evidence and OCR bounding-box extractions are reviewed in the Case Workspace and Evidence Contradiction Explorer.
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0 border-t border-slate-100 pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedApp(null)}
              className="text-xs border-slate-200"
            >
              Close
            </Button>
            <Button
              size="sm"
              onClick={() => handleAction('Open Case in Evidence Explorer')}
              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              Open Full Case Workspace
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
