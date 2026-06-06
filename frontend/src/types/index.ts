export interface FileDiff {
  path: string;
  patch: string;
  additions: number;
  deletions: number;
}

export interface CommitPayload {
  repo: string;
  commit_sha: string;
  branch: string;
  author: string;
  message: string;
  timestamp: string;
  changed_files: FileDiff[];
}

export interface DocPRPreview {
  pr_number: number;
  repo: string;
  title: string;
  body: string;
  base_branch: string;
  head_branch: string;
  status: string;
  author: string;
  doc_path: string;
  section_heading: string;
  diff: string;
  additions: number;
  deletions: number;
}

export interface DriftResult {
  doc_block_id: string;
  doc_path: string;
  section_heading: string;
  drift_score: number;
  changed_symbols: string[];
  original_content: string;
  suggested_rewrite: string | null;
  pr_url: string | null;
  pr_preview: DocPRPreview | null;
}

export interface RepoHealth {
  repo: string;
  freshness_score: number;
  total_doc_blocks: number;
  stale_blocks: number;
  critical_blocks: number;
  last_analyzed: string;
  analyzed_files: string[];
}

export interface DashboardMetrics {
  repo_health: RepoHealth;
  drift_results: DriftResult[];
  recent_commits: CommitPayload[];
}

export type JobStatus = 'pending' | 'running' | 'done' | 'failed';

export interface AnalysisJob {
  job_id: string;
  repo: string;
  commit_sha: string;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  result: DashboardMetrics | null;
  error: string | null;
}

export interface MockCommit {
  index: number;
  sha: string;
  author: string;
  message: string;
  branch: string;
  files: string[];
}

export interface GithubCommit {
  sha: string;        // short (7-char)
  full_sha: string;
  author: string;
  message: string;
  branch: string;
  files: string[];
}
