import React, { useEffect, useState, useCallback } from 'react';
import type { AnalysisJob, JobStatus } from '../types';
import { pollJob } from '../hooks/useApi';
import { CheckCircle, XCircle, Loader2, Clock } from 'lucide-react';

interface Props {
  jobId: string;
  onDone: (job: AnalysisJob) => void;
}

const STEPS = [
  { key: 'pending', label: 'Queued' },
  { key: 'running', label: 'Parsing symbols…' },
  { key: 'running2', label: 'Scoring drift…' },
  { key: 'running3', label: 'Drafting rewrites…' },
  { key: 'done', label: 'Complete' },
];

function stepIndex(status: JobStatus, elapsed: number): number {
  if (status === 'pending') return 0;
  if (status === 'done') return 4;
  if (status === 'failed') return -1;
  if (elapsed < 1500) return 1;
  if (elapsed < 3000) return 2;
  return 3;
}

export const JobProgress: React.FC<Props> = ({ jobId, onDone }) => {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const j = await pollJob(jobId);
      setJob(j);
      if (j.status === 'done') { onDone(j); return; }
      if (j.status === 'failed') return;
      setTimeout(poll, 600);
    } catch (e: any) {
      setError(e.message);
    }
  }, [jobId, onDone]);

  useEffect(() => {
    poll();
    const timer = setInterval(() => setElapsed(e => e + 200), 200);
    return () => clearInterval(timer);
  }, [poll]);

  const status = job?.status ?? 'pending';
  const current = stepIndex(status, elapsed);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/3 p-8 flex flex-col items-center gap-6">
      {status === 'failed' ? (
        <div className="flex flex-col items-center gap-3 text-red-400">
          <XCircle size={40} />
          <p className="text-sm">Analysis failed: {job?.error || error || 'Unknown error'}</p>
        </div>
      ) : status === 'done' ? (
        <div className="flex flex-col items-center gap-2 text-emerald-400">
          <CheckCircle size={40} />
          <p className="text-sm font-medium">Analysis complete</p>
        </div>
      ) : (
        <Loader2 size={36} className="text-blue-400 animate-spin" />
      )}

      {/* Step track */}
      <div className="flex items-center gap-0">
        {STEPS.map((step, i) => (
          <React.Fragment key={step.key}>
            <div className="flex flex-col items-center gap-1.5">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all
                ${i < current ? 'bg-emerald-500/30 text-emerald-400 ring-1 ring-emerald-500/40'
                : i === current ? 'bg-blue-500/25 text-blue-300 ring-1 ring-blue-400/50 animate-pulse'
                : 'bg-white/5 text-white/20'}`}>
                {i < current ? '✓' : i + 1}
              </div>
              <span className={`text-xs whitespace-nowrap ${i === current ? 'text-white/70' : 'text-white/25'}`}>
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-px w-8 mb-5 transition-colors ${i < current ? 'bg-emerald-500/40' : 'bg-white/10'}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      <p className="text-xs text-white/30 font-mono">job: {jobId.slice(0, 8)}…</p>
    </div>
  );
};
