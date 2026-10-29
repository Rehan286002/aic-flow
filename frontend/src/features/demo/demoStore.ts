/**
 * Versioned Browser-Side Persistent Demonstration Store.
 *
 * Implements an isolated, schema-versioned demonstration state store using localStorage
 * to preserve interactive scenario mutations across persona switching, page navigation,
 * and page reloads.
 *
 * SAFETY INVARIANT: All mutations stay in browser memory / localStorage.
 * Historical PostgreSQL records (Run 5822d8f2...) remain strictly read-only.
 */

import type {
  ValidationRunRead,
  ValidationResultRead,
  ValidationRunSummary,
  FindingRead,
  FindingStatus,
  ValidationResultStatus,
} from '@/features/validation/types';

export const DEMO_STORAGE_KEY = 'aic_verify_demo_state_v1';
export const DEMO_SCHEMA_VERSION = 1;

export interface ReplacementDocMeta {
  filename: string;
  byteSize: number;
  mimeType: string;
  sha256Digest: string;
  uploadedAt: string;
  versionLabel: string;
}

export interface DemoAuditEvent {
  sequenceNo: number;
  occurredAt: string;
  actor: string;
  action: string;
  details: string;
  previousHash: string;
  currentHash: string;
  isTampered?: boolean;
  tamperedPayload?: string;
}

export interface DemoState {
  version: number;
  scenarioId: string;
  applicationId: string;
  applicationNumber: string;
  institutionId: string;
  institutionName: string;
  academicYear: string;
  activeRevisionNumber: number;
  currentStage: 'INITIAL_REVIEW' | 'CLARIFICATION_PENDING' | 'RECTIFIED' | 'LEAD_REVIEW' | 'CONCURRED';
  
  // Rectification state for EOA-SD-04
  rectification: {
    status: 'NONE' | 'CLARIFICATION_REQUESTED' | 'RECTIFICATION_SUBMITTED' | 'CONCURRED';
    requirementCode: 'EOA-SD-04';
    deficiencyTitle: string;
    auditorInstruction: string;
    clarificationResponse: string | null;
    replacementDocument: ReplacementDocMeta | null;
    rectifiedAt: string | null;
  };

  // Findings list for the demo scenario
  findings: FindingRead[];

  // Active validation run structure for demo rendering
  validationRun: ValidationRunRead;

  // Audit ledger events
  auditLedger: DemoAuditEvent[];

  // Lead Auditor disposition
  leadDisposition: {
    disposition: 'PROCEED' | 'HOLD' | 'INSPECTION' | 'RETURN' | null;
    rationale: string | null;
    recordedAt: string | null;
    leadAuditorName: string | null;
  } | null;

  // Inspection Referral
  inspectionReferral: {
    referenceNumber: string;
    scope: string[];
    targetStartDate: string;
    targetEndDate: string;
    instructions: string;
    memoGeneratedAt: string;
  } | null;
}

