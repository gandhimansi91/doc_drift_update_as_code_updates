import axios from 'axios';
import type { AnalysisJob, DashboardMetrics, MockCommit, GithubCommit } from '../types';

const api = axios.create({
  // Relative URL uses Vite dev proxy (avoids CORS when port !== 3000)
  baseURL: '/api',
  timeout: 60000,
});

export async function triggerAnalysis(
  commitIndex: number,
  customPatch?: string | null,
  customPath?: string | null,
  githubToken?: string | null,
): Promise<{ job_id: string; commit: string }> {
  const body: Record<string, any> = { commit_index: commitIndex };
  if (customPatch) body.custom_patch = customPatch;
  if (customPath) body.custom_path = customPath;
  if (githubToken) body.github_token = githubToken;
  const res = await api.post('/webhook/github', body);
  return res.data;
}

export async function getConfig(): Promise<Record<string, any>> {
  const res = await api.get('/config');
  return res.data;
}

export async function pollJob(jobId: string): Promise<AnalysisJob> {
  const res = await api.get(`/jobs/${jobId}`);
  return res.data;
}

export async function getDashboard(jobId: string): Promise<DashboardMetrics> {
  const res = await api.get(`/dashboard/${jobId}`);
  return res.data;
}

export async function listJobs(): Promise<AnalysisJob[]> {
  const res = await api.get('/jobs');
  return res.data;
}

export async function listMockCommits(): Promise<MockCommit[]> {
  const res = await api.get('/mock/commits');
  return res.data;
}

export async function fetchGithubCommits(
  repo: string,
  token: string,
  limit = 5,
): Promise<GithubCommit[]> {
  const res = await api.post('/github/commits', { repo, github_token: token, limit });
  return res.data;
}

export async function analyzeGithubRepo(
  repo: string,
  sha: string,
  githubToken: string,
  llmApiKey?: string,
): Promise<{ job_id: string; commit: string }> {
  const body: Record<string, any> = { repo, sha, github_token: githubToken };
  if (llmApiKey) body.llm_api_key = llmApiKey;
  const res = await api.post('/analyze/repo', body);
  return res.data;
}

export async function validateGithubToken(token: string): Promise<{
  connected: boolean;
  login: string | null;
  name: string | null;
  scopes: string | null;
  error: string | null;
}> {
  const res = await api.post('/github/validate', { token });
  return res.data;
}
