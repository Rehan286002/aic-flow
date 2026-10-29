import React, { useState } from 'react';
import {
  Search,
  Bookmark,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  searchAphHandbook,
  APH_HANDBOOK_CHUNKS,
  type AphChunk,
} from '@/features/assist/aphHandbookData';

export const AuditorAssistPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeResults, setActiveResults] = useState<AphChunk[]>(APH_HANDBOOK_CHUNKS);

  const handleSearch = (q: string) => {
    setSearchQuery(q);
    setActiveResults(searchAphHandbook(q));
  };

  const quickPrompts = [
    'Affidavit 2 Stamp Paper Rules',
    'Structural Stability 30-Year Cutoff',
    'Fire Safety Issuing Authority',
    'ICAI UDIN Requirement',
    'Land Area Revenue Contradiction',
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Auditor</span>
            <span>/</span>
            <span>AIC Assist Handbook Guidance</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <img src="/aic-flow.svg" alt="AIC Logo" className="w-7 h-7 object-contain" />
            AICTE Regulatory Handbook Assistant (Auditor Edition)
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Verbatim statutory clauses, citations, and evaluation criteria from AICTE Approval Process Handbook (APH 2024–2027)
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary py-1 px-3 self-start sm:self-auto">
          AICTE APH 2024–2027 &bull; Official Bureau Edition
        </Badge>
      </div>

      {/* Search Bar & Quick Prompts */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
          <Input
            placeholder="Search regulations by requirement (e.g. 'EOA-SD-04'), keyword, or clause..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground text-[11px] flex items-center gap-1">
            <Bookmark className="w-3.5 h-3.5 text-primary" />
            Suggested Topics:
          </span>
          {quickPrompts.map((prompt) => (
            <Button
              key={prompt}
              variant="outline"
              size="sm"
              className="h-6 text-[11px] px-2 text-muted-foreground hover:text-foreground"
              onClick={() => handleSearch(prompt)}
            >
              {prompt}
            </Button>
          ))}
          {searchQuery && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[11px] px-2 text-primary"
              onClick={() => handleSearch('')}
            >
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Showing {activeResults.length} Authoritative Handbook Provisions</span>
          <span className="font-mono">Verbatim Statutory Citations Enforced</span>
        </div>

        {activeResults.map((chunk) => (
          <div
            key={chunk.id}
            className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-4 transition-all hover:border-primary/50"
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b pb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono font-bold text-xs bg-primary/10 text-primary px-2 py-0.5 rounded border border-primary/20">
                    {chunk.requirementCode}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {chunk.chapter} &bull; {chunk.clause}
                  </span>
                </div>
                <h2 className="text-base font-bold text-foreground">
                  {chunk.title}
                </h2>
              </div>

              <Badge
                variant="outline"
                className="bg-muted text-foreground border-muted-foreground/30 font-mono text-[11px] py-1 px-2.5 whitespace-nowrap self-start sm:self-auto"
              >
                Page {chunk.pageNumber}
              </Badge>
            </div>

            {/* Verbatim Quote Box */}
            <div className="rounded-md border border-primary/20 bg-primary/5 p-4 text-xs font-serif leading-relaxed text-foreground">
              <span className="text-[10px] font-sans font-bold uppercase tracking-wider text-primary block mb-1">
                Official Verbatim Handbook Text:
              </span>
              &ldquo;{chunk.verbatimText}&rdquo;
            </div>

            {/* Checkpoints & Citation */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
              <div className="space-y-1.5">
                <span className="font-semibold text-foreground text-[11px] uppercase tracking-wider block">
                  Mandatory Auditor Checkpoints:
                </span>
                <ul className="list-disc pl-4 space-y-1 text-muted-foreground text-[11px]">
                  {chunk.mandatoryCheckpoints.map((cp, idx) => (
                    <li key={idx}>{cp}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-1.5 flex flex-col justify-between">
                <div className="space-y-1">
                  <span className="font-semibold text-foreground text-[11px] uppercase tracking-wider block">
                    Statutory Citation:
                  </span>
                  <p className="font-mono text-muted-foreground text-[11px] bg-muted/40 p-2 rounded border">
                    {chunk.citation}
                  </p>
                </div>
                <p className="text-[10px] text-muted-foreground italic">
                  Deterministic citation verified against official AICTE 2024-2027 Approval Process Handbook.
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
export default AuditorAssistPage;