// Baseline Initial State (Revision 1, 4 DEFICIENT, 3 UNABLE_TO_DETERMINE, 0 SATISFIED)
export function createInitialDemoState(): DemoState {
  const appId = '082c25e6-a94c-454f-897b-7d307819abcd';
  const revId = 'REV-DEMO-01';

  const initialFindings: FindingRead[] = [
    {
      finding_id: 'FIND-DEMO-01',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-01',
      category: 'FIELD_MISMATCH',
      severity: 'MEDIUM',
      status: 'OPEN',
      title: 'Affidavit 2 Signatory Mismatch',
      internal_reason: 'Affidavit 2 signatory authority name format does not match chairman legal name in portal snapshot.',
      recommended_action: 'Verify trust deed signatory authority resolution.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:00:00Z',
      evidence: [],
    },
    {
      finding_id: 'FIND-DEMO-02',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-02',
      category: 'SOURCE_UNAVAILABLE',
      severity: 'LOW',
      status: 'OPEN',
      title: 'Processing Fee Exemption Unconfirmed',
      internal_reason: 'Portal snapshot fee requirement details require manual verification; missing authoritative exemption record.',
      recommended_action: 'Auditor manual check in AICTE portal.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:00:00Z',
      evidence: [],
    },
    {
      finding_id: 'FIND-DEMO-03',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-03',
      category: 'SOURCE_MISMATCH',
      severity: 'HIGH',
      status: 'OPEN',
      title: 'Land Area Contradiction with State Revenue',
      internal_reason: 'Contradiction: Declared 10.5 acres exceeds State Revenue registry confirmed 7.2 acres (SRC_REVENUE_LAND).',
      recommended_action: 'Request certified 7/12 land extract from applicant.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:00:00Z',
      evidence: [],
    },
    {
      finding_id: 'FIND-DEMO-04',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-04',
      category: 'MISSING_DOCUMENT',
      severity: 'HIGH',
      status: 'CLARIFICATION_REQUESTED',
      title: 'Structural Stability Certificate Required',
      internal_reason: 'Declared building completion date (15-May-1990) indicates age > 30 years. No Structural Stability Certificate attached in initial bundle.',
      recommended_action: 'Submit structural stability certificate issued by registered structural engineer.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:30:00Z',
      evidence: [],
    },
    {
      finding_id: 'FIND-DEMO-05',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-05',
      category: 'SOURCE_MISMATCH',
      severity: 'HIGH',
      status: 'OPEN',
      title: 'Fire Safety NOC Not Found in State Directorate',
      internal_reason: 'Fire Directorate registry search (SRC_FIRE_SERVICES) returned no active NOC for building plot.',
      recommended_action: 'Verify regional fire division clearance.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:00:00Z',
      evidence: [],
    },
    {
      finding_id: 'FIND-DEMO-06',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-06',
      category: 'LOW_OCR_CONFIDENCE',
      severity: 'MEDIUM',
      status: 'OPEN',
      title: 'Satellite Imagery Cloud Cover Obscurity',
      internal_reason: 'Bhuvan satellite imagery obscured by monsoon cloud cover; coordinates require manual boundary inspection.',
      recommended_action: 'Perform physical site boundary verification.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:00:00Z',
      evidence: [],
    },
    {
      finding_id: 'FIND-DEMO-07',
      application_id: appId,
      application_revision_id: revId,
      validation_result_id: 'RES-DEMO-07',
      category: 'SIGNATURE_ISSUE',
      severity: 'CRITICAL',
      status: 'OPEN',
      title: 'ICAI UDIN Registration Missing',
      internal_reason: 'ICAI UDIN verification failed: UDIN 24056781ABCD1234 was not registered in ICAI portal (SRC_ICAI_UDIN).',
      recommended_action: 'Demand Chartered Accountant certificate affirmation.',
      is_internal_only: false,
      created_at: '2026-10-29T09:00:00Z',
      updated_at: '2026-10-29T09:00:00Z',
      evidence: [],
    },
  ];

  const initialResults: ValidationResultRead[] = [
    {
      validation_result_id: 'RES-DEMO-01',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-01',
      validation_rule_version_id: 'RULE-VER-01',
      result_status: 'UNABLE_TO_DETERMINE',
      expected_value: 'Affidavit 2 notarized on ₹100 stamp paper with valid signatory',
      observed_value: 'Signatory format ambiguity with portal registration',
      explanation: 'Evaluator could not ascertain signatory match against authoritative registry without manual review.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[0]],
    },
    {
      validation_result_id: 'RES-DEMO-02',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-02',
      validation_rule_version_id: 'RULE-VER-02',
      result_status: 'UNABLE_TO_DETERMINE',
      expected_value: 'Proof of fee payment or official exemption order',
      observed_value: 'Exemption claimed but unconfirmed in portal snapshot',
      explanation: 'Authoritative exemption record is absent in current portal snapshot payload.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[1]],
    },
    {
      validation_result_id: 'RES-DEMO-03',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-03',
      validation_rule_version_id: 'RULE-VER-03',
      result_status: 'DEFICIENT',
      expected_value: '10.50 Acres contiguous land registered',
      observed_value: '7.20 Acres confirmed in State Revenue registry',
      explanation: 'Declared land area exceeds authoritative State Revenue registry record by 3.30 acres.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[2]],
    },
    {
      validation_result_id: 'RES-DEMO-04',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-04',
      validation_rule_version_id: 'RULE-VER-04',
      result_status: 'DEFICIENT',
      expected_value: 'Structural Stability Certificate required for structures > 30 years',
      observed_value: 'Building completed 15-May-1990 (> 30 yrs); Stability certificate missing',
      explanation: 'Structure age is 35 years. Annexure 2.1 Item iv mandates registered structural engineer certificate.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[3]],
    },
    {
      validation_result_id: 'RES-DEMO-05',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-05',
      validation_rule_version_id: 'RULE-VER-05',
      result_status: 'DEFICIENT',
      expected_value: 'Valid Fire Safety NOC recorded in State Fire Services Directorate',
      observed_value: 'No active NOC record found in State Fire Directorate registry',
      explanation: 'External verification against SRC_FIRE_SERVICES returned no matching clearance.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[4]],
    },
    {
      validation_result_id: 'RES-DEMO-06',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-06',
      validation_rule_version_id: 'RULE-VER-06',
      result_status: 'UNABLE_TO_DETERMINE',
      expected_value: 'Demarcated perimeter boundary verified via Bhuvan imagery',
      observed_value: 'Partial satellite obstruction; boundary confirmation inconclusive',
      explanation: 'Monsoon cloud coverage in satellite imagery prevents automated boundary confirmation.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[5]],
    },
    {
      validation_result_id: 'RES-DEMO-07',
      validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
      application_requirement_id: 'REQ-DEMO-07',
      validation_rule_version_id: 'RULE-VER-07',
      result_status: 'DEFICIENT',
      expected_value: 'Audited financial balance sheet with verified ICAI UDIN',
      observed_value: 'UDIN not registered in ICAI portal database',
      explanation: 'Automated lookup against SRC_ICAI_UDIN failed to verify declared UDIN 24056781ABCD1234.',
      evaluated_at: '2026-10-29T09:00:00Z',
      findings: [initialFindings[6]],
    },
  ];

  const initialSummary: ValidationRunSummary = {
    validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
    status: 'COMPLETED',
    run_type: 'FULL',
    engine_version: '1.0.0-phase6-batch3',
    started_at: '2026-10-29T09:00:00Z',
    completed_at: '2026-10-29T09:00:04Z',
    total_results: 7,
    satisfied_count: 0,
    deficient_count: 4,
    not_applicable_count: 0,
    unable_to_determine_count: 3,
    findings_by_severity: {
      CRITICAL: 1,
      HIGH: 3,
      MEDIUM: 2,
      LOW: 1,
      INFO: 0,
    },
  };

  const initialRun: ValidationRunRead = {
    validation_run_id: 'RUN-DEMO-INTERACTIVE-001',
    application_revision_id: revId,
    run_type: 'FULL',
    engine_version: '1.0.0-phase6-batch3',
    status: 'COMPLETED',
    started_at: '2026-10-29T09:00:00Z',
    completed_at: '2026-10-29T09:00:04Z',
    evaluation_as_of: '2026-10-29T09:00:00Z',
    summary: initialSummary,
    results: initialResults,
  };

  const initialLedger: DemoAuditEvent[] = [
    {
      sequenceNo: 1,
      occurredAt: '2026-10-29T08:30:00Z',
      actor: 'INSTITUTION_USER (Principal Dr. A. Sharma)',
      action: 'APPLICATION_SUBMITTED',
      details: 'Self-disclosure application APP-2026-EOA-0023 submitted for AY 2026-27 (Revision 1).',
      previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
      currentHash: 'b5a2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
    },
    {
      sequenceNo: 2,
      occurredAt: '2026-10-29T09:00:04Z',
      actor: 'VALIDATION_ENGINE (Batch 3 Engine)',
      action: 'EVALUATION_COMPLETED',
      details: 'Automated regulatory validation executed: 4 Deficient, 3 Unable to determine, 0 Satisfied.',
      previousHash: 'b5a2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      currentHash: 'c6b3d4e5f607182930415263748596a7b8c9d0e1f2031425364758697a8b9c0d',
    },
    {
      sequenceNo: 3,
      occurredAt: '2026-10-29T09:30:00Z',
      actor: 'AUDITOR (V. Rao)',
      action: 'CLARIFICATION_REQUESTED',
      details: 'Clarification requested on EOA-SD-04: Building completion 1990 exceeds 30-year threshold. Upload Structural Stability Certificate.',
      previousHash: 'c6b3d4e5f607182930415263748596a7b8c9d0e1f2031425364758697a8b9c0d',
      currentHash: 'd7c4e5f6a718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a',
    },
  ];

  return {
    version: DEMO_SCHEMA_VERSION,
    scenarioId: 'SCN-DEMO-APEX-0023',
    applicationId: appId,
    applicationNumber: 'APP-2026-EOA-0023',
    institutionId: '605839a3-9c20-4ec6-b9f9-765a4b732ad0',
    institutionName: 'Apex Institute of Technology',
    academicYear: '2026-27',
    activeRevisionNumber: 1,
    currentStage: 'CLARIFICATION_PENDING',
    rectification: {
      status: 'CLARIFICATION_REQUESTED',
      requirementCode: 'EOA-SD-04',
      deficiencyTitle: 'Structural Stability Certificate Required (Building Age > 30 Years)',
      auditorInstruction:
        'The declared building completion date (15-May-1990) indicates an age exceeding 30 years. Upload a valid Structural Stability Certificate issued by a registered structural engineer.',
      clarificationResponse: null,
      replacementDocument: null,
      rectifiedAt: null,
    },
    findings: initialFindings,
    validationRun: initialRun,
    auditLedger: initialLedger,
    leadDisposition: null,
    inspectionReferral: null,
  };
}

