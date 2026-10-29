import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { SYNTHETIC_APPLICATION_STATUS_DATA } from '@/features/dashboard/fixtures/auditor-dashboard-fixture';

interface TooltipPayloadItem {
  name: string;
  value: number;
  payload: {
    status: string;
    count: number;
    percentage: number;
    color: string;
  };
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload;
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-md text-xs">
        <div className="font-semibold text-slate-900">{data.status}</div>
        <div className="mt-1 flex items-center justify-between gap-4 text-slate-600">
          <span>Application Count:</span>
          <span className="font-bold text-slate-900 font-mono">{data.count}</span>
        </div>
        <div className="flex items-center justify-between gap-4 text-slate-500 text-[11px]">
          <span>Proportion:</span>
          <span className="font-mono">{data.percentage}%</span>
        </div>
      </div>
    );
  }
  return null;
}

export function StatusDistributionChart() {
  const data = SYNTHETIC_APPLICATION_STATUS_DATA;

  return (
    <Card className="bg-white border-slate-200/90 shadow-2xs">
      <CardHeader className="p-4 sm:p-5 pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-900">
              Application Status Distribution
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Current queue progression for AY 2026-27 Extension of Approval cases
            </CardDescription>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
            42 Total
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 pt-2">
        <div className="h-52 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <XAxis
                dataKey="status"
                tick={{ fontSize: 11, fill: '#64748B' }}
                axisLine={{ stroke: '#E2E8F0' }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: '#64748B' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F1F5F9' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={42}>
                {data.map((entry) => (
                  <Cell key={entry.status} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Status Breakdown Legend */}
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-5 gap-2 border-t border-slate-100 pt-3">
          {data.map((item) => (
            <div key={item.status} className="flex flex-col">
              <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                <span className="size-2 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="truncate">{item.status}</span>
              </div>
              <span className="font-mono text-xs font-semibold text-slate-800 ml-3.5">
                {item.count} <span className="text-[10px] text-slate-400">({item.percentage}%)</span>
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
