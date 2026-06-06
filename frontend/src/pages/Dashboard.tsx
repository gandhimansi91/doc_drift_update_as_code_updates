import React, { useState, useCallback, useEffect, useRef } from 'react';
import type { AnalysisJob, DashboardMetrics, MockCommit, GithubCommit } from '../types';
import {
  triggerAnalysis, listMockCommits, getConfig,
  validateGithubToken, fetchGithubCommits, analyzeGithubRepo,
} from '../hooks/useApi';
import { JobProgress } from '../components/JobProgress';
import { DriftCard } from '../components/DriftCard';
import { FreshnessGauge } from '../components/FreshnessGauge';
import { DriftBadge } from '../components/DriftBadge';
import {
  GitCommit, Play, BarChart3, FileText, AlertTriangle, Zap,
  RefreshCw, CheckCircle, XCircle, Loader, Github, Search,
} from 'lucide-react';

type View = 'home' | 'running' | 'dashboard';
type CommitMode = 'mock' | 'github';

export const Dashboard: React.FC = () => {
  const [view, setView] = useState<View>('home');
  const [commits, setCommits] = useState<MockCommit[]>([]);
  const [selectedCommit, setSelectedCommit] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterMin, setFilterMin] = useState(0);
  const [llmConfigured, setLlmConfigured] = useState(false);
  const [githubConfigured, setGithubConfigured] = useState(false);
  const [customPath, setCustomPath] = useState('');
  const [customPatch, setCustomPatch] = useState('');
  const [llmApiKey, setLlmApiKey] = useState('');

  // GitHub token + validation
  const [githubToken, setGithubToken] = useState('');
  const [githubValidating, setGithubValidating] = useState(false);
  const [githubConnected, setGithubConnected] = useState<boolean | null>(null);
  const [githubUser, setGithubUser] = useState<string | null>(null);
  const [githubScopes, setGithubScopes] = useState<string | null>(null);
  const [githubValidateError, setGithubValidateError] = useState<string | null>(null);
  const githubDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Real GitHub repo commits
  const [commitMode, setCommitMode] = useState<CommitMode>('mock');
  const [repoInput, setRepoInput] = useState('');
  const [githubCommits, setGithubCommits] = useState<GithubCommit[]>([]);
  const [selectedGithubCommit, setSelectedGithubCommit] = useState(0);
  const [fetchingCommits, setFetchingCommits] = useState(false);
  const [fetchCommitsError, setFetchCommitsError] = useState<string | null>(null);

  const [loadError, setLoadError] = useState<string | null>(null);
  const sortedResults = [...(metrics?.drift_results ?? [])].filter(r => r.drift_score >= filterMin);

  useEffect(() => {
    setLoadError(null);
    Promise.all([listMockCommits(), getConfig()])
      .then(([commitsRes, cfg]) => {
        setCommits(commitsRes);
        setLlmConfigured(Boolean(cfg.LLM_CONFIGURED));
        setGithubConfigured(Boolean(cfg.GITHUB_CONFIGURED));
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : 'Could not reach the API';
        setLoadError(msg);
      });
  }, []);

  const handleGithubTokenChange = (token: string) => {
    setGithubToken(token);
    setGithubConnected(null);
    setGithubUser(null);
    setGithubValidateError(null);
    setCommitMode('mock');
    setGithubCommits([]);
    if (githubDebounceRef.current) clearTimeout(githubDebounceRef.current);
    if (!token.trim()) return;
    setGithubValidating(true);
    githubDebounceRef.current = setTimeout(async () => {
      try {
        const result = await validateGithubToken(token.trim());
        setGithubConnected(result.connected);
        setGithubUser(result.login);
        setGithubScopes(result.scopes);
        setGithubValidateError(result.error);
      } catch {
        setGithubConnected(false);
        setGithubValidateError('Failed to reach backend');
      } finally {
        setGithubValidating(false);
      }
    }, 600);
  };

  const handleFetchCommits = async () => {
    if (!repoInput.trim() || !githubToken) return;
    const slug = parseRepoSlug(repoInput);
    if (!slug.includes('/')) {
      setFetchCommitsError('Enter a repo as owner/repo (e.g. owner/repo-name)');
      return;
    }
    setRepoInput(slug); // normalise the input field to clean slug
    setFetchingCommits(true);
    setFetchCommitsError(null);
    setGithubCommits([]);
    try {
      const result = await fetchGithubCommits(slug, githubToken, 5);
      if (result.length === 0) {
        setFetchCommitsError('No commits found in this repo.');
      } else {
        setGithubCommits(result);
        setSelectedGithubCommit(0);
        setCommitMode('github');
      }
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;
      if (status === 404) {
        setFetchCommitsError(`"${slug}" not found — if it's a private repo, your token needs the "repo" scope (GitHub → Settings → Developer settings → Personal access tokens → regenerate with "repo" checked).`);
      } else if (status === 401 || status === 403) {
        setFetchCommitsError('Token doesn\'t have permission. Regenerate it with "repo" scope.');
      } else {
        setFetchCommitsError(detail ?? e.message ?? 'Failed to fetch commits');
      }
    } finally {
      setFetchingCommits(false);
    }
  };

  const handleRun = async () => {
    setLoading(true);
    try {
      if (commitMode === 'github' && githubCommits.length > 0) {
        const chosen = githubCommits[selectedGithubCommit];
        const { job_id } = await analyzeGithubRepo(
          parseRepoSlug(repoInput),
          chosen.full_sha,
          githubToken,
          llmApiKey || undefined,
        );
        setJobId(job_id);
      } else {
        const { job_id } = await triggerAnalysis(
          selectedCommit,
          customPatch || undefined,
          customPath || undefined,
          githubToken || undefined,
        );
        setJobId(job_id);
      }
      setView('running');
    } catch (e: any) {
      alert(`Failed to start analysis: ${e?.response?.data?.detail ?? e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDone = useCallback((job: AnalysisJob) => {
    if (job.result) {
      setMetrics(job.result);
      setTimeout(() => setView('dashboard'), 600);
    }
  }, []);

  const handleReset = () => {
    setView('home');
    setJobId(null);
    setMetrics(null);
    setFilterMin(0);
  };

  const health = metrics?.repo_health;
  const isGithubMode = commitMode === 'github' && githubCommits.length > 0;

  const parseRepoSlug = (input: string): string => {
    // Accept "owner/repo", full GitHub URLs, or URLs with /tree/branch etc.
    const withoutOrigin = input.trim().replace(/^https?:\/\/(www\.)?github\.com\//, '');
    const parts = withoutOrigin.split('/').filter(Boolean);
    return parts.slice(0, 2).join('/');
  };

  return (
    <div className="min-h-screen bg-[#080b12] text-white" style={{ fontFamily: "'IBM Plex Mono', 'Fira Code', monospace" }}>
      {/* Top bar */}
      <header className="border-b border-white/6 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold">
            DD
          </div>
          <span className="font-bold tracking-tight text-white/90">DocDrift</span>
          <span className="text-white/20 text-xs">/ doc health monitor</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/70 text-white/80 ring-1 ring-white/10 flex items-center gap-1.5">
            {llmConfigured ? 'LLM: API' : 'LLM: Mock'}
            <span className="text-white/30">·</span>
            {githubConnected === true
              ? <span className="text-green-400 flex items-center gap-1"><CheckCircle size={10} /> GitHub: {githubUser}</span>
              : githubConfigured
                ? 'GitHub: Env'
                : 'GitHub: Mock'}
          </span>
          {view !== 'home' && (
            <button onClick={handleReset} className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors px-2 py-1 rounded hover:bg-white/5">
              <RefreshCw size={11} /> Reset
            </button>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">

        {/* HOME */}
        {view === 'home' && (
          <div className="space-y-10">
            <div>
              <h1 className="text-3xl font-bold text-white/90 mb-2">Doc Health Check</h1>
              <p className="text-white/40 text-sm leading-relaxed max-w-xl">
                Select a commit and run the analysis pipeline. DocDrift parses changed symbols,
                scores drift against linked doc blocks, drafts LLM rewrites, and surfaces a
                reviewable PR — all in seconds.
              </p>
            </div>

            {/* Credentials */}
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-widest text-white/30">API credentials (optional)</p>
              <input
                type="password"
                placeholder="LLM API key (e.g., sk-...)"
                value={llmApiKey}
                onChange={e => setLlmApiKey(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-white/25"
              />

              {/* GitHub token with live validation */}
              <div className="relative">
                <input
                  type="password"
                  placeholder="GitHub token (e.g., ghp_...)"
                  value={githubToken}
                  onChange={e => handleGithubTokenChange(e.target.value)}
                  className={`w-full rounded-xl border px-4 py-2 pr-10 text-sm text-white placeholder:text-white/25 bg-white/5 transition-colors
                    ${githubConnected === true ? 'border-green-500/50' : githubConnected === false ? 'border-red-500/40' : 'border-white/10'}`}
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {githubValidating && <Loader size={14} className="text-white/40 animate-spin" />}
                  {!githubValidating && githubConnected === true && <CheckCircle size={14} className="text-green-400" />}
                  {!githubValidating && githubConnected === false && <XCircle size={14} className="text-red-400" />}
                </div>
              </div>
              {githubConnected === true && githubUser && (
                <div className="space-y-1">
                  <p className="text-xs text-green-400/80 flex items-center gap-1">
                    <CheckCircle size={11} /> Connected as <span className="font-mono">@{githubUser}</span>
                  </p>
                  {githubScopes !== null && githubScopes !== '' && !githubScopes.split(',').map(s => s.trim()).includes('repo') && (
                    <p className="text-xs text-amber-400/80 flex items-center gap-1">
                      <AlertTriangle size={11} /> Classic token without <span className="font-mono">repo</span> scope — private repos may not be accessible.
                    </p>
                  )}
                </div>
              )}
              {githubConnected === false && (
                <p className="text-xs text-red-400/70 flex items-center gap-1">
                  <XCircle size={11} /> {githubValidateError ?? 'Invalid token'}
                </p>
              )}

              {/* GitHub repo picker — only when token is valid */}
              {githubConnected === true && (
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 space-y-3">
                  <p className="text-xs text-blue-400/80 flex items-center gap-1.5">
                    <Github size={12} /> Analyze a real GitHub repo
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="owner/repo or paste a GitHub URL"
                      value={repoInput}
                      onChange={e => { setRepoInput(e.target.value); setGithubCommits([]); setCommitMode('mock'); }}
                      className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/25"
                    />
                    <button
                      onClick={handleFetchCommits}
                      disabled={!repoInput.trim() || fetchingCommits}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600/80 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm transition-colors"
                    >
                      {fetchingCommits ? <Loader size={13} className="animate-spin" /> : <Search size={13} />}
                      Fetch
                    </button>
                  </div>
                  {fetchCommitsError && (
                    <p className="text-xs text-red-400/80 flex items-center gap-1">
                      <XCircle size={11} /> {fetchCommitsError}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Commit picker */}
            <div>
              {isGithubMode ? (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs uppercase tracking-widest text-white/30">
                      Recent commits · <span className="text-blue-400">{repoInput}</span>
                    </p>
                    <button
                      onClick={() => { setCommitMode('mock'); setGithubCommits([]); }}
                      className="text-xs text-white/30 hover:text-white/60 transition-colors"
                    >
                      ← Use demo scenarios
                    </button>
                  </div>
                  <div className="grid gap-3">
                    {githubCommits.map((c, i) => (
                      <button
                        key={c.full_sha}
                        onClick={() => setSelectedGithubCommit(i)}
                        className={`text-left rounded-xl border p-4 transition-all
                          ${selectedGithubCommit === i
                            ? 'border-blue-500/50 bg-blue-500/8 ring-1 ring-blue-500/20'
                            : 'border-white/8 bg-white/2 hover:border-white/15 hover:bg-white/4'}`}
                      >
                        <div className="flex items-start gap-3">
                          <GitCommit size={14} className={`mt-0.5 shrink-0 ${selectedGithubCommit === i ? 'text-blue-400' : 'text-white/30'}`} />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-mono text-xs text-white/30">{c.sha}</span>
                            </div>
                            <p className="text-sm text-white/80 leading-snug">{c.message}</p>
                            <p className="text-xs text-white/35 mt-1">{c.author}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-3">Select demo commit scenario</p>
                  <div className="grid gap-3">
                    {loadError ? (
                      <p className="text-red-400/90 text-sm">
                        Failed to load scenarios: {loadError}. Start the backend on port 8000, then refresh.
                      </p>
                    ) : commits.length === 0 ? (
                      <p className="text-white/30 text-sm animate-pulse">Loading scenarios…</p>
                    ) : (
                      commits.map((c, i) => (
                        <button
                          key={c.sha}
                          onClick={() => setSelectedCommit(i)}
                          className={`text-left rounded-xl border p-4 transition-all
                            ${selectedCommit === i
                              ? 'border-blue-500/50 bg-blue-500/8 ring-1 ring-blue-500/20'
                              : 'border-white/8 bg-white/2 hover:border-white/15 hover:bg-white/4'}`}
                        >
                          <div className="flex items-start gap-3">
                            <GitCommit size={14} className={`mt-0.5 shrink-0 ${selectedCommit === i ? 'text-blue-400' : 'text-white/30'}`} />
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-mono text-xs text-white/30">{c.sha}</span>
                                <span className="text-xs text-white/25 px-1.5 py-0.5 rounded bg-white/5">{c.branch}</span>
                              </div>
                              <p className="text-sm text-white/80 leading-snug">{c.message}</p>
                              <p className="text-xs text-white/35 mt-1">{c.author} · {c.files.join(', ')}</p>
                            </div>
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Custom input (shown when LLM key entered or LLM is configured) */}
            {(llmApiKey || llmConfigured) && !isGithubMode && (
              <div>
                <p className="text-xs uppercase tracking-widest text-white/30 mb-2">Custom input</p>
                <input
                  type="text"
                  placeholder="doc path (e.g. README.md)"
                  value={customPath}
                  onChange={e => setCustomPath(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-white/25 mb-2"
                />
                <label className="text-xs text-white/40">Patch / content to evaluate</label>
                <textarea
                  rows={6}
                  value={customPatch}
                  onChange={e => setCustomPatch(e.target.value)}
                  placeholder="Paste a unified diff or new section content here"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-white/25 mt-2"
                />
              </div>
            )}

            <button
              onClick={handleRun}
              disabled={loading || (!isGithubMode && commits.length === 0)}
              className="flex items-center gap-2.5 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors"
            >
              {loading ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
              {isGithubMode ? 'Analyze Real Repo' : 'Run Demo Analysis'}
            </button>
          </div>
        )}

        {/* RUNNING */}
        {view === 'running' && jobId && (
          <div className="max-w-lg mx-auto mt-16">
            <h2 className="text-xl font-bold mb-6 text-center">Analysing commit…</h2>
            <JobProgress jobId={jobId} onDone={handleDone} />
          </div>
        )}

        {/* DASHBOARD */}
        {view === 'dashboard' && metrics && health && (
          <div className="space-y-8">
            {/* Provenance banner — shows exactly what was analyzed */}
            <div className="rounded-xl border border-white/8 bg-white/2 px-5 py-4 space-y-2">
              <div className="flex items-center gap-2 text-xs text-white/50">
                <Github size={12} />
                <span className="font-mono text-white/70 font-semibold">{health.repo}</span>
                <span className="text-white/20">·</span>
                <span className="font-mono text-white/40">{metrics.recent_commits[0]?.commit_sha}</span>
                <span className="text-white/20">·</span>
                <span>{metrics.recent_commits[0]?.message}</span>
              </div>
              {health.analyzed_files.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  <span className="text-xs text-white/25">docs scanned:</span>
                  {health.analyzed_files.map(f => (
                    <span key={f} className="text-xs font-mono bg-white/5 px-2 py-0.5 rounded text-white/50 border border-white/8">{f}</span>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="col-span-2 md:col-span-1 rounded-2xl border border-white/8 bg-white/3 p-5 flex flex-col items-center justify-center">
                <FreshnessGauge score={health.freshness_score} />
                <p className="text-xs text-white/30 mt-2">Repo Freshness</p>
              </div>
              {[
                { label: 'Total Blocks', value: health.total_doc_blocks, icon: <FileText size={16} />, color: 'text-white/70' },
                { label: 'Stale Blocks', value: health.stale_blocks, icon: <AlertTriangle size={16} />, color: 'text-amber-400' },
                { label: 'Critical', value: health.critical_blocks, icon: <Zap size={16} />, color: 'text-red-400' },
              ].map(stat => (
                <div key={stat.label} className="rounded-2xl border border-white/8 bg-white/3 p-5 flex flex-col justify-between">
                  <div className={`${stat.color} mb-3`}>{stat.icon}</div>
                  <div>
                    <p className={`text-3xl font-bold font-mono ${stat.color}`}>{stat.value}</p>
                    <p className="text-xs text-white/30 mt-1">{stat.label}</p>
                  </div>
                </div>
              ))}
            </div>

            {metrics.recent_commits[0] && (
              <div className="rounded-xl border border-white/8 bg-white/2 px-5 py-3.5 flex items-center gap-3">
                <GitCommit size={13} className="text-white/30 shrink-0" />
                <span className="font-mono text-xs text-white/40">{metrics.recent_commits[0].commit_sha}</span>
                <span className="text-sm text-white/65 flex-1 truncate">{metrics.recent_commits[0].message}</span>
                <span className="text-xs text-white/30">{metrics.recent_commits[0].author}</span>
              </div>
            )}

            <div className="flex items-center gap-4">
              <BarChart3 size={15} className="text-white/30" />
              <p className="text-sm text-white/60">Drift results</p>
              <div className="flex gap-1 ml-auto">
                {[0, 15, 40, 70].map(min => (
                  <button
                    key={min}
                    onClick={() => setFilterMin(min)}
                    className={`px-3 py-1 rounded-lg text-xs transition-colors
                      ${filterMin === min ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/60'}`}
                  >
                    {min === 0 ? 'All' : `≥${min}`}
                  </button>
                ))}
              </div>
              <span className="text-xs text-white/25">{sortedResults.length} shown</span>
            </div>

            <div className="space-y-2">
              {sortedResults.length === 0 ? (
                <div className="text-center py-12 text-white/25 text-sm">No blocks above this threshold — docs look fresh!</div>
              ) : (
                sortedResults.map((result, i) => (
                  <DriftCard key={result.doc_block_id} result={result} rank={i + 1} repo={health.repo} />
                ))
              )}
            </div>

            <p className="text-center text-xs text-white/20 pb-4">
              Last analyzed {new Date(health.last_analyzed).toLocaleTimeString()} · {health.repo}
            </p>
          </div>
        )}
      </main>
    </div>
  );
};