export class DemoStore {
  private static cachedState: DemoState | null = null;

  public static load(): DemoState {
    if (this.cachedState) {
      return this.cachedState;
    }

    try {
      const raw = localStorage.getItem(DEMO_STORAGE_KEY);
      if (!raw) {
        const fresh = createInitialDemoState();
        this.save(fresh);
        return fresh;
      }

      const parsed = JSON.parse(raw) as DemoState;
      if (parsed.version !== DEMO_SCHEMA_VERSION) {
        console.warn('DemoStore: Schema version mismatch. Resetting demo state.');
        const fresh = createInitialDemoState();
        this.save(fresh);
        return fresh;
      }

      this.cachedState = parsed;
      return parsed;
    } catch (e) {
      console.error('DemoStore: Failed to load demo state from localStorage:', e);
      const fresh = createInitialDemoState();
      this.save(fresh);
      return fresh;
    }
  }

  public static save(state: DemoState): void {
    try {
      this.cachedState = state;
      localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.error('DemoStore: Failed to persist state to localStorage:', e);
    }
  }

  public static reset(): DemoState {
    try {
      localStorage.removeItem(DEMO_STORAGE_KEY);
    } catch {
      // ignore
    }
    const fresh = createInitialDemoState();
    this.save(fresh);
    return fresh;
  }

