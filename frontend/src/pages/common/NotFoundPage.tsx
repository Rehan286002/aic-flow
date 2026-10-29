import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center p-6">
      <div className="flex size-16 items-center justify-center rounded-2xl bg-white mb-4 p-2 border border-slate-200 shadow-sm">
        <img src="/aic-flow.svg" alt="AIC-Flow Logo" className="size-full object-contain" />
      </div>

      <h1 className="text-xl font-bold tracking-tight text-slate-900">
        Regulatory Route Not Found
      </h1>

      <p className="mt-2 text-xs sm:text-sm text-slate-500 max-w-md leading-relaxed">
        The requested application endpoint does not exist or has been relocated within the AIC-Flow workspace.
      </p>

      <div className="mt-6 flex items-center gap-3">
        <Button asChild size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs h-8">
          <Link to="/auditor/dashboard">
            <ArrowLeft className="size-3.5 mr-1.5" />
            <span>Return to Auditor Dashboard</span>
          </Link>
        </Button>
      </div>
    </div>
  );
}
