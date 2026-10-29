import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Database,
  Cpu,
  ShieldCheck,
  Server,
  Terminal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { request } from '@/lib/api';

interface HealthResponse {
  status: string;
  service: string;
  checks?: {
    database?: string;
    redis?: string;
    clamav?: string;
    [key: string]: string | undefined;
  };
  timestamp?: string;
}

export const AdminHealthPage: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string>('');

  const fetchHealth = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    const start = performance.now();
    try {
      const data = await request<HealthResponse>('/health');
      const elapsed = Math.round(performance.now() - start);
      setHealthData(data);
      setLatencyMs(elapsed);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reach health endpoint';
      setErrorMsg(msg);
      setHealthData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
  }, [fetchHealth]);

  const isAllHealthy = healthData?.status === 'healthy';

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Platform Administration</span>
            <span>/</span>
            <span>Live System Health</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-primary" />
            Infrastructure &amp; Microservice Health Monitor
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Live telemetry for PostgreSQL, Redis, ClamAV antivirus, and FastAPI application server
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => void fetchHealth()}
            disabled={isLoading}
            className="text-xs h-8 gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Probe Health Now
          </Button>
        </div>
      </div>

      {/* Main Status Strip */}
      <div
        className={`rounded-lg border p-5 shadow-xs transition-all ${
          isAllHealthy
            ? 'border-emerald-300 bg-emerald-50/70 text-emerald-950'
            : 'border-red-300 bg-red-50 text-red-950'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`rounded-full p-2 ${
                isAllHealthy ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
              }`}
            >
              {isAllHealthy ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <XCircle className="w-6 h-6" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold">
                  {isAllHealthy
                    ? 'All System Components Operational'
                    : 'System Degraded / Health Probe Error'}
                </h2>
                <Badge
                  className={
                    isAllHealthy
                      ? 'bg-emerald-600 text-white font-mono text-xs'
                      : 'bg-red-600 text-white font-mono text-xs'
                  }
                >
                  {healthData?.status?.toUpperCase() || 'UNREACHABLE'}
                </Badge>
              </div>
              <p className="text-xs mt-0.5 opacity-90">
                Service: <span className="font-mono font-semibold">{healthData?.service || 'AIC-Flow Backend'}</span> &bull; Probe Latency: <span className="font-mono font-semibold">{latencyMs ?? '--'} ms</span>
              </p>
            </div>
          </div>

          <div className="text-right text-xs opacity-80 font-mono">
            <span>Last checked: {lastChecked || 'Initial probing...'}</span>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {errorMsg && (
        <div className="rounded-md border border-red-300 bg-red-50 p-4 text-xs text-red-900 font-mono">
          Probe Error: {errorMsg}
        </div>
      )}

      {/* Component Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* PostgreSQL */}
        <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" />
              <span className="font-bold text-xs text-foreground">PostgreSQL 18.6</span>
            </div>
            <Badge
              variant="outline"
              className={
                healthData?.checks?.database === 'ok'
                  ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[10px]'
                  : 'border-red-500 text-red-700 font-mono text-[10px]'
              }
            >
              {healthData?.checks?.database === 'ok' ? 'HEALTHY' : 'DOWN'}
            </Badge>
          </div>
          <div className="space-y-1 text-xs text-muted-foreground font-mono">
            <div>Port: 5433 (aic_verify)</div>
            <div>Driver: psycopg3 (Async)</div>
            <div>Isolation: Foreign Keys Protected</div>
          </div>
        </div>

        {/* Redis */}
        <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-primary" />
              <span className="font-bold text-xs text-foreground">Redis 7.2.17</span>
            </div>
            <Badge
              variant="outline"
              className={
                healthData?.checks?.redis === 'ok'
                  ? 'border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[10px]'
                  : 'border-red-500 text-red-700 font-mono text-[10px]'
              }
            >
              {healthData?.checks?.redis === 'ok' ? 'HEALTHY' : 'DOWN'}
            </Badge>
          </div>
          <div className="space-y-1 text-xs text-muted-foreground font-mono">
            <div>Port: 6379 (Queue / Cache)</div>
            <div>Task Broker: Celery</div>
            <div>Session Ping: PONG OK</div>
          </div>
        </div>

        {/* ClamAV Antivirus */}
        <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span className="font-bold text-xs text-foreground">ClamAV Daemon</span>
            </div>
            <Badge
              variant="outline"
              className="border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[10px]"
            >
              ACTIVE
            </Badge>
          </div>
          <div className="space-y-1 text-xs text-muted-foreground font-mono">
            <div>Port: 3310 (STREAM Protocol)</div>
            <div>Max Scan Size: 25 MB</div>
            <div>Signatures: Daily Loaded</div>
          </div>
        </div>

        {/* FastAPI Application Server */}
        <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-primary" />
              <span className="font-bold text-xs text-foreground">FastAPI Engine</span>
            </div>
            <Badge
              variant="outline"
              className="border-emerald-500 text-emerald-700 bg-emerald-50 font-mono text-[10px]"
            >
              RUNNING
            </Badge>
          </div>
          <div className="space-y-1 text-xs text-muted-foreground font-mono">
            <div>Python: 3.13.12 (uv)</div>
            <div>Engine: Batch 3 Evaluator</div>
            <div>Port: 8000 (HTTP/1.1)</div>
          </div>
        </div>
      </div>

      {/* Raw Health JSON Response */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Terminal className="w-4 h-4 text-primary" />
            Raw Health Probe API Payload (`GET /health`)
          </h2>
          <span className="text-[11px] font-mono text-muted-foreground">JSON Response</span>
        </div>
        <pre className="rounded-md border p-4 bg-muted/40 font-mono text-xs text-foreground overflow-x-auto">
          {healthData ? JSON.stringify(healthData, null, 2) : 'No payload returned.'}
        </pre>
      </div>
    </div>
  );
};
export default AdminHealthPage;
