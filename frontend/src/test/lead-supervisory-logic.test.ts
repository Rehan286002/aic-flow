import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// Node 22 polyfill for localStorage in test environment
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

import { DemoStore } from '../features/demo/demoStore.ts';

describe('Milestone 3: Lead Auditor Oversight & Inspection Referrals', () => {
  beforeEach(() => {
    localStorage.clear();
    DemoStore.reset();
  });

  test('recordLeadDisposition records supervisory workflow recommendation', () => {
    const disposition = 'INSPECTION';
    const rationale = 'Unresolved revenue survey contradiction on plot 74 requires on-site physical demarcation.';
    const leadName = 'Dr. H. V. Verma (Lead Auditor)';

    const updated = DemoStore.recordLeadDisposition(disposition, rationale, leadName);

    assert.ok(updated.leadDisposition);
    assert.equal(updated.leadDisposition.disposition, 'INSPECTION');
    assert.equal(updated.leadDisposition.rationale, rationale);
    assert.equal(updated.leadDisposition.leadAuditorName, leadName);
    assert.ok(updated.leadDisposition.recordedAt);

    // Ledger must have recorded the disposition event
    const lastEvent = updated.auditLedger[updated.auditLedger.length - 1];
    assert.equal(lastEvent.action, 'LEAD_DISPOSITION_INSPECTION');
    assert.ok(lastEvent.details.includes(rationale));
  });

  test('generateInspectionReferral creates official inspection memo details', () => {
    const scopes = [
      'State Revenue Land Demarcation & Perimeter Survey',
      'Fire Safety Clearances & Active Pump Installation',
    ];
    const startDate = '2026-11-15';
    const endDate = '2026-11-20';
    const instructions = 'Verify physical boundary pillars against revenue extract 7/12.';

    const updated = DemoStore.generateInspectionReferral(scopes, startDate, endDate, instructions);

    assert.ok(updated.inspectionReferral);
    assert.match(updated.inspectionReferral.referenceNumber, /^INSP-REF-2026-\d{4}$/);
    assert.deepEqual(updated.inspectionReferral.scope, scopes);
    assert.equal(updated.inspectionReferral.targetStartDate, startDate);
    assert.equal(updated.inspectionReferral.targetEndDate, endDate);
    assert.equal(updated.inspectionReferral.instructions, instructions);
    assert.ok(updated.inspectionReferral.memoGeneratedAt);

    // Ledger must record the referral event
    const lastEvent = updated.auditLedger[updated.auditLedger.length - 1];
    assert.equal(lastEvent.action, 'INSPECTION_REFERRAL_ISSUED');
  });

  test('lead finding action accepts or dismisses escalated finding', () => {
    // Triage FIND-DEMO-03 to ACCEPTED by Lead Auditor
    const updated = DemoStore.updateFindingStatus(
      'FIND-DEMO-03',
      'ACCEPTED',
      'Lead Auditor concurs with deficiency finding based on revenue records.',
      'Lead Auditor (Dr. H. V. Verma)'
    );

    const finding = updated.findings.find((f) => f.finding_id === 'FIND-DEMO-03');
    assert.ok(finding);
    assert.equal(finding.status, 'ACCEPTED');

    const lastEvent = updated.auditLedger[updated.auditLedger.length - 1];
    assert.equal(lastEvent.action, 'FINDING_TRIAGE_ACCEPTED');
    assert.ok(lastEvent.actor.includes('Lead Auditor'));
  });
});

