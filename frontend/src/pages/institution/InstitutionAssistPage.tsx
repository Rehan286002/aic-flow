import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Bookmark,
  CheckCircle2,
  ArrowRight,
  FileText,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  searchAphHandbook,
  APH_HANDBOOK_CHUNKS,
  type AphChunk,
} from '@/features/assist/aphHandbookData';

export const InstitutionAssistPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeResults, setActiveResults] = useState<AphChunk[]>(APH_HANDBOOK_CHUNKS);

  const handleSearch = (q: string) => {
    setSearchQuery(q);
    setActiveResults(searchAphHandbook(q));
  };

  const quickPrompts = [
    'Affidavit 2 Stamp Paper Rules',
    'Structural Stability 30-Year Cutoff',
    'Fire Safety Clearances',
    'ICAI UDIN Requirement',
    'Fee Exemption Guidelines',
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Institution</span>
            <span>/</span>
            <span>Regulatory Help &amp; Guidelines</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <img src="/aic-flow.svg" alt="AIC Logo" className="w-7 h-7 object-contain" />
            AICTE Regulatory Compliance Knowledge Base
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Applicant self-disclosure instructions and documentation norms under AICTE Approval Process Handbook (APH 2024–2027)
          </p>
        </div>

        <Button
          size="sm"
          variant="outline"
          className="text-xs h-8"
          onClick={() => navigate('/institution/rectification')}
        >
          <FileText className="w-3.5 h-3.5 mr-1 text-primary" />
          Rectification Center
        </Button>
      </div>

      {/* Search Bar & Quick Prompts */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs p-5 space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
          <Input
            placeholder="Search guidelines (e.g. 'Structural Stability', 'Affidavit 2', 'UDIN')..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground text-[11px] flex items-center gap-1">
            <Bookmark className="w-3.5 h-3.5 text-primary" />
            Common Inquiries:
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

      {/* Guidance Cards */}
      <div className="space-y-4">
        {activeResults.map((chunk) => (
          <div
            key={chunk.id}
            className="rounded-lg border bg-card text-card-foreground shadow-xs p-6 space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border-b pb-3">
              <div>
                <span className="font-mono font-bold text-xs bg-muted text-foreground px-2 py-0.5 rounded border inline-block mb-1">
                  {chunk.requirementCode} &bull; {chunk.chapter}
                </span>
                <h2 className="text-base font-bold text-foreground">
                  {chunk.title}
                </h2>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                Page {chunk.pageNumber}
              </Badge>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              {chunk.summary}
            </p>

            {/* Official Verbatim Excerpt */}
            <div className="rounded-md border p-3.5 bg-muted/30 text-xs font-serif leading-relaxed text-foreground">
              <span className="text-[10px] font-sans font-bold uppercase tracking-wider text-muted-foreground block mb-1">
                Official Rule Text:
              </span>
              &ldquo;{chunk.verbatimText}&rdquo;
            </div>

            {/* Applicant Checkpoints */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider block">
                Filing Checklist for Applicants:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {chunk.mandatoryCheckpoints.map((cp, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded border bg-background text-[11px] text-muted-foreground flex items-start gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{cp}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-between items-center text-xs text-muted-foreground border-t">
              <span className="font-mono text-[11px]">{chunk.citation}</span>
              {chunk.requirementCode === 'EOA-SD-04' && (
                <Button
                  size="sm"
                  className="h-7 text-xs bg-primary text-primary-foreground"
                  onClick={() => navigate('/institution/rectification')}
                >
                  Rectify Deficiency
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
export default InstitutionAssistPage;
