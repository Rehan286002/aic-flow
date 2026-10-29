export type RequirementStatus =
  | 'satisfied'
  | 'deficient'
  | 'not_applicable'
  | 'unable_to_determine'
  | 'pending'
  | 'under_review';

export type ApplicabilityStatus = 'applicable' | 'not_applicable';

export interface ChecklistRequirement {
  id: string;
  code: string;
  name: string;
  description: string;
  applicability: ApplicabilityStatus;
  status: RequirementStatus;
  statusLabel: string;
  supportingDocument?: {
    name: string;
    detail: string;
  };
  permittedAction?: {
    label: string;
    variant?: 'default' | 'outline' | 'ghost';
    actionKey: 'view_document' | 'upload_replacement' | 'view_receipt' | 'view_map' | 'view_financials';
  };
}

export interface ChecklistSummaryCounts {
  total: number;
  satisfied: number;
  deficient: number;
  notApplicable: number;
  underReview: number;
  pending: number;
  unableToDetermine: number;
}
