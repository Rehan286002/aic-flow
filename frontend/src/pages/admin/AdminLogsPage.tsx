import React, { useState } from 'react';
import {
  Search,
  Terminal,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface SystemLogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'SECURITY';
  actor: string;
  ipAddress: string;
  eventType: string;
  message: string;
}

export const AdminLogsPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const logs: SystemLogEntry[] = [
    {
      id: 'LOG-1092',
      timestamp: '2026-10-29 09:30:15',
      level: 'INFO',
      actor: 'Vikram Rao (Auditor)',
      ipAddress: '10.14.22.4',
      eventType: 'FINDING_STATUS_MUTATION',
      message: 'Finding FIND-DEMO-04 transitioned to CLARIFICATION_REQUESTED for requirement EOA-SD-04.',
    },
    {
      id: 'LOG-1091',
      timestamp: '2026-10-29 09:00:04',
      level: 'INFO',
      actor: 'VALIDATION_ENGINE',
      ipAddress: '127.0.0.1',
      eventType: 'VALIDATION_RUN_COMPLETED',
      message: 'Batch 3 Validation Engine completed run 5822d8f2: 4 Deficient, 3 Unable to determine.',
    },
    {
      id: 'LOG-1090',
      timestamp: '2026-10-29 08:30:12',
      level: 'SECURITY',
      actor: 'Dr. Anil Sharma (Institution)',
      ipAddress: '115.111.45.88',
      eventType: 'APPLICATION_SUBMISSION',
      message: 'Self-disclosure application APP-2026-EOA-0023 submitted for AY 2026-27 (Revision 1).',
    },
    {
      id: 'LOG-1089',
      timestamp: '2026-10-29 08:28:45',
      level: 'INFO',
      actor: 'SYSTEM_ANTIVIRUS',
      ipAddress: '127.0.0.1:3310',
      eventType: 'CLAMAV_SCAN_CLEAN',
      message: 'Document stream scan passed (OK): Audited_Balance_Sheet_AY2025_26.pdf (0 viruses found).',
    },
    {
      id: 'LOG-1088',
      timestamp: '2026-10-29 07:55:10',
      level: 'SECURITY',
      actor: 'Rajesh Mehta (Admin)',
      ipAddress: '10.14.10.1',
      eventType: 'ADMIN_SESSION_AUTHENTICATED',
      message: 'Successful credential login with CSRF token issuance from secure internal subnet.',
    },
  ];

  const filteredLogs = logs.filter((l) => {
    const q = searchQuery.toLowerCase();
    return (
      l.eventType.toLowerCase().includes(q) ||
      l.actor.toLowerCase().includes(q) ||
      l.message.toLowerCase().includes(q)
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
            <span>Security Audit Logs</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Terminal className="w-6 h-6 text-primary" />
            Security &amp; Operational Audit Log Stream
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Immutable log stream recording authentication events, evaluator runs, virus scans, and triage actions
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary py-1 px-3 self-start sm:self-auto">
          Audit Stream Active
        </Badge>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
        <Input
          placeholder="Filter logs by event type, actor, or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 text-sm"
        />
      </div>

      {/* Logs Table */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b bg-muted/40 font-semibold text-muted-foreground">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Level</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Actor &amp; Subnet</th>
                <th className="py-3 px-4">Audit Payload Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-muted/30 transition-colors font-mono">
                  <td className="py-3 px-4 whitespace-nowrap text-muted-foreground text-[11px]">
                    {log.timestamp}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={
                        log.level === 'SECURITY'
                          ? 'border-purple-400 text-purple-700 bg-purple-50 text-[10px]'
                          : log.level === 'WARN'
                          ? 'border-amber-400 text-amber-700 bg-amber-50 text-[10px]'
                          : 'border-emerald-400 text-emerald-700 bg-emerald-50 text-[10px]'
                      }
                    >
                      {log.level}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap font-bold text-foreground text-xs">
                    {log.eventType}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap text-muted-foreground text-[11px]">
                    <span className="text-foreground block">{log.actor}</span>
                    <span className="text-[10px] text-muted-foreground">{log.ipAddress}</span>
                  </td>
                  <td className="py-3 px-4 text-foreground text-xs font-sans">
                    {log.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default AdminLogsPage;
