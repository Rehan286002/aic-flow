export type WorkflowCaseQuickFilter =
  | 'ALL'
  | 'DUE_SOON'
  | 'OVERDUE'
  | 'UNASSIGNED'
  | 'MY_ACTIONS';

export interface WorkflowQueueItem {
  current_stage: string;
  due_at: string | null;
  assigned_user_id: string | null;
}

const CLOSED_STAGES = new Set(['CLOSED', 'APPROVED', 'REJECTED']);
const INSTITUTION_ACTION_STAGES = new Set(['DRAFT', 'CLARIFICATION_REQUESTED']);

export function isWorkflowCaseOverdue(item: WorkflowQueueItem, nowMs = Date.now()): boolean {
  return Boolean(
    item.due_at
    && !CLOSED_STAGES.has(item.current_stage)
    && new Date(item.due_at).getTime() < nowMs,
  );
}

export function countWorkflowCasesDueWithinSevenDays(
  items: WorkflowQueueItem[],
  nowMs = Date.now(),
): number {
  const end = nowMs + 7 * 24 * 60 * 60 * 1000;
  return items.filter((item) => {
    if (!item.due_at || CLOSED_STAGES.has(item.current_stage)) return false;
    const dueMs = new Date(item.due_at).getTime();
    return dueMs >= nowMs && dueMs <= end;
  }).length;
}

export function filterWorkflowCases<T extends WorkflowQueueItem>(
  items: T[],
  filter: WorkflowCaseQuickFilter,
  nowMs = Date.now(),
): T[] {
  if (filter === 'ALL') return [...items];
  if (filter === 'OVERDUE') {
    return items.filter((item) => isWorkflowCaseOverdue(item, nowMs));
  }
  if (filter === 'DUE_SOON') {
    const end = nowMs + 7 * 24 * 60 * 60 * 1000;
    return items.filter((item) => {
      if (!item.due_at || CLOSED_STAGES.has(item.current_stage)) return false;
      const dueMs = new Date(item.due_at).getTime();
      return dueMs >= nowMs && dueMs <= end;
    });
  }
  if (filter === 'UNASSIGNED') {
    return items.filter((item) => !item.assigned_user_id && !CLOSED_STAGES.has(item.current_stage));
  }
  return items.filter((item) => INSTITUTION_ACTION_STAGES.has(item.current_stage));
}


export function workflowApplicationLinkPath(workspace: string): string {
  const paths: Record<string, string> = {
    institution: '/institution/activity',
    auditor: '/office/dossiers',
    regional: '/regional/queue',
    committee: '/committee/assigned',
    lead: '/bureau',
    admin: '/admin/overview',
  };
  return paths[workspace] || '/';
}
