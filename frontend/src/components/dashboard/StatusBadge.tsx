import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  AlertCircle,
  ArrowUpRight,
  HelpCircle,
  MinusCircle,
} from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  label?: string;
  size?: 'sm' | 'default';
}

export function StatusBadge({ status, label, size = 'default' }: StatusBadgeProps) {
  const displayLabel = label || status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const textSize = size === 'sm' ? 'text-[10px] h-4.5 px-1.5' : 'text-xs h-5 px-2';

  switch (status.toLowerCase()) {
    case 'draft':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-slate-100 text-slate-800 border-slate-300 gap-1`}
        >
          <Clock className="size-3 text-slate-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'submitted':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-blue-50 text-blue-800 border-blue-200 gap-1`}
        >
          <CheckCircle2 className="size-3 text-blue-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'applicable':
    case 'validated':
    case 'verified':
    case 'satisfied':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-emerald-50 text-emerald-800 border-emerald-200 gap-1`}
        >
          <CheckCircle2 className="size-3 text-emerald-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'under_review':
    case 'in_progress':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-indigo-50 text-indigo-800 border-indigo-200 gap-1`}
        >
          <Clock className="size-3 text-indigo-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'pending':
    case 'pending_determination':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-amber-50 text-amber-800 border-amber-200 gap-1`}
        >
          <Clock className="size-3 text-amber-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'rectification':
    case 'rectification_requested':
    case 'action_required':
    case 'flagged':
    case 'discrepancy':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-amber-50 text-amber-800 border-amber-300 gap-1`}
        >
          <AlertTriangle className="size-3 text-amber-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'deficient':
    case 'expired':
    case 'missing':
    case 'critical':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-rose-50 text-rose-800 border-rose-200 gap-1`}
        >
          <AlertCircle className="size-3 text-rose-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'not_applicable':
    case 'not applicable':
    case 'na':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-slate-100 text-slate-600 border-slate-200 gap-1`}
        >
          <MinusCircle className="size-3 text-slate-400" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'escalated':
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-purple-50 text-purple-800 border-purple-200 gap-1`}
        >
          <ArrowUpRight className="size-3 text-purple-600" />
          <span>{displayLabel}</span>
        </Badge>
      );

    case 'undetermined':
    case 'unable_to_determine':
    default:
      return (
        <Badge
          variant="outline"
          className={`${textSize} font-semibold bg-slate-100 text-slate-700 border-slate-200 gap-1`}
        >
          <HelpCircle className="size-3 text-slate-500" />
          <span>{displayLabel}</span>
        </Badge>
      );
  }
}
