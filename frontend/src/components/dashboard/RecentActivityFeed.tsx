import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { SYNTHETIC_RECENT_ACTIVITY } from '@/features/dashboard/fixtures/auditor-dashboard-fixture';
import { History, FileCheck2, AlertTriangle, Cpu, ArrowUpRight, Database } from 'lucide-react';

export function RecentActivityFeed() {
  const activities = SYNTHETIC_RECENT_ACTIVITY;

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'verification':
        return <FileCheck2 className="size-3.5 text-emerald-600" />;
      case 'flag':
        return <AlertTriangle className="size-3.5 text-amber-600" />;
      case 'document':
        return <Cpu className="size-3.5 text-indigo-600" />;
      case 'escalation':
        return <ArrowUpRight className="size-3.5 text-purple-600" />;
      case 'system':
      default:
        return <Database className="size-3.5 text-teal-600" />;
    }
  };

  return (
    <Card className="bg-white border-slate-200/90 shadow-2xs">
      <CardHeader className="p-4 sm:p-5 pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
              <History className="size-4 text-indigo-600" />
              <span>Real-Time Audit Activity</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Audit event ledger and document verification pipeline signals
            </CardDescription>
          </div>
          <span className="size-2 rounded-full bg-emerald-500 animate-pulse" title="Live Pipeline Active" />
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 pt-0">
        <div className="relative pl-5 space-y-4 border-l-2 border-slate-100 my-1">
          {activities.map((act) => (
            <div key={act.id} className="relative group text-xs">
              {/* Dot on the timeline */}
              <div className="absolute -left-[27px] top-0.5 flex size-5 items-center justify-center rounded-full bg-white border border-slate-200 shadow-2xs">
                {getActivityIcon(act.type)}
              </div>

              <div className="space-y-0.5">
                <div className="flex items-center justify-between gap-1">
                  <span className="font-semibold text-slate-800 leading-tight">
                    {act.title}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono shrink-0">
                    {act.timeAgo}
                  </span>
                </div>

                <p className="text-[11px] text-slate-600 leading-relaxed">
                  {act.description}
                </p>

                <div className="flex items-center gap-2 pt-0.5 text-[10px]">
                  <span className="font-medium text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
                    {act.actor}
                  </span>
                  {act.ruleCode && (
                    <span className="font-mono text-indigo-700 bg-indigo-50 px-1 rounded font-semibold">
                      {act.ruleCode}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
