import React, { useState } from 'react';
import type { DriftResult } from '../types';
import { DriftBadge } from './DriftBadge';
import { PrPreviewModal } from './PrPreviewModal';
import { resolvePrPreview } from '../utils/prPreview';
import { ChevronDown, ChevronRight, GitPullRequest, Code2, BookOpen } from 'lucide-react';

interface Props {
  result: DriftResult;
  rank: number;
  repo?: string;
}

export const DriftCard: React.FC<Props> = ({ result, rank, repo }) => {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<'original' | 'rewrite'>('original');
  const [showPr, setShowPr] = useState(false);

  const hasRewrite = !!result.suggested_rewrite;
  const prPreview = resolvePrPreview(result, repo);
  const canViewPr = !!prPreview;

  return (
    <div
      className={`rounded-xl border transition-all duration-200 overflow-hidden
        ${result.drift_score >= 70
          ? 'border-red-500/30 bg-red-950/10'
          : result.drift_score >= 40
          ? 'border-amber-500/25 bg-amber-950/10'
          : 'border-white/8 bg-white/3'}`}
    >
      {/* Header row */}
      <button
        className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-white/4 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-white/25 font-mono text-xs w-5 shrink-0">#{rank}</span>

        <span className="flex-1 min-w-0">
          <span className="font-mono text-sm text-white/90 truncate block">
            {result.section_heading}
          </span>
          <span className="text-xs text-white/35 mt-0.5 block font-mono">
            {result.doc_path.split('/').slice(-2).join('/')}
          </span>
        </span>

        <div className="flex items-center gap-2 shrink-0">
          {result.changed_symbols.slice(0, 3).map(sym => (
            <span key={sym} className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/5 text-white/50 text-xs font-mono">
              <Code2 size={10} />
              {sym}
            </span>
          ))}
          {result.changed_symbols.length > 3 && (
            <span className="text-xs text-white/30">+{result.changed_symbols.length - 3}</span>
          )}
          <DriftBadge score={result.drift_score} size="sm" />
          {open ? <ChevronDown size={14} className="text-white/30" /> : <ChevronRight size={14} className="text-white/30" />}
        </div>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="border-t border-white/6 px-5 pb-5 pt-4">
          {/* Tabs */}
          <div className="flex gap-1 mb-4">
            {(['original', 'rewrite'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                disabled={t === 'rewrite' && !hasRewrite}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                  ${tab === t
                    ? 'bg-white/10 text-white'
                    : 'text-white/35 hover:text-white/60 disabled:opacity-20 disabled:cursor-not-allowed'}`}
              >
                {t === 'original' ? (
                  <><BookOpen size={11} className="inline mr-1.5" />Current Doc</>
                ) : (
                  <><Code2 size={11} className="inline mr-1.5" />Suggested Rewrite</>
                )}
              </button>
            ))}
            {canViewPr && (
              <button
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  setShowPr(true);
                }}
                className="ml-auto flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/15 transition-colors"
              >
                <GitPullRequest size={11} />
                View PR
              </button>
            )}
          </div>

          {/* Content pane */}
          <div className="rounded-lg bg-black/30 border border-white/6 p-4 text-sm text-white/70 font-mono whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
            {tab === 'original'
              ? result.original_content
              : result.suggested_rewrite ?? 'No rewrite available'}
          </div>

          {/* Symbol pills */}
          {result.changed_symbols.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              <span className="text-xs text-white/25 mr-1">Affected symbols:</span>
              {result.changed_symbols.map(sym => (
                <span key={sym} className="px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 text-xs font-mono">
                  {sym}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {showPr && prPreview && (
        <PrPreviewModal preview={prPreview} onClose={() => setShowPr(false)} />
      )}
    </div>
  );
};
