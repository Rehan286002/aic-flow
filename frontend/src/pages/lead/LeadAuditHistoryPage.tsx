import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  RotateCcw,
  Binary,
  GitCommit,
  Layers,
  Flame,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useDemoScenario } from '@/features/demo/demoContext';
import {
  buildMerkleTree,
  generateMerkleInclusionProof,
  type MerkleInclusionProof,
} from '@/features/demo/merkleLedger';

export const LeadAuditHistoryPage: React.FC = () => {
  const { demoState, toggleTamperEvent, resetDemo } = useDemoScenario();
  const [selectedLeafIndex, setSelectedLeafIndex] = useState<number>(0);
  const [inclusionProof, setInclusionProof] = useState<MerkleInclusionProof | null>(null);
  const [merkleRoot, setMerkleRoot] = useState<string>('');

  const events = demoState.auditLedger;
  const isAnyTampered = events.some((e) => e.isTampered);

  // Recompute Merkle root and proof when events change
  useEffect(() => {
    let isMounted = true;

    const runCrypto = async () => {
      try {
        const leafStrings = events.map((e) =>
          e.isTampered ? (e.tamperedPayload || e.details) : e.details
        );
        const { root } = await buildMerkleTree(leafStrings);
        const proof = await generateMerkleInclusionProof(
          leafStrings,
          Math.min(selectedLeafIndex, leafStrings.length - 1)
        );

        if (isMounted) {
          setMerkleRoot(root);
          setInclusionProof(proof);
        }
      } catch (err) {
        console.error('Crypto error computing Merkle tree:', err);
      }
    };

    void runCrypto();
    return () => {
      isMounted = false;
    };
  }, [events, selectedLeafIndex]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Lead Auditor</span>
            <span>/</span>
            <span>Cryptographic Proof &amp; Immutable Ledger</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Binary className="w-6 h-6 text-primary" />
            Audit Ledger &amp; RFC 6962 Merkle Verification
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Application: <span className="font-semibold text-foreground">{demoState.applicationNumber}</span> &bull; {demoState.institutionName}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={resetDemo}
            className="text-xs text-muted-foreground hover:text-foreground h-8"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Scenario
          </Button>
        </div>
      </div>

      {/* Security Status Banner */}
      {isAnyTampered ? (
        <div className="rounded-lg border-2 border-red-500 bg-red-50 p-5 shadow-xs animate-pulse">
          <div className="flex items-start gap-3.5">
            <div className="rounded-full bg-red-100 p-2 text-red-700">
              <Flame className="w-6 h-6 text-red-600" />
            </div>
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-red-900">
                  CRITICAL SECURITY ALERT: LEDGER TAMPERING DETECTED!
                </span>
                <Badge className="bg-red-600 text-white font-mono text-xs">
                  PROOF MISMATCH
                </Badge>
              </div>
              <p className="text-sm text-red-950 font-medium">
                One or more ledger event payloads have been altered. The Linear SHA-256 Hash Chain has broken and the RFC 6962 Merkle Root has diverged from the expected statutory anchor.
              </p>
              <div className="text-xs font-mono text-red-800 pt-1">
                Altered Root: <span className="font-bold underline">{merkleRoot}</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50/70 p-5 shadow-xs">
          <div className="flex items-start gap-3.5">
            <div className="rounded-full bg-emerald-100 p-2 text-emerald-700">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div className="space-y-1 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-900">
                  Cryptographic Ledger Integrity Intact
                </span>
                <Badge className="bg-emerald-600 text-white font-mono text-xs">
                  CHAIN VERIFIED
                </Badge>
              </div>
              <p className="text-xs text-emerald-950 leading-relaxed">
                All {events.length} audit trail events are strictly anchored in chronological linear order via Web Crypto SHA-256. Zero unauthorized modifications detected.
              </p>
              <div className="text-[11px] font-mono text-emerald-800 pt-0.5">
                RFC 6962 Merkle Root Anchor: <span className="font-bold">{merkleRoot}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audit Ledger Events Table with Tamper Simulator */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
            <GitCommit className="w-4 h-4 text-primary" />
            Linear Hash-Linked Audit Event Ledger
          </h2>
          <span className="text-xs text-muted-foreground">
            Click &ldquo;Simulate Tamper&rdquo; to test real-time cryptographic divergence
          </span>
        </div>

        <div className="space-y-3">
          {events.map((evt, idx) => {
            const isTampered = evt.isTampered;
            const isDownstreamFromTamper =
              events.slice(0, idx).some((e) => e.isTampered) && !isTampered;

            return (
              <div
                key={evt.sequenceNo}
                className={`rounded-lg border p-4 transition-all text-xs space-y-2.5 ${
                  isTampered
                    ? 'border-red-500 bg-red-50/80 shadow-xs'
                    : isDownstreamFromTamper
                    ? 'border-amber-400 bg-amber-50/50'
                    : 'border-border bg-card'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-foreground bg-muted px-2 py-0.5 rounded border text-[11px]">
                      Seq #{evt.sequenceNo}
                    </span>
                    <span className="font-bold text-foreground text-xs">{evt.action}</span>
                    <span className="text-muted-foreground text-[11px]">by {evt.actor}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-[10px] font-mono">
                      {new Date(evt.occurredAt).toLocaleString()}
                    </span>
                    <Button
                      size="sm"
                      variant={isTampered ? 'destructive' : 'outline'}
                      className="h-6 text-[10px] px-2 font-mono"
                      onClick={() => toggleTamperEvent(evt.sequenceNo)}
                    >
                      {isTampered ? 'Restore Original' : 'Simulate Tamper'}
                    </Button>
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-muted-foreground text-[10px] uppercase font-semibold block">
                    Event Payload Details:
                  </span>
                  <p
                    className={`font-mono text-xs leading-relaxed ${
                      isTampered ? 'text-red-950 font-bold underline' : 'text-foreground'
                    }`}
                  >
                    {isTampered && evt.tamperedPayload ? evt.tamperedPayload : evt.details}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1 font-mono text-[10px] text-muted-foreground border-t">
                  <div>
                    <span className="text-slate-500 select-none">Prev Hash: </span>
                    <span className="text-foreground truncate block">{evt.previousHash}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 select-none">Block Hash: </span>
                    <span
                      className={`truncate block ${
                        isTampered
                          ? 'text-red-700 font-bold underline'
                          : isDownstreamFromTamper
                          ? 'text-amber-700 font-bold'
                          : 'text-emerald-700'
                      }`}
                    >
                      {evt.currentHash}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* RFC 6962 Merkle Inclusion Proof Inspector */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3">
          <h2 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            RFC 6962 Mathematical Inclusion Proof Inspector
          </h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Select Target Leaf:</span>
            <select
              value={selectedLeafIndex}
              onChange={(e) => setSelectedLeafIndex(Number(e.target.value))}
              className="text-xs font-mono border rounded px-2 py-1 bg-background text-foreground"
            >
              {events.map((evt, idx) => (
                <option key={evt.sequenceNo} value={idx}>
                  Leaf #{idx + 1} ({evt.action})
                </option>
              ))}
            </select>
          </div>
        </div>

        {inclusionProof && (
          <div className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-md bg-muted/40 border">
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">
                  Target Leaf Hash (0x00 Prefix)
                </span>
                <span className="font-bold text-foreground truncate block">
                  {inclusionProof.leafHash}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">
                  Calculated Merkle Root
                </span>
                <span className="font-bold text-foreground truncate block">
                  {inclusionProof.calculatedRoot}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">
                  Proof Status
                </span>
                <Badge
                  variant="outline"
                  className={
                    inclusionProof.isValid
                      ? 'border-emerald-500 text-emerald-700 bg-emerald-50'
                      : 'border-red-500 text-red-700 bg-red-50'
                  }
                >
                  {inclusionProof.isValid ? 'MATHEMATICALLY VALID' : 'PROOF DIVERGENCE'}
                </Badge>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-muted-foreground text-[11px] font-sans font-semibold block">
                O(log N) Sibling Audit Path Steps:
              </span>
              {inclusionProof.auditPath.length === 0 ? (
                <p className="text-muted-foreground text-xs italic font-sans">
                  Single leaf tree; leaf hash is root.
                </p>
              ) : (
                <div className="space-y-1.5">
                  {inclusionProof.auditPath.map((step, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-2 rounded bg-muted/30 border text-[11px]"
                    >
                      <span className="text-muted-foreground font-sans">
                        Step #{idx + 1}:
                      </span>
                      <Badge variant="outline" className="text-[10px] uppercase">
                        {step.direction} sibling
                      </Badge>
                      <span className="text-foreground truncate flex-1">
                        {step.hash}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default LeadAuditHistoryPage;
