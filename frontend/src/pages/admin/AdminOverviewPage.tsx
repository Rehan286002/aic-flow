import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Server,
  Network,
  Sliders,
  RefreshCw,
  Lock,
} from 'lucide-react';
import { toast } from 'sonner';

export default function AdminOverviewPage() {
  const handleConnectorPing = (name: string) => {
    toast.success(`Connector Ping: ${name}`, {
      description: 'Simulated sandbox responded with HTTP 200 (Latency: 42ms).',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Platform & Regulatory Engine Administration
            </h1>
            <Badge variant="outline" className="text-xs font-semibold bg-slate-100 text-slate-800 border-slate-300">
              System Admin
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            System Operations, Rule Versioning, and Simulated Connector Orchestration
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => handleConnectorPing('All Services')}
            variant="outline"
            className="h-8 text-xs border-slate-200 text-slate-700"
          >
            <RefreshCw className="size-3.5 mr-1.5" />
            <span>Ping Connectors</span>
          </Button>

          <Button
            size="sm"
            onClick={() => toast.info('Rule Configuration Editor: Annexure 2.1 Rule Engine v4.2 active.')}
            className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Sliders className="size-3.5 mr-1.5" />
            <span>Rule Configuration</span>
          </Button>
        </div>
      </div>

      {/* Admin Isolation Callout */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-700 flex items-start gap-3 shadow-2xs">
        <Lock className="size-4.5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <div className="font-semibold text-slate-900">
            Mandatory Role Isolation Policy (AGENTS.md & Schema v4)
          </div>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            Platform Administrators manage user access, rule versioning, and external issuer connectors.
            In compliance with AICTE regulatory isolation boundaries, Administrator accounts do not automatically
            possess read/write access to confidential institutional application documents or finding notes.
          </p>
        </div>
      </div>

      {/* Health & Connectors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Simulated Connectors */}
        <Card className="bg-white border-slate-200/90 shadow-2xs">
          <CardHeader className="p-4 sm:p-5 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                  <Network className="size-4 text-indigo-600" />
                  <span>Simulated Issuer Connectors</span>
                </CardTitle>
                <CardDescription className="text-xs text-slate-500 mt-0.5">
                  Sandboxes providing synthetic verification signals for Annexure 2.1
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200">
                4 Active
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-4 sm:p-5 divide-y divide-slate-100 text-xs">
            <div className="py-2.5 first:pt-0 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">DigiLocker Academic Sandbox</span>
                <p className="text-[11px] text-slate-500">Affidavit & certificate digital signature validation</p>
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => handleConnectorPing('DigiLocker Sandbox')}
                className="h-6 text-[11px] text-indigo-600 hover:bg-indigo-50"
              >
                Simulated OK
              </Button>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">State Cadastral Land Registry</span>
                <p className="text-[11px] text-slate-500">Ownership title & land acreage cross-reference</p>
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => handleConnectorPing('Land Registry')}
                className="h-6 text-[11px] text-indigo-600 hover:bg-indigo-50"
              >
                Simulated OK
              </Button>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">State GIS Satellite Map Gateway</span>
                <p className="text-[11px] text-slate-500">Cadastral boundary coordinate reconciliation</p>
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => handleConnectorPing('State GIS')}
                className="h-6 text-[11px] text-indigo-600 hover:bg-indigo-50"
              >
                Simulated OK
              </Button>
            </div>

            <div className="py-2.5 last:pb-0 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">Bank UTR Reconciliation API</span>
                <p className="text-[11px] text-slate-500">Extension of Approval fee transaction validation</p>
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => handleConnectorPing('Bank Gateway')}
                className="h-6 text-[11px] text-indigo-600 hover:bg-indigo-50"
              >
                Simulated OK
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Infrastructure & Storage Status */}
        <Card className="bg-white border-slate-200/90 shadow-2xs">
          <CardHeader className="p-4 sm:p-5 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                  <Server className="size-4 text-indigo-600" />
                  <span>Regulatory Platform Services</span>
                </CardTitle>
                <CardDescription className="text-xs text-slate-500 mt-0.5">
                  Target stack services configured for AIC-Flow
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-[10px] bg-indigo-50 text-indigo-700 border-indigo-200">
                Stack Ready
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-4 sm:p-5 divide-y divide-slate-100 text-xs">
            <div className="py-2.5 first:pt-0 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">PostgreSQL 18</span>
                <p className="text-[11px] text-slate-500">AICTE Regulatory Schema v4 Reference</p>
              </div>
              <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-semibold">
                Reference Ready
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">FastAPI Backend Service</span>
                <p className="text-[11px] text-slate-500">Python 3.12 + SQLAlchemy 2.0</p>
              </div>
              <span className="text-[11px] font-mono text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded font-semibold">
                Configured
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">DocIntel Worker (PaddleOCR)</span>
                <p className="text-[11px] text-slate-500">PDF text extraction, pHash & bounding boxes</p>
              </div>
              <span className="text-[11px] font-mono text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded font-semibold">
                Configured
              </span>
            </div>

            <div className="py-2.5 last:pb-0 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-800">Private Document Quarantine</span>
                <p className="text-[11px] text-slate-500">SHA-256 immutable submission storage</p>
              </div>
              <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-semibold">
                Quarantined
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
