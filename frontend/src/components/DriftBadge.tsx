import React from 'react';

interface Props {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

function getColor(score: number): { bg: string; text: string; ring: string; label: string } {
  if (score >= 70) return { bg: 'bg-red-950/60', text: 'text-red-300', ring: 'ring-red-500/40', label: 'CRITICAL' };
  if (score >= 40) return { bg: 'bg-amber-950/60', text: 'text-amber-300', ring: 'ring-amber-500/40', label: 'STALE' };
  if (score >= 15) return { bg: 'bg-yellow-950/40', text: 'text-yellow-400', ring: 'ring-yellow-600/30', label: 'WARN' };
  return { bg: 'bg-emerald-950/40', text: 'text-emerald-400', ring: 'ring-emerald-600/30', label: 'FRESH' };
}

const sizes = {
  sm: { wrap: 'px-2 py-0.5 text-xs gap-1.5', dot: 'w-1.5 h-1.5' },
  md: { wrap: 'px-3 py-1 text-sm gap-2', dot: 'w-2 h-2' },
  lg: { wrap: 'px-4 py-1.5 text-base gap-2', dot: 'w-2.5 h-2.5' },
};

export const DriftBadge: React.FC<Props> = ({ score, size = 'md' }) => {
  const { bg, text, ring, label } = getColor(score);
  const s = sizes[size];
  return (
    <span
      className={`inline-flex items-center rounded-full font-mono font-semibold ring-1 ${bg} ${text} ${ring} ${s.wrap}`}
    >
      <span className={`rounded-full ${s.dot}`} style={{ background: 'currentColor', opacity: 0.8 }} />
      {score.toFixed(0)}
      <span className="opacity-60 text-[0.7em] tracking-widest">{label}</span>
    </span>
  );
};
