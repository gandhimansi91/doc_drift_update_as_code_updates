import React from 'react';
import type { DocPRPreview } from '../types';
import { X, GitPullRequest, GitBranch, User } from 'lucide-react';

interface Props {
  preview: DocPRPreview;
  onClose: () => void;
}

function DiffLine({ line }: { line: string }) {
  let className = 'text-white/55';
  if (line.startsWith('+++') || line.startsWith('---')) {
    className = 'text-white/35';
  } else if (line.startsWith('@@')) {
    className = 'text-blue-400/80';
  } else if (line.startsWith('+')) {
    className = 'text-emerald-400/90 bg-emerald-500/8';
  } else if (line.startsWith('-')) {
    className = 'text-red-400/90 bg-red-500/8';
  }
  return (
    <div className={`px-3 py-0.5 font-mono text-xs leading-relaxed whitespace-pre-wrap ${className}`}>
      {line || ' '}
    </div>
  );
}

export const PrPreviewModal: React.FC<Props> = ({ preview, onClose }) => {
  const diffLines = preview.diff.split('\n');
  const isRealPr = preview.pr_url && (preview.pr_url.includes('github.com') || preview.pr_url.includes('api.github.com'));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-2xl border border-white/10 bg-[#0d1117] shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-labelledby="pr-preview-title"
      >
        <div className="flex items-start justify-between gap-4 px-6 py-4 border-b border-white/8">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <GitPullRequest size={16} className="text-green-400 shrink-0" />
              <span className="text-xs font-mono text-white/40">{isRealPr ? 'Real PR' : 'Mock PR'} #{preview.pr_number}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 ring-1 ring-green-500/25 capitalize">
                {preview.status}
              </span>
              {!isRealPr && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300/90 ring-1 ring-amber-500/20">
                  Demo — not on GitHub
                </span>
              )}
            </div>
            <h2 id="pr-preview-title" className="text-lg font-semibold text-white/90 leading-snug">
              {preview.title}
            </h2>
            <p className="text-xs text-white/35 mt-1 font-mono truncate">{preview.repo}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white/80 hover:bg-white/8 transition-colors shrink-0"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-3 border-b border-white/6 flex flex-wrap items-center gap-4 text-xs text-white/45">
          <span className="flex items-center gap-1.5">
            <User size={12} />
            {preview.author}
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <GitBranch size={12} />
            <span className="text-emerald-400/90">{preview.head_branch}</span>
            <span className="text-white/25">→</span>
            <span>{preview.base_branch}</span>
          </span>
          <span className="text-emerald-400/80">+{preview.additions}</span>
          <span className="text-red-400/80">−{preview.deletions}</span>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-5">
          <div>
            <p className="text-xs uppercase tracking-widest text-white/25 mb-2">Description</p>
            <p className="text-sm text-white/65 whitespace-pre-wrap leading-relaxed font-mono">
              {preview.body}
            </p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-widest text-white/25 mb-2">
              Changed file — {preview.doc_path.split('/').slice(-2).join('/')}
            </p>
            <p className="text-xs text-white/35 mb-2 font-mono">{preview.section_heading}</p>
            <div className="rounded-lg border border-white/8 bg-black/40 overflow-hidden max-h-80 overflow-y-auto">
              {diffLines.map((line, i) => (
                <DiffLine key={`${i}-${line.slice(0, 8)}`} line={line} />
              ))}
            </div>
          </div>
        </div>

        <div className="px-6 py-3 border-t border-white/8 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm bg-white/8 hover:bg-white/12 text-white/80 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
