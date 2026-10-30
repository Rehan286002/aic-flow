import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCheck, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { workflowApi, type WorkflowNotification } from '@/features/workflow/api';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { workflowApplicationLinkPath } from '@/features/workflow/filters';

export function NotificationPopover() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [notifications, setNotifications] = useState<WorkflowNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'unread'>('all');
  const [loading, setLoading] = useState(false);
  const unreadCount = notifications.filter((n) => !n.read_at).length;

  const refresh = async () => {
    setLoading(true);
    try { setNotifications(await workflowApi.notifications()); }
    catch { /* Notification centre is supplementary; the workflow page displays API errors. */ }
    finally { setLoading(false); }
  };

  useEffect(() => { void refresh(); }, []);
  useEffect(() => { if (open) void refresh(); }, [open]);

  const markRead = async (id: string) => {
    try {
      const updated = await workflowApi.markRead(id);
      setNotifications((prev) => prev.map((n) => n.notification_id === id ? updated : n));
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Could not update notification.'); }
  };

  const markAllRead = async () => {
    const unread = notifications.filter((n) => !n.read_at);
    for (const item of unread) await markRead(item.notification_id);
    toast.success('Notifications updated.');
  };

  const openNotification = (notification: WorkflowNotification) => {
    if (!notification.read_at) void markRead(notification.notification_id);
    if (!notification.application_id) return;
    const workspace = auth.activeWorkspace || 'auditor';
    const destination = workflowApplicationLinkPath(workspace);
    setOpen(false);
    navigate(destination + '?applicationId=' + encodeURIComponent(notification.application_id));
  };

  const filtered = notifications.filter((n) => activeTab === 'all' || !n.read_at);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="icon-sm" className="relative text-slate-700 bg-white border-slate-200 hover:bg-slate-50" aria-label={`Open notifications (${unreadCount} unread)`}>
          <Bell className="size-4" />
          {unreadCount > 0 && <span className="absolute -top-1 -right-1 flex size-4 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white shadow-xs">{unreadCount > 9 ? '9+' : unreadCount}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 sm:w-96 p-0 shadow-lg border-slate-200">
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 bg-slate-50/70">
          <div className="flex items-center gap-2"><h4 className="font-semibold text-sm text-slate-900">Notifications</h4><Badge variant={unreadCount ? 'destructive' : 'secondary'} className="h-5 px-1.5 text-[10px]">{unreadCount} unread</Badge></div>
          {unreadCount > 0 && <Button variant="ghost" size="xs" onClick={() => void markAllRead()} className="text-xs text-muted-foreground hover:text-foreground h-6 px-1.5"><CheckCheck className="size-3 mr-1"/>Mark read</Button>}
        </div>
        <div className="flex border-b border-slate-100 px-3 py-1.5 text-xs gap-2 bg-white">
          <button type="button" onClick={() => setActiveTab('all')} className={`px-2.5 py-1 rounded-md font-medium ${activeTab === 'all' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600'}`}>All ({notifications.length})</button>
          <button type="button" onClick={() => setActiveTab('unread')} className={`px-2.5 py-1 rounded-md font-medium ${activeTab === 'unread' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600'}`}>Unread ({unreadCount})</button>
        </div>
        <ScrollArea className="max-h-[340px]">
          {filtered.length === 0 ? <div className="p-8 text-center text-xs text-muted-foreground"><CheckCircle2 className="size-8 text-emerald-500 mx-auto mb-2 opacity-80"/><p className="font-medium text-slate-700">{loading ? 'Loading notifications…' : 'No notifications'}</p><p className="mt-1 text-slate-500">Case events and operational updates appear here.</p></div> : <div className="divide-y divide-slate-100">{filtered.map((n) => <button type="button" key={n.notification_id} onClick={() => openNotification(n)} className={`flex w-full items-start gap-3 p-3 text-left text-xs transition-colors hover:bg-slate-50 ${!n.read_at ? 'bg-indigo-50/30' : ''}`}><div className="mt-0.5 shrink-0">{n.severity === 'WARNING' ? <AlertCircle className="size-4 text-amber-600"/> : <Info className="size-4 text-indigo-600"/>}</div><div className="flex-1 space-y-0.5"><span className="font-semibold text-slate-900">{n.title}</span><p className="text-slate-600 text-[11px] leading-relaxed">{n.body}</p><span className="text-[10px] text-slate-400">{new Date(n.created_at).toLocaleString()}</span>{n.application_id && <span className="mt-1 block text-[10px] font-semibold text-indigo-700">Open application</span>}</div>{!n.read_at && <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-indigo-600"/>}</button>)}</div>}
        </ScrollArea>
        <div className="border-t border-slate-100 bg-slate-50 px-3 py-2 text-[10px] text-center text-slate-500">AIC-Flow · Persistent case notifications</div>
      </PopoverContent>
    </Popover>
  );
}
