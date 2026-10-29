/**
 * RFC 6962 Domain-Separated Merkle Tree and Linear Hash Chain Engine.
 *
 * Implements deterministic cryptographic ledger verification and tamper detection
 * using the browser Web Crypto API (SubtleCrypto).
 *
 * Mathematical Invariants:
 * 1. Linear Chain: H(seq | time | action | actor | payload | prev_hash)
 * 2. RFC 6962 Merkle Leaf: SHA-256( 0x00 || leaf_data )
 * 3. RFC 6962 Merkle Node: SHA-256( 0x01 || left_child || right_child )
 */

import { computeBufferSha256 } from './cryptoUtils.ts';

export interface MerkleProofStep {
  direction: 'left' | 'right';
  hash: string;
}

export interface MerkleInclusionProof {
  leafHash: string;
  leafIndex: number;
  auditPath: MerkleProofStep[];
  expectedRoot: string;
  calculatedRoot: string;
  isValid: boolean;
}

export interface ChainVerificationResult {
  isValid: boolean;
  tamperedIndex: number | null;
  expectedHashes: string[];
  actualHashes: string[];
}

/**
 * Encodes text to UTF-8 Uint8Array.
 */
function toUtf8(str: string): Uint8Array {
  return new TextEncoder().encode(str);
}

/**
 * Converts lowercase hex string to Uint8Array.
 */
function fromHex(hex: string): Uint8Array {
  const clean = hex.trim();
  const bytes = new Uint8Array(clean.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(clean.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

/**
 * Computes SHA-256 over raw Uint8Array bytes.
 */
export async function sha256Bytes(bytes: Uint8Array): Promise<string> {
  return computeBufferSha256(bytes.buffer as ArrayBuffer);
}

/**
 * Computes Linear Hash Chain hash for an audit event.
 */
export async function computeLinearEventHash(
  sequenceNo: number,
  occurredAt: string,
  action: string,
  actor: string,
  details: string,
  previousHash: string
): Promise<string> {
  const payload = `${sequenceNo}|${occurredAt}|${action}|${actor}|${details}|${previousHash}`;
  return sha256Bytes(toUtf8(payload));
}

/**
 * RFC 6962 Domain-Separated Leaf Hash: SHA-256( 0x00 || leaf_data )
 */
export async function computeRfc6962LeafHash(leafData: string): Promise<string> {
  const dataBytes = toUtf8(leafData);
  const buffer = new Uint8Array(1 + dataBytes.length);
  buffer[0] = 0x00; // Leaf domain separator
  buffer.set(dataBytes, 1);
  return sha256Bytes(buffer);
}

/**
 * RFC 6962 Domain-Separated Internal Node Hash: SHA-256( 0x01 || left_child || right_child )
 */
export async function computeRfc6962NodeHash(
  leftChildHex: string,
  rightChildHex: string
): Promise<string> {
  const leftBytes = fromHex(leftChildHex);
  const rightBytes = fromHex(rightChildHex);
  const buffer = new Uint8Array(1 + leftBytes.length + rightBytes.length);
  buffer[0] = 0x01; // Interior node domain separator
  buffer.set(leftBytes, 1);
  buffer.set(rightBytes, 1 + leftBytes.length);
  return sha256Bytes(buffer);
}

/**
 * Builds RFC 6962 Merkle Tree from an array of leaf strings.
 * Returns layers of hashes from bottom (leaves) to top (root).
 */
export async function buildMerkleTree(
  leaves: string[]
): Promise<{ layers: string[][]; root: string }> {
  if (leaves.length === 0) {
    const emptyRoot = await sha256Bytes(new Uint8Array(0));
    return { layers: [[]], root: emptyRoot };
  }

  // 1. Compute leaf nodes with 0x00 domain separator
  let currentLayer: string[] = [];
  for (const leaf of leaves) {
    currentLayer.push(await computeRfc6962LeafHash(leaf));
  }

  const layers: string[][] = [currentLayer];

  // 2. Build interior nodes layer-by-layer
  while (currentLayer.length > 1) {
    const nextLayer: string[] = [];
    for (let i = 0; i < currentLayer.length; i += 2) {
      if (i + 1 < currentLayer.length) {
        nextLayer.push(await computeRfc6962NodeHash(currentLayer[i], currentLayer[i + 1]));
      } else {
        // Odd node promoted per RFC 6962
        nextLayer.push(currentLayer[i]);
      }
    }
    layers.push(nextLayer);
    currentLayer = nextLayer;
  }

  return { layers, root: currentLayer[0] };
}

/**
 * Computes RFC 6962 Merkle inclusion proof for a given leaf index.
 */
export async function generateMerkleInclusionProof(
  leaves: string[],
  targetIndex: number
): Promise<MerkleInclusionProof> {
  const { layers, root } = await buildMerkleTree(leaves);
  const auditPath: MerkleProofStep[] = [];
  let index = targetIndex;

  for (let l = 0; l < layers.length - 1; l++) {
    const layer = layers[l];
    const isRightChild = index % 2 === 1;
    const siblingIndex = isRightChild ? index - 1 : index + 1;

    if (siblingIndex < layer.length) {
      auditPath.push({
        direction: isRightChild ? 'left' : 'right',
        hash: layer[siblingIndex],
      });
    }
    index = Math.floor(index / 2);
  }

  const leafHash = await computeRfc6962LeafHash(leaves[targetIndex]);

  // Verify the audit path to calculate the root
  let runningHash = leafHash;
  for (const step of auditPath) {
    if (step.direction === 'left') {
      runningHash = await computeRfc6962NodeHash(step.hash, runningHash);
    } else {
      runningHash = await computeRfc6962NodeHash(runningHash, step.hash);
    }
  }

  return {
    leafHash,
    leafIndex: targetIndex,
    auditPath,
    expectedRoot: root,
    calculatedRoot: runningHash,
    isValid: root === runningHash,
  };
}

/**
 * Validates the entire linear hash chain of audit ledger events.
 * Returns the exact index where tampering occurred, if any.
 */
export async function verifyLinearHashChain(
  events: Array<{
    sequenceNo: number;
    occurredAt: string;
    action: string;
    actor: string;
    details: string;
    previousHash: string;
    currentHash: string;
    isTampered?: boolean;
    tamperedPayload?: string;
  }>
): Promise<ChainVerificationResult> {
  const expectedHashes: string[] = [];
  const actualHashes: string[] = [];
  let previousHash = '0000000000000000000000000000000000000000000000000000000000000000';
  let tamperedIndex: number | null = null;

  for (let i = 0; i < events.length; i++) {
    const evt = events[i];
    const payload = evt.isTampered && evt.tamperedPayload ? evt.tamperedPayload : evt.details;
    const expected = await computeLinearEventHash(
      evt.sequenceNo,
      evt.occurredAt,
      evt.action,
      evt.actor,
      payload,
      previousHash
    );

    expectedHashes.push(expected);
    actualHashes.push(evt.currentHash);

    // If expected hash diverges from recorded hash or previousHash link is broken
    if (expected !== evt.currentHash && tamperedIndex === null) {
      tamperedIndex = i;
    }

    previousHash = evt.currentHash;
  }

  return {
    isValid: tamperedIndex === null,
    tamperedIndex,
    expectedHashes,
    actualHashes,
  };
}
