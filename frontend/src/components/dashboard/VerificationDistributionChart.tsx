import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { SYNTHETIC_VERIFICATION_STATUS_DATA } from '@/features/dashboard/fixtures/auditor-dashboard-fixture';

interface TooltipPayloadItem {
  name: string;
  value: number;
  payload: {
    category: string;
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
        <div className="font-semibold text-slate-900">{data.category}</div>
        <div className="mt-1 flex items-center justify-between gap-4 text-slate-600">
          <span>Evaluated Rules:</span>
          <span className="font-bold text-slate-900 font-mono">{data.count} items</span>
        </div>
        <div className="flex items-center justify-between gap-4 text-slate-500 text-[11px]">
          <span>Coverage:</span>
          <span className="font-mono">{data.percentage}%</span>
        </div>
      </div>
    );
  }
  return null;
}

export function VerificationDistributionChart() {
  const data = SYNTHETIC_VERIFICATION_STATUS_DATA;
  const totalEvaluations = data.reduce((acc, curr) => acc + curr.count, 0);

  return (
    <Card className="bg-white border-slate-200/90 shadow-2xs">
      <CardHeader className="p-4 sm:p-5 pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-900">
              Evidence Verification Distribution
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Automated rule outcomes across Annexure 2.1 evidence categories
            </CardDescription>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
            {totalEvaluations} Evidence Signals
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 pt-2">
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-center">
          {/* Donut Chart */}
          <div className="sm:col-span-5 h-48 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip content={<CustomTooltip />} />
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="count"
                  nameKey="category"
                >
                  {data.map((entry) => (
                    <Cell key={entry.category} fill={entry.color} stroke="#ffffff" strokeWidth={2} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            {/* Center metric */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xl font-bold font-mono text-slate-900">68.1%</span>
              <span className="text-[10px] uppercase font-semibold text-emerald-700 tracking-wider">
                Compliant
              </span>
            </div>
          </div>

          {/* Status Breakdown List */}
          <div className="sm:col-span-7 space-y-2.5">
            {data.map((item) => (
              <div key={item.category} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 font-medium text-slate-700">
                    <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="truncate">{item.category}</span>
                  </span>
                  <span className="font-mono text-slate-900 font-semibold text-xs">
                    {item.count} <span className="text-slate-400 font-normal text-[11px]">({item.percentage}%)</span>
                  </span>
                </div>

                {/* Mini progress bar */}
                <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${item.percentage}%`,
                      backgroundColor: item.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Annexure 2.1 Scope Notice */}
        <div className="mt-3 border-t border-slate-100 pt-3 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Rules EOA-SD-01 through EOA-SD-07</span>
          <span className="text-indigo-600 font-medium">Annexure 2.1 Engine Active</span>
        </div>
      </CardContent>
    </Card>
  );
}
