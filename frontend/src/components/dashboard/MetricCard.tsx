import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Files, Clock, AlertCircle, ShieldAlert, Info } from 'lucide-react';
import type { MetricCardData } from '@/types/dashboard';

interface MetricCardProps {
  metric: MetricCardData;
}

export function MetricCard({ metric }: MetricCardProps) {
  const getIconConfig = () => {
    switch (metric.iconName) {
      case 'total-apps':
        return {
          icon: Files,
          bgColor: 'bg-indigo-50',
          textColor: 'text-indigo-600',
          borderColor: 'border-indigo-100',
        };
      case 'pending':
        return {
          icon: Clock,
          bgColor: 'bg-amber-50',
          textColor: 'text-amber-600',
          borderColor: 'border-amber-100',
        };
      case 'expired':
        return {
          icon: AlertCircle,
          bgColor: 'bg-rose-50',
          textColor: 'text-rose-600',
          borderColor: 'border-rose-100',
        };
      case 'escalated':
      default:
        return {
          icon: ShieldAlert,
          bgColor: 'bg-purple-50',
          textColor: 'text-purple-600',
          borderColor: 'border-purple-100',
        };
    }
  };

  const { icon: Icon, bgColor, textColor, borderColor } = getIconConfig();

  return (
    <Card className="bg-white border-slate-200/90 shadow-2xs hover:shadow-xs transition-shadow">
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
              <span>{metric.title}</span>
              {metric.syntheticFootnote && (
                <Tooltip delayDuration={200}>
                  <TooltipTrigger asChild>
                    <span className="cursor-help text-slate-400 hover:text-slate-600">
                      <Info className="size-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="text-xs max-w-xs">
                    {metric.syntheticFootnote}
                  </TooltipContent>
                </Tooltip>
              )}
            </div>

            <div className="flex items-baseline gap-2 pt-1">
              <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-mono">
                {metric.value}
              </span>
            </div>
          </div>

          <div
            className={`flex size-10 items-center justify-center rounded-xl border ${bgColor} ${borderColor} ${textColor}`}
          >
            <Icon className="size-5" />
          </div>
        </div>

        <div className="mt-3.5 flex items-center justify-between border-t border-slate-100 pt-3">
          <p className="text-xs text-slate-500 truncate max-w-[180px] sm:max-w-none">
            {metric.subtext}
          </p>

          {metric.badge && (
            <Badge
              variant="outline"
              className={`text-[10px] h-4.5 px-1.5 font-semibold ${
                metric.badge.variant === 'warning'
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : metric.badge.variant === 'destructive'
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : metric.badge.variant === 'secondary'
                  ? 'bg-purple-50 text-purple-700 border-purple-200'
                  : 'bg-indigo-50 text-indigo-700 border-indigo-200'
              }`}
            >
              {metric.badge.label}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
