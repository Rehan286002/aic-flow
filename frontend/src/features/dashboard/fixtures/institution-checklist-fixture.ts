import type { ChecklistRequirement } from '@/types/checklist';

/**
 * APPLICANT SELF-DISCLOSURE CHECKLIST FIXTURE
 * 
 * Application: APP-2026-EOA-0842
 * Institution: Apex Institute of Technology, Pune (Code: 1-10948201)
 * Academic Year: 2026-27 • Extension of Approval (EoA)
 * 
 * Note: Under AIC-Flow privacy boundaries, applicant views display only
 * applicant-safe descriptions, formal deficiency guidance, and evidence statuses.
 * Internal auditor deliberation comments, risk scores, and anomaly severity vectors
 * remain restricted to authorized verification auditors.
 */

export const SYNTHETIC_INSTITUTION_CHECKLIST: ChecklistRequirement[] = [
  {
    id: 'req-01',
    code: 'EOA-SD-01',
    name: 'Affidavit 2',
    description:
      'Notarized affidavit on ₹100 non-judicial stamp paper affirming compliance with AICTE governance, fee, and faculty norms under Approval Process Handbook Annexure 2.1.',
    applicability: 'applicable',
    status: 'satisfied',
    statusLabel: 'Satisfied',
    supportingDocument: {
      name: 'Affidavit_2_Executed.pdf',
      detail: 'Stamp Paper #MH-2026-94812 • Notary Verification Confirmed',
    },
    permittedAction: {
      label: 'View Document',
      variant: 'outline',
      actionKey: 'view_document',
    },
  },
  {
    id: 'req-02',
    code: 'EOA-SD-02',
    name: 'Payment Receipt',
    description:
      'Official bank challan / payment gateway receipt confirming regulatory processing fee remittance for Academic Year 2026-27.',
    applicability: 'applicable',
    status: 'satisfied',
    statusLabel: 'Satisfied',
    supportingDocument: {
      name: 'Fee_Challan_Receipt.pdf',
      detail: 'Bank UTR: HDFC202610240982 • Reconciliation Confirmed',
    },
    permittedAction: {
      label: 'View Receipt',
      variant: 'outline',
      actionKey: 'view_receipt',
    },
  },
  {
    id: 'req-03',
    code: 'EOA-SD-03',
    name: 'Building-Related Certificate',
    description:
      'Registered land ownership title deed and competent municipal authority sanction approving premises for educational occupancy.',
    applicability: 'applicable',
    status: 'satisfied',
    statusLabel: 'Satisfied',
    supportingDocument: {
      name: 'Building_Plan_Sanction.pdf',
      detail: 'Municipal Sanction #PMC-BP-2007-882 • 10.5 Acres Registered',
    },
    permittedAction: {
      label: 'View Document',
      variant: 'outline',
      actionKey: 'view_document',
    },
  },
  {
    id: 'req-04',
    code: 'EOA-SD-04',
    name: 'Structural Stability Certificate',
    description:
      'Mandatory only when building completion exceeds 30 years. Campus structures were completed in 2008 (age: 18 years); condition is not applicable.',
    applicability: 'not_applicable',
    status: 'not_applicable',
    statusLabel: 'Not Applicable',
    supportingDocument: {
      name: 'Completion_Certificate_2008.pdf',
      detail: 'Occupancy Date: 12-Jul-2008 • Structure Age: 18 yrs (&lt; 30 yr threshold)',
    },
    permittedAction: {
      label: 'View Completion Proof',
      variant: 'ghost',
      actionKey: 'view_document',
    },
  },
  {
    id: 'req-05',
    code: 'EOA-SD-05',
    name: 'Fire Safety Certificate',
    description:
      'Fire Safety Certificate from competent local authority. Under the configured validity rule for this case, certificate validity expired on 15-Sep-2026 prior to Academic Year 2026-27 commencement.',
    applicability: 'applicable',
    status: 'deficient',
    statusLabel: 'Deficient',
    supportingDocument: {
      name: 'Fire_Safety_NOC_2025.pdf',
      detail: 'NOC #PMC-F-4410 • Validity Expired: 15-Sep-2026',
    },
    permittedAction: {
      label: 'Upload Renewal Certificate',
      variant: 'default',
      actionKey: 'upload_replacement',
    },
  },
  {
    id: 'req-06',
    code: 'EOA-SD-06',
    name: 'Satellite Map / Coordinates',
    description:
      'Satellite map with demarcated campus boundary polygon and GPS coordinates (18.5204° N, 73.8567° E). Automated state GIS cadastral reconciliation verified within 8.4m tolerance.',
    applicability: 'applicable',
    status: 'satisfied',
    statusLabel: 'Satisfied',
    supportingDocument: {
      name: 'Campus_Satellite_Map_GIS.pdf',
      detail: 'Khata No. 412/1A • Geo-Boundary Variance: 8.4m (Within 25m Limit)',
    },
    permittedAction: {
      label: 'View Coordinates',
      variant: 'outline',
      actionKey: 'view_map',
    },
  },
  {
    id: 'req-07',
    code: 'EOA-SD-07',
    name: 'Previous-Year Audited Accounts',
    description:
      'Complete audited financial statements, balance sheet, and receipt/expenditure accounts for FY 2024-25, certified by an active Chartered Accountant with verifiable UDIN.',
    applicability: 'applicable',
    status: 'satisfied',
    statusLabel: 'Satisfied',
    supportingDocument: {
      name: 'Audited_Accounts_FY2024-25.pdf',
      detail: 'CA Reg #048219 • Verifiable UDIN: 25048219BGHLM9182',
    },
    permittedAction: {
      label: 'View Statements',
      variant: 'outline',
      actionKey: 'view_financials',
    },
  },
];
