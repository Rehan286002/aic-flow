import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// Node 22 has global crypto.subtle. Polyfill localStorage for node environment if missing
if (typeof globalThis.localStorage === 'undefined') {
  const store = new Map<string, string>();
  globalThis.localStorage = {
    getItem: (key: string) => store.get(key) || null,
    setItem: (key: string, val: string) => {
      store.set(key, String(val));
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
    key: (index: number) => Array.from(store.keys())[index] || null,
    length: 0,
  } as Storage;
}

import {
  DemoStore,
  createInitialDemoState,
  type ReplacementDocMeta,
} from '../features/demo/demoStore.ts';
import { computeStringSha256 } from '../features/demo/cryptoUtils.ts';

describe('Milestone 2: Persistent Demo Store & Rectification Logic', () => {
  beforeEach(() => {
    localStorage.clear();
    DemoStore.reset();
  });

  test('createInitialDemoState initializes Revision 1 baseline correctly', () => {
    const state = createInitialDemoState();
    assert.equal(state.version, 1);
    assert.equal(state.activeRevisionNumber, 1);
    assert.equal(state.applicationNumber, 'APP-2026-EOA-0023');
    assert.equal(state.validationRun.summary?.satisfied_count, 0);
    assert.equal(state.validationRun.summary?.deficient_count, 4);
    assert.equal(state.validationRun.summary?.unable_to_determine_count, 3);
    assert.equal(state.validationRun.results.length, 7);

    // EOA-SD-04 must initially be DEFICIENT
    const sd04 = state.validationRun.results.find(
      (r) => r.validation_result_id === 'RES-DEMO-04'
    );
    assert.ok(sd04);
    assert.equal(sd04.result_status, 'DEFICIENT');
  });

  test('submitRectification generates Revision 2 and shifts EOA-SD-04 to SATISFIED', () => {
    const docMeta: ReplacementDocMeta = {
      filename: 'Structural_Stability_Certificate_2026.pdf',
      byteSize: 1024 * 1024 * 2.5,
      mimeType: 'application/pdf',
      sha256Digest: 'caf75d2e2b6e52132f38098524c77290f78897e0bbe125794efbbf4d2ee68dcd',
      uploadedAt: new Date().toISOString(),
      versionLabel: 'v2 (Replacement)',
    };
    const explanation = 'Submitted structural stability certificate from registered structural engineer.';

    const updated = DemoStore.submitRectification(docMeta, explanation);

    // Active revision number must increment to 2
    assert.equal(updated.activeRevisionNumber, 2);
    assert.equal(updated.currentStage, 'RECTIFIED');
    assert.equal(updated.rectification.status, 'RECTIFICATION_SUBMITTED');
    assert.equal(updated.rectification.replacementDocument?.filename, docMeta.filename);

    // EOA-SD-04 must shift from DEFICIENT -> SATISFIED
    const sd04 = updated.validationRun.results.find(
      (r) => r.validation_result_id === 'RES-DEMO-04'
    );
    assert.ok(sd04);
    assert.equal(sd04.result_status, 'SATISFIED');

    // Finding FIND-DEMO-04 must shift to RESOLVED
    const finding = updated.findings.find((f) => f.finding_id === 'FIND-DEMO-04');
    assert.ok(finding);
    assert.equal(finding.status, 'RESOLVED');

    // Summary counts must reflect: 1 SATISFIED, 3 DEFICIENT, 3 UNABLE_TO_DETERMINE
    assert.equal(updated.validationRun.summary?.satisfied_count, 1);
    assert.equal(updated.validationRun.summary?.deficient_count, 3);
    assert.equal(updated.validationRun.summary?.unable_to_determine_count, 3);

    // Audit ledger must record the rectification event
    const lastEvent = updated.auditLedger[updated.auditLedger.length - 1];
    assert.equal(lastEvent.action, 'RECTIFICATION_SUBMITTED');
  });

  test('updateFindingStatus updates finding status and records audit event', () => {
    const updated = DemoStore.updateFindingStatus(
      'FIND-DEMO-03',
      'ESCALATED',
      'Escalated to Lead Auditor due to revenue survey contradiction.',
      'Auditor (Review Team Alpha)'
    );

    const finding = updated.findings.find((f) => f.finding_id === 'FIND-DEMO-03');
    assert.ok(finding);
    assert.equal(finding.status, 'ESCALATED');

    const lastEvent = updated.auditLedger[updated.auditLedger.length - 1];
    assert.equal(lastEvent.action, 'FINDING_TRIAGE_ESCALATED');
    assert.ok(lastEvent.details.includes('FIND-DEMO-03'));
  });

  test('computeStringSha256 produces valid 64-char lowercase hex digest', async () => {
    const hash = await computeStringSha256('AIC-Flow Statutory Test String');
    assert.equal(typeof hash, 'string');
    assert.equal(hash.length, 64);
    assert.match(hash, /^[0-9a-f]{64}$/);
  });

  test('reset restores initial state and wipes mutations', () => {
    // Mutate state first
    DemoStore.submitRectification(
      {
        filename: 'test.pdf',
        byteSize: 100,
        mimeType: 'application/pdf',
        sha256Digest: 'abc',
        uploadedAt: 'now',
        versionLabel: 'v2',
      },
      'Test note'
    );
    assert.equal(DemoStore.load().activeRevisionNumber, 2);

    // Reset
    const restored = DemoStore.reset();
    assert.equal(restored.activeRevisionNumber, 1);
    assert.equal(restored.validationRun.summary?.satisfied_count, 0);
    assert.equal(restored.validationRun.summary?.deficient_count, 4);
  });
});