  /**
   * Updates finding status in demo store and appends audit event.
   */
  public static updateFindingStatus(
    findingId: string,
    targetStatus: FindingStatus,
    rationale: string,
    actorName: string
  ): DemoState {
    const state = this.load();

    const updatedFindings = state.findings.map((f) => {
      if (f.finding_id === findingId) {
        return {
          ...f,
          status: targetStatus,
          internal_reason: `${f.internal_reason || ''}\n\n[ACTION ${new Date().toISOString()} by ${actorName}] Status -> ${targetStatus}: ${rationale}`,
          updated_at: new Date().toISOString(),
        };
      }
      return f;
    });

    // Also update finding inside validationRun.results
    const updatedResults = state.validationRun.results.map((res) => {
      const updatedChildFindings = res.findings.map((f) => {
        if (f.finding_id === findingId) {
          return {
            ...f,
            status: targetStatus,
            internal_reason: `${f.internal_reason || ''}\n\n[ACTION ${new Date().toISOString()} by ${actorName}] Status -> ${targetStatus}: ${rationale}`,
            updated_at: new Date().toISOString(),
          };
        }
        return f;
      });
      return { ...res, findings: updatedChildFindings };
    });

    const now = new Date().toISOString();
    const prevHash = state.auditLedger[state.auditLedger.length - 1]?.currentHash || '0000000000000000';
    const newHash = Math.random().toString(16).substring(2, 10) + prevHash.substring(0, 56);

    const newLedgerEvent: DemoAuditEvent = {
      sequenceNo: state.auditLedger.length + 1,
      occurredAt: now,
      actor: actorName,
      action: `FINDING_TRIAGE_${targetStatus}`,
      details: `Finding ${findingId} transitioned to ${targetStatus}: "${rationale}"`,
      previousHash: prevHash,
      currentHash: newHash,
    };

    const newState: DemoState = {
      ...state,
      findings: updatedFindings,
      validationRun: {
        ...state.validationRun,
        results: updatedResults,
      },
      auditLedger: [...state.auditLedger, newLedgerEvent],
    };

    this.save(newState);
    return newState;
  }

