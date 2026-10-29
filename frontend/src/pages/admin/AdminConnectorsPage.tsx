import React, { useState } from 'react';
import {
  Database,
  Radio,
  CheckCircle2,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface SourceConnectorInfo {
  code: string;
  name: string;
  authority: string;
  category: string;
  endpointUrl: string;
  authMode: string;
  timeoutMs: number;
  provenance: 'SIMULATED';
  snapshotHash: string;
  lastSyncAt: string;
}

export const AdminConnectorsPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [pingStatus, setPingStatus] = useState<Record<string, { status: string; latencyMs: number }>>({});
  const [pingingCode, setPingingCode] = useState<string | null>(null);

  const connectors: SourceConnectorInfo[] = [
    {
      code: 'SRC_AICTE_PORTAL',
      name: 'AICTE Institutional Web-Portal Registry',
      authority: 'All India Council for Technical Education',
      category: 'INSTITUTION_PROFILE',
      endpointUrl: 'https://sim.aicte-india.org/api/v4/institutions/1-10948201',
      authMode: 'MUTUAL_TLS_BEARER',
      timeoutMs: 3500,
      provenance: 'SIMULATED',
      snapshotHash: 'a7f9e8d3ac7447388099218284ad4ed8721c54b38d492048f7294bb827104812',
      lastSyncAt: '2026-10-29T08:00:00Z',
    },
    {
      code: 'SRC_REVENUE_LAND',
      name: 'State Land & Revenue Records (Bhoomi / Mahabhulekh)',
      authority: 'State Revenue & Disaster Management Department',
      category: 'LAND_TITLE',
      endpointUrl: 'https://sim.landrecords.gov.in/api/v2/cadastral/survey/74-2A',
      authMode: 'API_KEY_HMAC',
      timeoutMs: 5000,
      provenance: 'SIMULATED',
      snapshotHash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
      lastSyncAt: '2026-10-29T08:00:00Z',
    },
    {
      code: 'SRC_MUNICIPAL_BLDG',
      name: 'Municipal Corporation Building Sanction Authority',
      authority: 'Pune Municipal Corporation Town Planning Dept',
      category: 'INFRASTRUCTURE',
      endpointUrl: 'https://sim.pmc.gov.in/api/v1/building-permissions/PMC-BP-1990-1142',
      authMode: 'OAUTH2_CLIENT_CREDS',
      timeoutMs: 4000,
      provenance: 'SIMULATED',
      snapshotHash: '6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090',
      lastSyncAt: '2026-10-29T08:00:00Z',
    },
    {
      code: 'SRC_FIRE_SERVICES',
      name: 'State Fire Services Directorate Clearance Registry',
      authority: 'Directorate of Maharashtra Fire Services',
      category: 'LIFE_SAFETY',
      endpointUrl: 'https://sim.fireservices.mah.gov.in/api/noc-verify/MFS-P-2023-8874',
      authMode: 'BEARER_TOKEN',
      timeoutMs: 4000,
      provenance: 'SIMULATED',
      snapshotHash: 'bcae56e22dd318d189ced5952f1e0df1e15fa52bf658826703f8a4cb75d1d648',
      lastSyncAt: '2026-10-29T08:00:00Z',
    },
    {
      code: 'SRC_ICAI_UDIN',
      name: 'ICAI Chartered Accountants UDIN Verification Portal',
      authority: 'Institute of Chartered Accountants of India',
      category: 'FINANCIAL_INTEGRITY',
      endpointUrl: 'https://sim.udin.icai.org/api/v1/verify/24056781ABCD1234',
      authMode: 'X509_CERTIFICATE',
      timeoutMs: 3000,
      provenance: 'SIMULATED',
      snapshotHash: '5b922079de9ff9c025d50616999a01fdbe152f281260492cb47065ffef6b86cd',
      lastSyncAt: '2026-10-29T08:00:00Z',
    },
    {
      code: 'SRC_BHUVAN_GEOMAP',
      name: 'ISRO Bhuvan Satellite Geospatial Overlay Registry',
      authority: 'National Remote Sensing Centre (ISRO)',
      category: 'GEOSPATIAL',
      endpointUrl: 'https://sim.bhuvan.nrsc.gov.in/api/v3/wms/cadastral-overlay',
      authMode: 'BEARER_TOKEN',
      timeoutMs: 6000,
      provenance: 'SIMULATED',
      snapshotHash: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      lastSyncAt: '2026-10-29T08:00:00Z',
    },
  ];

  const handlePing = (code: string) => {
    setPingingCode(code);
    setTimeout(() => {
      const mockLatency = Math.floor(45 + Math.random() * 40);
      setPingStatus((prev) => ({
        ...prev,
        [code]: { status: '200 OK', latencyMs: mockLatency },
      }));
      setPingingCode(null);
    }, 400);
  };

  const filteredConnectors = connectors.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.code.toLowerCase().includes(q) ||
      c.name.toLowerCase().includes(q) ||
      c.authority.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Platform Administration</span>
            <span>/</span>
            <span>External Source Connectors</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Database className="w-6 h-6 text-primary" />
            Registered External Source Connectors
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Authoritative registry mock endpoints underpinning AIC-Flow independent multi-source triangulation
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-emerald-400 text-emerald-700 bg-emerald-50 py-1 px-3 self-start sm:self-auto">
          6 Registered Connectors &bull; [SIMULATED]
        </Badge>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
        <Input
          placeholder="Search connectors by code, authority, or category..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 text-sm"
        />
      </div>

      {/* Connector Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredConnectors.map((connector) => {
          const ping = pingStatus[connector.code];
          const isPinging = pingingCode === connector.code;

          return (
            <div
              key={connector.code}
              className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4 transition-all hover:border-primary/40"
            >
              <div className="flex items-start justify-between gap-2 border-b pb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono font-bold text-xs bg-primary/10 text-primary px-2 py-0.5 rounded border border-primary/20">
                      {connector.code}
                    </span>
                    <Badge variant="outline" className="text-[10px] font-mono border-amber-300 text-amber-700 bg-amber-50">
                      {connector.provenance}
                    </Badge>
                  </div>
                  <h2 className="text-sm font-bold text-foreground">
                    {connector.name}
                  </h2>
                  <span className="text-xs text-muted-foreground block">
                    {connector.authority}
                  </span>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  disabled={isPinging}
                  onClick={() => handlePing(connector.code)}
                  className="h-7 text-xs font-mono shrink-0"
                >
                  <Radio className={`w-3 h-3 mr-1 ${isPinging ? 'animate-pulse text-primary' : ''}`} />
                  {isPinging ? 'Pinging...' : 'Test Ping'}
                </Button>
              </div>

              {/* Endpoint Details */}
              <div className="space-y-1.5 font-mono text-[11px] text-muted-foreground">
                <div className="flex justify-between border-b pb-1">
                  <span>Endpoint:</span>
                  <span className="text-foreground truncate max-w-[240px]" title={connector.endpointUrl}>
                    {connector.endpointUrl}
                  </span>
                </div>
                <div className="flex justify-between border-b pb-1">
                  <span>Authentication:</span>
                  <span className="text-foreground font-semibold">{connector.authMode}</span>
                </div>
                <div className="flex justify-between border-b pb-1">
                  <span>Timeout:</span>
                  <span className="text-foreground">{connector.timeoutMs} ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Snapshot SHA-256:</span>
                  <span className="text-emerald-700 font-bold truncate max-w-[200px]" title={connector.snapshotHash}>
                    {connector.snapshotHash.slice(0, 16)}...
                  </span>
                </div>
              </div>

              {/* Ping Result Bar */}
              {ping && (
                <div className="flex items-center justify-between p-2 rounded bg-muted/40 border text-xs font-mono">
                  <div className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Ping Response: {ping.status}</span>
                  </div>
                  <span className="text-muted-foreground">RTT: {ping.latencyMs} ms</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default AdminConnectorsPage;
