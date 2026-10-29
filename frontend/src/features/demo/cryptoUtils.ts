/**
 * Cryptographic utility functions using Web Crypto API.
 * Provides client-side SHA-256 hashing for files, strings, and audit ledger integrity.
 */

export async function computeBufferSha256(buffer: ArrayBuffer): Promise<string> {
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function computeFileSha256(
  file: File,
  onProgress?: (progressPercent: number) => void
): Promise<string> {
  if (file.size === 0) {
    throw new Error('Zero-byte file rejected: cannot compute SHA-256 on empty file');
  }

  // Report starting progress
  if (onProgress) onProgress(10);
  
  const arrayBuffer = await file.arrayBuffer();
  if (onProgress) onProgress(60);
  
  const hash = await computeBufferSha256(arrayBuffer);
  if (onProgress) onProgress(100);
  
  return hash;
}

export async function computeStringSha256(content: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(content);
  return computeBufferSha256(data.buffer as ArrayBuffer);
}