  /**
   * Submits replacement document and clarification for EOA-SD-04, generating Revision 2.
   * Re-evaluates EOA-SD-04 from DEFICIENT -> SATISFIED!
   */
  public static submitRectification(
    docMeta: ReplacementDocMeta,
    clarificationText: string
  ): DemoState {
    const state = this.load();
    const now = new Date().toISOString();

    // 1. Update finding FIND-DEMO-04 to RESOLVED
    const updatedFindings = state.findings.map((f) => {
      if (f.finding_id === 'FIND-DEMO-04') {
        return {
          ...f,
          status: 'RESOLVED' as FindingStatus,
          internal_reason: `${f.internal_reason}\n\n[RECTIFICATION ${now}] Replacement certificate verified: ${docMeta.filename} (SHA-256: ${docMeta.sha256Digest.substring(0, 16)}...). Deficiency resolved.`,
          updated_at: now,
        };
      }
      return f;
    });

    // 2. Update validation result for EOA-SD-04 from DEFICIENT -> SATISFIED
    const updatedResults = state.validationRun.results.map((res) => {
      // Find EOA-SD-04 requirement result
      if (res.validation_result_id === 'RES-DEMO-04') {
        const resolvedFinding = updatedFindings.find((f) => f.finding_id === 'FIND-DEMO-04')!;
        return {
          ...res,
          result_status: 'SATISFIED' as ValidationResultStatus,
          observed_value: `Structural Stability Certificate attached: ${docMeta.filename} (Valid through 2031, Structural Eng. Lic #SE-98442)`,
          explanation: `Applicant submitted valid Structural Stability Certificate in Revision 2. Deficiency resolved.`,
          evaluated_at: now,
          findings: [resolvedFinding],
        };
      }
      return res;
    });

    // 3. Re-aggregate summary counts: Satisfied = 1, Deficient = 3, Unable to determine = 3
    const newSummary: ValidationRunSummary = {
      validation_run_id: 'RUN-DEMO-INTERACTIVE-002',
      status: 'COMPLETED',
      run_type: 'FULL',
      engine_version: '1.0.0-phase6-batch3',
      started_at: state.validationRun.started_at,
      completed_at: now,
      total_results: 7,
      satisfied_count: 1,
      deficient_count: 3,
      not_applicable_count: 0,
      unable_to_determine_count: 3,
      findings_by_severity: {
        CRITICAL: 1,
        HIGH: 2, // decreased from 3
        MEDIUM: 2,
        LOW: 1,
        INFO: 1,
      },
    };

    const prevHash = state.auditLedger[state.auditLedger.length - 1]?.currentHash || '0000000000000000';
    const rectHash = 'e8f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5';

    const newLedgerEvent: DemoAuditEvent = {
      sequenceNo: state.auditLedger.length + 1,
      occurredAt: now,
      actor: 'INSTITUTION_USER (Principal Dr. A. Sharma)',
      action: 'RECTIFICATION_SUBMITTED',
      details: `Revision 2 submitted with replacement certificate "${docMeta.filename}" (SHA-256: ${docMeta.sha256Digest.slice(0, 16)}...). EOA-SD-04 re-evaluated to SATISFIED.`,
      previousHash: prevHash,
      currentHash: rectHash,
    };

    const newState: DemoState = {
      ...state,
      activeRevisionNumber: 2,
      currentStage: 'RECTIFIED',
      rectification: {
        status: 'RECTIFICATION_SUBMITTED',
        requirementCode: 'EOA-SD-04',
        deficiencyTitle: 'Structural Stability Certificate Required (Building Age > 30 Years)',
        auditorInstruction: state.rectification.auditorInstruction,
        clarificationResponse: clarificationText,
        replacementDocument: docMeta,
        rectifiedAt: now,
      },
      findings: updatedFindings,
      validationRun: {
        ...state.validationRun,
        validation_run_id: 'RUN-DEMO-INTERACTIVE-002',
        application_revision_id: 'REV-DEMO-02',
        evaluation_as_of: now,
        summary: newSummary,
        results: updatedResults,
      },
      auditLedger: [...state.auditLedger, newLedgerEvent],
    };

    this.save(newState);
    return newState;
  }

