import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  computeLinearEventHash,
  computeRfc6962LeafHash,
  computeRfc6962NodeHash,
  buildMerkleTree,
  generateMerkleInclusionProof,
} from '../features/demo/merkleLedger.ts';
import {
  searchAphHandbook,
  APH_HANDBOOK_CHUNKS,
} from '../features/assist/aphHandbookData.ts';

describe('Milestone 4: RFC 6962 Merkle Tree & AIC Assist Logic', () => {
  test('computeLinearEventHash produces deterministic 64-char hex hash', async () => {
    const hash1 = await computeLinearEventHash(
      1,
      '2026-10-29T08:30:00Z',
      'APPLICATION_SUBMITTED',
      'Principal Dr. A. Sharma',
      'Application APP-2026-EOA-0023 submitted',
      '0000000000000000000000000000000000000000000000000000000000000000'
    );
    const hash2 = await computeLinearEventHash(
      1,
      '2026-10-29T08:30:00Z',
      'APPLICATION_SUBMITTED',
      'Principal Dr. A. Sharma',
      'Application APP-2026-EOA-0023 submitted',
      '0000000000000000000000000000000000000000000000000000000000000000'
    );
    assert.equal(hash1, hash2);
    assert.equal(hash1.length, 64);
    assert.match(hash1, /^[0-9a-f]{64}$/);
  });

  test('RFC 6962 domain separation distinguishes leaf from internal node', async () => {
    const data = 'Audit Data Leaf Node Payload';
    const leafHash = await computeRfc6962LeafHash(data);
    // Even with same bytes, interior node hash must not match leaf hash
    const fakeNodeHash = await computeRfc6962NodeHash(
      leafHash.slice(0, 32),
      leafHash.slice(32, 64)
    );
    assert.notEqual(leafHash, fakeNodeHash);
  });

  test('generateMerkleInclusionProof computes valid mathematical proof for all leaves', async () => {
    const sampleLeaves = [
      'Event 1: Application Revision 1 Created',
      'Event 2: Batch 3 Validation Engine Evaluated',
      'Event 3: Auditor Clarification Requested on EOA-SD-04',
      'Event 4: Replacement Stability Certificate Ingested',
    ];

    const { root } = await buildMerkleTree(sampleLeaves);
    assert.equal(root.length, 64);

    for (let i = 0; i < sampleLeaves.length; i++) {
      const proof = await generateMerkleInclusionProof(sampleLeaves, i);
      assert.equal(proof.isValid, true);
      assert.equal(proof.expectedRoot, root);
      assert.equal(proof.calculatedRoot, root);
      assert.equal(proof.leafIndex, i);
    }
  });

  test('tampering with a leaf payload breaks Merkle inclusion proof', async () => {
    const originalLeaves = [
      'Event 1: Application Revision 1 Created',
      'Event 2: Batch 3 Validation Engine Evaluated',
      'Event 3: Auditor Clarification Requested on EOA-SD-04',
      'Event 4: Replacement Stability Certificate Ingested',
    ];

    const { root: expectedRoot } = await buildMerkleTree(originalLeaves);

    // Alter leaf 2
    const tamperedLeaves = [...originalLeaves];
    tamperedLeaves[2] = 'Event 3: UNAUTHORIZED MUTATION TO BYPASS AUDITOR REVIEW';

    const { root: tamperedRoot } = await buildMerkleTree(tamperedLeaves);
    assert.notEqual(expectedRoot, tamperedRoot);

    // Proof against original root fails
    const proof = await generateMerkleInclusionProof(tamperedLeaves, 2);
    assert.equal(proof.calculatedRoot, tamperedRoot);
    assert.notEqual(proof.calculatedRoot, expectedRoot);
  });

  test('searchAphHandbook retrieves exact citations and verbatim text', () => {
    assert.equal(APH_HANDBOOK_CHUNKS.length, 7);

    // EOA-SD-01 search
    const affResults = searchAphHandbook('Affidavit 2 Stamp Paper');
    assert.ok(affResults.length > 0);
    assert.equal(affResults[0].requirementCode, 'EOA-SD-01');
    assert.equal(affResults[0].pageNumber, 142);
    assert.ok(affResults[0].verbatimText.includes('₹100'));

    // EOA-SD-04 search
    const stabilityResults = searchAphHandbook('Structural Stability 30 Years');
    assert.ok(stabilityResults.length > 0);
    assert.equal(stabilityResults[0].requirementCode, 'EOA-SD-04');
    assert.equal(stabilityResults[0].pageNumber, 144);
    assert.ok(stabilityResults[0].verbatimText.includes('thirty (30) or more years'));

    // EOA-SD-07 search
    const udinResults = searchAphHandbook('ICAI UDIN Balance Sheet');
    assert.ok(udinResults.length > 0);
    assert.equal(udinResults[0].requirementCode, 'EOA-SD-07');
    assert.equal(udinResults[0].pageNumber, 145);
    assert.ok(udinResults[0].verbatimText.includes('Unique Document Identification Number'));
  });
});

