import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  ShieldCheck,
  Eye,
  RefreshCw,
  Search,
  CheckCircle2,
  Building2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { useDemoScenario } from '@/features/demo/demoContext';
import { InstitutionWorkflowProgress } from '@/components/institution/InstitutionWorkflowProgress';

interface DocumentItem {
  id: string;
  requirementCode: string;
  title: string;
  filename: string;
  version: string;
  fileSize: string;
  sha256: string;
  virusScan: 'CLEAN' | 'SCANNING';
  extractionStatus: 'COMPLETED' | 'PROCESSING';
  uploadedAt: string;
  extractedSnippet: string;
  allowReplace: boolean;
}

export const InstitutionDocumentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { demoState } = useDemoScenario();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocForPreview, setSelectedDocForPreview] = useState<DocumentItem | null>(null);

  const isRectified = demoState.rectification.status === 'RECTIFICATION_SUBMITTED';

  const documents: DocumentItem[] = [
    {
      id: 'DOC-001',
      requirementCode: 'EOA-SD-01',
      title: 'Affidavit 2 (₹100 e-Stamp, Notarized)',
      filename: 'Affidavit_2_Notarized_AY2026.pdf',
      version: 'v1 (Original)',
      fileSize: '1.42 MB',
      sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: '2026-10-29T08:15:00Z',
      extractedSnippet:
        'BEFORE THE COMPETENT NOTARY PUBLIC AT PUNE... I, Dr. Anil Sharma, Secretary of Apex Education Society, do hereby solemnly affirm and declare on oath on Rs. 100 Non-Judicial Stamp Paper...',
      allowReplace: false,
    },
    {
      id: 'DOC-002',
      requirementCode: 'EOA-SD-02',
      title: 'Processing Fee Challan / Exemption Order',
      filename: 'AICTE_Processing_Fee_Challan_2026.pdf',
      version: 'v1 (Original)',
      fileSize: '840 KB',
      sha256: 'b2c3d4e5f6a17890123456789abcdef0123456789abcdef0123456789abcdef1',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: '2026-10-29T08:16:00Z',
      extractedSnippet:
        'CENTRALIZED APPLICATION PROCESSING RECEIPT... Category: Self-Financing / Exemption Claimed under Section 2.4... Reference Number: REC-2026-99214...',
      allowReplace: false,
    },
    {
      id: 'DOC-003',
      requirementCode: 'EOA-SD-03',
      title: 'Land Ownership & Registration Deed',
      filename: 'Registered_Sale_Deed_Land_Plot_74.pdf',
      version: 'v1 (Original)',
      fileSize: '4.85 MB',
      sha256: 'c3d4e5f6a1b27890123456789abcdef0123456789abcdef0123456789abcdef2',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: '2026-10-29T08:18:00Z',
      extractedSnippet:
        'OFFICE OF THE SUB-REGISTRAR HAVELI PUNE... Registered Conveyance Deed Document No. 4521/1988... Area: 10.50 Acres (Survey No. 74/2A)...',
      allowReplace: false,
    },
    {
      id: 'DOC-004',
      requirementCode: 'EOA-SD-04',
      title: 'Building Plan Approval & Structural Stability Certificate',
      filename: isRectified && demoState.rectification.replacementDocument
        ? demoState.rectification.replacementDocument.filename
        : 'Approved_Municipal_Building_Plan_1990.pdf',
      version: isRectified ? 'v2 (Replacement)' : 'v1 (Original)',
      fileSize: isRectified && demoState.rectification.replacementDocument
        ? `${(demoState.rectification.replacementDocument.byteSize / (1024 * 1024)).toFixed(2)} MB`
        : '3.12 MB',
      sha256: isRectified && demoState.rectification.replacementDocument
        ? demoState.rectification.replacementDocument.sha256Digest
        : 'd4e5f6a1b2c37890123456789abcdef0123456789abcdef0123456789abcdef3',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: isRectified && demoState.rectification.replacementDocument
        ? demoState.rectification.replacementDocument.uploadedAt
        : '2026-10-29T08:20:00Z',
      extractedSnippet: isRectified
        ? 'STRUCTURAL STABILITY & SAFETY CERTIFICATION (NBC 2016)... This is to certify that the institutional building premises of Apex Institute of Technology constructed in 1990 were structurally inspected on 12-Jan-2026. The RCC frames, load bearing pillars, and foundations are structurally sound and fit for educational usage through Year 2031... Er. K. V. Deshmukh (SE-98442)...'
        : 'PUNE MUNICIPAL CORPORATION... Building Sanction Order No. PMC/BP/1990/1142... Plinth and Completion Sanction granted on 15-May-1990 for ground + 3 floors...',
      allowReplace: true,
    },
    {
      id: 'DOC-005',
      requirementCode: 'EOA-SD-05',
      title: 'Fire Safety Certificate / NOC',
      filename: 'Fire_Safety_NOC_Certificate.pdf',
      version: 'v1 (Original)',
      fileSize: '1.20 MB',
      sha256: 'e5f6a1b2c3d47890123456789abcdef0123456789abcdef0123456789abcdef4',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: '2026-10-29T08:22:00Z',
      extractedSnippet:
        'MAHARASHTRA FIRE SERVICES... Provisional Fire Safety Clearance No. MFS/P-2023/8874... Valid up to December 2026 subject to annual pump servicing...',
      allowReplace: false,
    },
    {
      id: 'DOC-006',
      requirementCode: 'EOA-SD-06',
      title: 'Demarcated Satellite Map with Geocoordinates',
      filename: 'Satellite_Demarcation_Bhuvan_Survey.pdf',
      version: 'v1 (Original)',
      fileSize: '6.40 MB',
      sha256: 'f6a1b2c3d4e57890123456789abcdef0123456789abcdef0123456789abcdef5',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: '2026-10-29T08:25:00Z',
      extractedSnippet:
        'ISRO BHUVAN GEOSPATIAL MAP OVERLAY... Boundary Coordinates: Point A: 18.5204° N, 73.8567° E; Point B: 18.5218° N, 73.8591° E... Demarcated Perimeter: 1,420 meters...',
      allowReplace: false,
    },
    {
      id: 'DOC-007',
      requirementCode: 'EOA-SD-07',
      title: 'Audited Financial Statements with ICAI UDIN',
      filename: 'Audited_Balance_Sheet_AY2025_26.pdf',
      version: 'v1 (Original)',
      fileSize: '2.95 MB',
      sha256: '01a2b3c4d5e67890123456789abcdef0123456789abcdef0123456789abcdef6',
      virusScan: 'CLEAN',
      extractionStatus: 'COMPLETED',
      uploadedAt: '2026-10-29T08:28:00Z',
      extractedSnippet:
        'INDEPENDENT AUDITOR’S REPORT... For M/s Apex Education Society... UDIN: 24056781ABCD1234... Chartered Accountants Firm Reg No. 104522W... Balance Sheet total Rs. 28,45,12,000...',
      allowReplace: false,
    },
  ];

  const filteredDocs = documents.filter((doc) => {
    const q = searchQuery.toLowerCase();
    return (
      doc.title.toLowerCase().includes(q) ||
      doc.requirementCode.toLowerCase().includes(q) ||
      doc.filename.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Institution</span>
            <span>/</span>
            <span>Evidence Vault</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Building2 className="w-6 h-6 text-primary" />
            Institutional Evidence Documents &amp; Audit Hashes
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Application: <span className="font-semibold text-foreground">{demoState.applicationNumber}</span> | Total Evidence Bundles: <span className="font-semibold text-foreground">{documents.length}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isRectified && (
            <Badge className="bg-emerald-600 text-white text-xs py-1 px-2.5">
              Revision #2 Active (1 Replacement Ingested)
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/institution/rectification')}
            className="text-xs font-medium"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Rectification Center
          </Button>
        </div>
      </div>

      {/* Lifecycle Progress Stepper */}
      <InstitutionWorkflowProgress />

      {/* Search & Filter Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
          <Input
            placeholder="Search by requirement code, title, or filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>All 7 bundles verified via SHA-256 + ClamAV</span>
        </div>
      </div>

      {/* Documents Table */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b bg-muted/50 font-semibold text-muted-foreground">
                <th className="py-3 px-4">Requirement</th>
                <th className="py-3 px-4">Document Title &amp; Filename</th>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Cryptographic SHA-256</th>
                <th className="py-3 px-4">Integrity / OCR</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredDocs.map((doc) => (
                <tr key={doc.id} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-foreground whitespace-nowrap">
                    {doc.requirementCode}
                  </td>
                  <td className="py-3 px-4">
                    <p className="font-semibold text-foreground text-xs">{doc.title}</p>
                    <p className="font-mono text-muted-foreground text-[11px] truncate max-w-xs">
                      {doc.filename}
                    </p>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={
                        doc.version.includes('Replacement')
                          ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[11px]'
                          : 'font-mono text-[11px]'
                      }
                    >
                      {doc.version}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-muted-foreground whitespace-nowrap font-mono">
                    {doc.fileSize}
                  </td>
                  <td className="py-3 px-4 font-mono text-muted-foreground text-[11px]">
                    <span className="truncate block max-w-[140px]" title={doc.sha256}>
                      {doc.sha256.slice(0, 16)}...
                    </span>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <Badge variant="outline" className="border-emerald-500 text-emerald-700 text-[10px] py-0 px-1.5 font-normal">
                        <CheckCircle2 className="w-3 h-3 mr-0.5 inline" />
                        CLEAN
                      </Badge>
                      <Badge variant="outline" className="border-primary/40 text-primary text-[10px] py-0 px-1.5 font-normal">
                        OCR OK
                      </Badge>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right whitespace-nowrap space-x-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-xs px-2"
                      onClick={() => setSelectedDocForPreview(doc)}
                      title="Inspect OCR text extraction"
                    >
                      <Eye className="w-3.5 h-3.5 mr-1" />
                      OCR Snippet
                    </Button>
                    {doc.allowReplace && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs px-2 text-primary border-primary/40 hover:bg-primary/10"
                        onClick={() => navigate('/institution/rectification')}
                        title="Open rectification upload"
                      >
                        <RefreshCw className="w-3.5 h-3.5 mr-1" />
                        Rectify
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* OCR Text Extraction Modal */}
      <Dialog
        open={Boolean(selectedDocForPreview)}
        onOpenChange={(open) => !open && setSelectedDocForPreview(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              RapidOCR Text Extraction Snippet
            </DialogTitle>
            <DialogDescription>
              Extracted plaintext layer from {selectedDocForPreview?.filename} ({selectedDocForPreview?.requirementCode})
            </DialogDescription>
          </DialogHeader>

          {selectedDocForPreview && (
            <div className="space-y-4 pt-2">
              <div className="rounded-md bg-muted/60 p-3 font-mono text-xs space-y-1 border">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version:</span>
                  <span className="font-semibold text-foreground">{selectedDocForPreview.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">SHA-256 Digest:</span>
                  <span className="font-semibold text-foreground break-all">{selectedDocForPreview.sha256}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Uploaded At:</span>
                  <span className="font-semibold text-foreground">{selectedDocForPreview.uploadedAt}</span>
                </div>
              </div>

              <div className="rounded-md border p-4 bg-background font-mono text-xs text-foreground leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">
                {selectedDocForPreview.extractedSnippet}
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedDocForPreview(null)}
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
export default InstitutionDocumentsPage;
