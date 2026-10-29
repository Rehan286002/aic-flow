export interface MetricCardData {
  id: string;
  title: string;
  value: number | string;
  subtext: string;
  badge?: {
    label: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'warning' | 'success';
  };
  iconName: 'total-apps' | 'pending' | 'expired' | 'escalated';
  syntheticFootnote?: string;
}

export interface ApplicationStatusStat {
  status: string;
  count: number;
  color: string;
  percentage: number;
}

export interface VerificationRuleStat {
  category: string;
  status: 'verified' | 'flagged' | 'expired' | 'undetermined';
  count: number;
  percentage: number;
  color: string;
}

export interface RecentApplication {
  id: string;
  applicationNumber: string;
  institutionName: string;
  institutionCode: string;
  state: string;
  category: string;
  academicYear: string;
  submittedDate: string;
  verifiedCount: number;
  totalRequirements: number;
  flagCount: number;
  status: 'under_review' | 'action_required' | 'validated' | 'escalated' | 'rectification';
  statusLabel: string;
  assignedAuditor: string;
  riskLevel: 'low' | 'medium' | 'high';
}

export interface PendingWorkItem {
  id: string;
  ruleCode: string;
  ruleTitle: string;
  applicationNumber: string;
  institutionName: string;
  severity: 'high' | 'medium' | 'low';
  summary: string;
  timestamp: string;
  documentType: string;
}

export interface ActivityItem {
  id: string;
  timestamp: string;
  timeAgo: string;
  title: string;
  description: string;
  actor: string;
  type: 'verification' | 'flag' | 'document' | 'system' | 'escalation';
  ruleCode?: string;
}

export interface SyntheticNotification {
  id: string;
  title: string;
  message: string;
  timeAgo: string;
  read: boolean;
  type: 'info' | 'warning' | 'alert' | 'success';
  applicationNumber?: string;
}