  /**
   * Records Lead Auditor supervisory review disposition.
   */
  public static recordLeadDisposition(
    disposition: 'PROCEED' | 'HOLD' | 'INSPECTION' | 'RETURN',
    rationale: string,
    leadAuditorName: string
  ): DemoState {
    const state = this.load();
    const now = new Date().toISOString();

    const prevHash = state.auditLedger[state.auditLedger.length - 1]?.currentHash || '0000000000000000';
    const dispHash = 'f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0';

    const newLedgerEvent: DemoAuditEvent = {
      sequenceNo: state.auditLedger.length + 1,
      occurredAt: now,
      actor: `LEAD_AUDITOR (${leadAuditorName})`,
      action: `LEAD_DISPOSITION_${disposition}`,
      details: `Lead Review completed. Internal disposition: ${disposition}. Rationale: "${rationale}"`,
      previousHash: prevHash,
      currentHash: dispHash,
    };

    const newState: DemoState = {
      ...state,
      currentStage: disposition === 'INSPECTION' ? 'LEAD_REVIEW' : 'CONCURRED',
      leadDisposition: {
        disposition,
        rationale,
        recordedAt: now,
        leadAuditorName,
      },
      auditLedger: [...state.auditLedger, newLedgerEvent],
    };

    this.save(newState);
    return newState;
  }

  /**
   * Generates Physical On-Site Inspection Referral.
   */
  public static generateInspectionReferral(
    scope: string[],
    targetStartDate: string,
    targetEndDate: string,
    instructions: string
  ): DemoState {
    const state = this.load();
    const now = new Date().toISOString();
    const refNum = `INSP-REF-2026-${Math.floor(1000 + Math.random() * 9000)}`;

    const prevHash = state.auditLedger[state.auditLedger.length - 1]?.currentHash || '0000000000000000';
    const inspHash = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';

    const newLedgerEvent: DemoAuditEvent = {
      sequenceNo: state.auditLedger.length + 1,
      occurredAt: now,
      actor: 'LEAD_AUDITOR (Dr. H. V. Verma)',
      action: 'INSPECTION_REFERRAL_ISSUED',
      details: `Physical inspection referral ${refNum} generated for scopes: ${scope.join(', ')}. Target: ${targetStartDate} to ${targetEndDate}.`,
      previousHash: prevHash,
      currentHash: inspHash,
    };

    const newState: DemoState = {
      ...state,
      inspectionReferral: {
        referenceNumber: refNum,
        scope,
        targetStartDate,
        targetEndDate,
        instructions,
        memoGeneratedAt: now,
      },
      auditLedger: [...state.auditLedger, newLedgerEvent],
    };

    this.save(newState);
    return newState;
  }

  /**
   * Simulates byte tampering on an audit ledger event for M4 Merkle verification demo.
   */
  public static toggleTamperEvent(sequenceNo: number): DemoState {
    const state = this.load();
    const updatedLedger = state.auditLedger.map((evt) => {
      if (evt.sequenceNo === sequenceNo) {
        const isTampered = !evt.isTampered;
        return {
          ...evt,
          isTampered,
          tamperedPayload: isTampered ? `${evt.details} [MODIFIED BY UNAUTHORIZED ACTOR]` : undefined,
        };
      }
      return evt;
    });

    const newState: DemoState = {
      ...state,
      auditLedger: updatedLedger,
    };
    this.save(newState);
    return newState;
  }
}
