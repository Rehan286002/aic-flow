import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  computeBufferSha256,
  computeFileSha256,
  computeStringSha256,
} from '../features/demo/cryptoUtils.ts';

describe('Audit Section 4: Cryptographic File Integrity & NIST SHA-256 Verification', () => {
  test('NIST CAVP Vector 1: Empty string digest is e3b0c442...', async () => {
    // NIST CAVP standard test vector for empty string (0-length)
    const emptyHash = await computeStringSha256('');
    assert.equal(
      emptyHash,
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      'Empty string must produce standard NIST digest e3b0c442...'
    );
  });

  test('NIST CAVP Vector 2: "abc" produces known standard digest', async () => {
    // NIST CAVP standard test vector for "abc"
    const abcHash = await computeStringSha256('abc');
    assert.equal(
      abcHash,
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
      'String "abc" must produce exact NIST CAVP digest'
    );
  });

  test('NIST CAVP Vector 3: 448-bit string produces known standard digest', async () => {
    const input = 'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq';
    const hash = await computeStringSha256(input);
    assert.equal(
      hash,
      '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1',
      '448-bit string must produce exact NIST CAVP digest'
    );
  });

  test('Actual non-empty demonstration file computes authentic SHA-256 digest', async () => {
    const fileContent = '%PDF-1.4 Demonstration Structural Stability Certificate 2026 - Apex Institute';
    const file = new File([fileContent], 'Structural_Stability_Certificate_2026.pdf', {
      type: 'application/pdf',
    });

    assert.ok(file.size > 0, 'Demonstration file must have non-zero byte size');
    assert.equal(file.size, 77, 'Demonstration file has exact size of 77 bytes');

    let progressReported = false;
    const digest = await computeFileSha256(file, (progress) => {
      if (progress === 100) progressReported = true;
    });

    assert.equal(progressReported, true, 'Progress callback must reach 100%');
    assert.equal(
      digest,
      'caf75d2e2b6e52132f38098524c77290f78897e0bbe125794efbbf4d2ee68dcd',
      'Digest must match pre-calculated SHA-256 of the demonstration PDF content'
    );
    assert.notEqual(
      digest,
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      'Demonstration file digest must NOT match the empty-string hash'
    );
  });

  test('0-byte file upload is explicitly rejected with an exception', async () => {
    const emptyFile = new File([], 'empty.pdf', { type: 'application/pdf' });
    assert.equal(emptyFile.size, 0, 'File must be 0 bytes');

    await assert.rejects(
      async () => {
        await computeFileSha256(emptyFile);
      },
      {
        name: 'Error',
        message: /Zero-byte file rejected: cannot compute SHA-256 on empty file/,
      },
      'computeFileSha256 must reject zero-byte files'
    );
  });

  test('Buffer hashing matches file hashing byte-for-byte', async () => {
    const content = 'AICTE Regulatory Verification Platform - Document Buffer Test';
    const encoder = new TextEncoder();
    const buffer = encoder.encode(content).buffer as ArrayBuffer;

    const file = new File([content], 'test.txt', { type: 'text/plain' });

    const bufferHash = await computeBufferSha256(buffer);
    const fileHash = await computeFileSha256(file);
    const stringHash = await computeStringSha256(content);

    assert.equal(bufferHash, fileHash);
    assert.equal(fileHash, stringHash);
  });
});
