"""
Main analysis worker.
Orchestrates the full DocDrift pipeline:
  1. Parse changed symbols from diff (real tree-sitter, or diff-text fallback)
  2. Load + index doc blocks (real Qdrant + embeddings)
  3. Score drift (real algorithm)
  4. Request LLM rewrites (mock or real)
  5. Open doc PR (mock or real)
  6. Return DashboardMetrics
"""

from __future__ import annotations
import asyncio
import difflib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.models.schemas import (
    CommitPayload,
    AnalysisJob,
    DashboardMetrics,
    DriftResult,
    RepoHealth,
    PRRequest,
    JobStatus,
    DocPRPreview,
    CodeSymbol,
)
from app.services.llm_service import openai_llm_rewrite
from app.services.symbol_extractor import (
    extract_changed_symbols,
    extract_symbols_from_directory,
    extract_symbols_from_diff_text,
)
from app.services.doc_parser import parse_all_docs, parse_docs_from_dict
from app.services.vector_index import index_doc_blocks, build_symbol_doc_map
from app.services.drift_scorer import score_all_blocks, compute_repo_freshness
from app.services.github_service import choose_github_pr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# STUB — persistent job storage (implement)
# ---------------------------------------------------------------------------

class PersistenceLayer:
    """
    Persistent storage for AnalysisJob objects using SQLite.
    """

    DB_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "jobs.db")
    )

    def __init__(self) -> None:
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, job: "AnalysisJob") -> None:
        """Persist a job to the SQLite job store."""
        payload = job.model_dump_json()
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs (id, data) VALUES (?, ?)",
                (job.job_id, payload),
            )
            conn.commit()

    def load(self, job_id: str) -> Optional["AnalysisJob"]:
        """Load a job by ID from the SQLite job store."""
        with sqlite3.connect(self.DB_PATH) as conn:
            row = conn.execute(
                "SELECT data FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return AnalysisJob.model_validate_json(row[0])

    def list_all(self) -> List["AnalysisJob"]:
        """Return all jobs newest-first from the SQLite job store."""
        with sqlite3.connect(self.DB_PATH) as conn:
            rows = conn.execute("SELECT data FROM jobs").fetchall()
        jobs = [AnalysisJob.model_validate_json(row[0]) for row in rows]
        return sorted(jobs, key=lambda job: job.created_at, reverse=True)


_persistence = PersistenceLayer()

# In-memory job store — replaced by _persistence once implemented
_jobs: dict[str, AnalysisJob] = {}


def save_job(job: AnalysisJob) -> None:
    """Persist a job and keep the in-memory cache in sync."""
    _jobs[job.job_id] = job
    _persistence.save(job)


def _build_doc_diff(doc_path: str, original: str, revised: str) -> Tuple[str, int, int]:
    """Unified diff for one doc section (local PR preview, not GitHub)."""
    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(),
            revised.splitlines(),
            fromfile=f"a/{doc_path}",
            tofile=f"b/{doc_path}",
            lineterm="",
        )
    )
    diff_text = "\n".join(diff_lines) if diff_lines else (
        f"--- a/{doc_path}\n+++ b/{doc_path}\n@@ section @@\n{revised}"
    )
    additions = sum(
        1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++")
    )
    deletions = sum(
        1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---")
    )
    return diff_text, additions, deletions


def get_job(job_id: str) -> Optional[AnalysisJob]:
    job = _jobs.get(job_id)
    if job:
        return job
    job = _persistence.load(job_id)
    if job:
        _jobs[job_id] = job
    return job


def list_jobs() -> List[AnalysisJob]:
    return _persistence.list_all()


async def run_analysis(
    job: AnalysisJob,
    commit: CommitPayload,
    llm_api_key: Optional[str] = None,
    github_token: Optional[str] = None,
    markdown_docs: Optional[Dict[str, str]] = None,  # real GitHub docs keyed by path
) -> None:
    """
    Run the full DocDrift pipeline for a commit.
    When markdown_docs is provided the pipeline runs against a real GitHub repo;
    otherwise it falls back to the local sample_repo.
    Updates job in-place.
    """
    save_job(job)
    job.status = JobStatus.RUNNING
    save_job(job)
    is_real_repo = markdown_docs is not None
    logger.info(
        "Starting analysis job=%s commit=%s real_repo=%s real_llm=%s real_github=%s",
        job.job_id,
        commit.commit_sha,
        is_real_repo,
        bool(llm_api_key or settings.LLM_API_KEY),
        bool(github_token or settings.GITHUB_TOKEN),
    )

    try:
        # ----------------------------------------------------------------
        # 1. Collect all changed symbol names across touched files
        # ----------------------------------------------------------------
        changed_symbol_names: List[str] = []

        for file_diff in commit.changed_files:
            if is_real_repo:
                # No local files — extract purely from the diff text
                touched = extract_symbols_from_diff_text(file_diff.patch)
            else:
                full_path = os.path.join(settings.SAMPLE_REPO_PATH, file_diff.path)
                if os.path.exists(full_path) and full_path.endswith(".py"):
                    touched = extract_changed_symbols(file_diff.patch, full_path)
                else:
                    touched = extract_symbols_from_diff_text(file_diff.patch)
            changed_symbol_names.extend(touched)

        changed_symbol_names = list(set(changed_symbol_names))
        logger.info("Changed symbols: %s", changed_symbol_names)

        # ----------------------------------------------------------------
        # 2. Load all symbols from repo (for explicit linking)
        # ----------------------------------------------------------------
        if is_real_repo:
            # Synthesise lightweight CodeSymbol objects from the diff
            all_symbols: List[CodeSymbol] = []
            for name in changed_symbol_names:
                all_symbols.append(CodeSymbol(
                    name=name, kind="function", file_path="<github>",
                    start_line=1, end_line=1,
                ))
        else:
            repo_src = os.path.join(settings.SAMPLE_REPO_PATH, "src")
            all_symbols = extract_symbols_from_directory(repo_src)

        # ----------------------------------------------------------------
        # 3. Load & parse all doc blocks
        # ----------------------------------------------------------------
        read_counts = {}
        if settings.USE_MOCKS and not is_real_repo:
            from app.mocks.mock_interfaces import get_mock_read_counts
            read_counts = get_mock_read_counts()

        if is_real_repo:
            doc_blocks = parse_docs_from_dict(markdown_docs, read_counts)
            analyzed_files = list(markdown_docs.keys())
        else:
            docs_dir = os.path.join(settings.SAMPLE_REPO_PATH, "docs")
            doc_blocks = parse_all_docs(docs_dir, read_counts)
            analyzed_files = ["sample_repo/docs/api_reference.md"]

        if not doc_blocks:
            # Fallback: no docs found — still produce a valid (empty) result
            logger.warning("No doc blocks found for job=%s", job.job_id)

        logger.info("Parsed %d doc blocks", len(doc_blocks))

        # ----------------------------------------------------------------
        # 4. Build symbol↔doc links (explicit mentions + embeddings)
        # ----------------------------------------------------------------
        build_symbol_doc_map(doc_blocks, all_symbols)
        index_doc_blocks(doc_blocks)  # upsert into Qdrant

        # ----------------------------------------------------------------
        # 5. Score drift for each block
        # ----------------------------------------------------------------
        drift_results = score_all_blocks(
            doc_blocks, changed_symbol_names, commit.timestamp
        )

        # ----------------------------------------------------------------
        # 6. LLM rewrites for drifted blocks
        # ----------------------------------------------------------------
        stale = [r for r in drift_results if r.drift_score > 30]
        logger.info("Requesting rewrites for %d stale blocks", len(stale))

        diff_context = "\n\n".join(
            f"File: {fd.path}\n{fd.patch}" for fd in commit.changed_files
        )

        api_key = llm_api_key.strip() if llm_api_key else settings.LLM_API_KEY
        use_real_llm = bool(api_key)

        if use_real_llm:
            logger.info("Using real LLM for rewrites")
            rewrite_fn = lambda heading, original, diff: openai_llm_rewrite(
                heading, original, diff, api_key, settings.LLM_MODEL,
            )
        else:
            from app.mocks.mock_interfaces import mock_llm_rewrite
            logger.info("Using mock LLM rewrites")
            rewrite_fn = mock_llm_rewrite

        rewrite_tasks = [
            rewrite_fn(r.section_heading, r.original_content, diff_context)
            for r in stale
        ]
        rewrites = await asyncio.gather(*rewrite_tasks)
        for result, rewrite in zip(stale, rewrites):
            result.suggested_rewrite = rewrite

        # ----------------------------------------------------------------
        # 7. Open a doc PR for drifted blocks with rewrites
        # ----------------------------------------------------------------
        if stale:
            file_changes: dict[str, str] = {
                r.doc_path: r.suggested_rewrite
                for r in stale
                if r.suggested_rewrite
            }

            pr_req = PRRequest(
                repo=commit.repo,
                base_branch=commit.branch,
                head_branch=f"docdrift/fix-{commit.commit_sha[:7]}",
                title=f"docs: fix drift after {commit.commit_sha[:7]}",
                body=f"Auto-generated by DocDrift.\n\n{len(stale)} stale blocks updated.",
                file_changes=file_changes,
            )

            pr_resp = None
            if github_token and not settings.USE_MOCKS:
                try:
                    logger.info("Using real GitHub PR creation")
                    pr_resp = await choose_github_pr(pr_req, github_token)
                except Exception as exc:
                    logger.exception(
                        "Real GitHub PR creation failed, falling back to local preview",
                        exc_info=exc,
                    )

            if pr_resp is None:
                from app.mocks.mock_interfaces import mock_create_pr
                logger.info("Using local PR preview")
                pr_resp = await mock_create_pr(pr_req)

            for r in stale:
                if not r.suggested_rewrite:
                    continue
                diff_text, adds, dels = _build_doc_diff(
                    r.doc_path, r.original_content, r.suggested_rewrite
                )
                r.pr_preview = DocPRPreview(
                    pr_number=pr_resp.pr_number,
                    repo=commit.repo,
                    title=pr_req.title,
                    body=(
                        f"{pr_req.body}\n\n"
                        f"### Section\n{r.section_heading}\n\n"
                        f"Doc path: `{r.doc_path}`"
                    ),
                    base_branch=pr_req.base_branch,
                    head_branch=pr_resp.head_branch,
                    status=pr_resp.status,
                    author="docdrift-bot[bot]",
                    doc_path=r.doc_path,
                    section_heading=r.section_heading,
                    diff=diff_text,
                    additions=adds,
                    deletions=dels,
                )
                r.pr_url = pr_resp.pr_url

        # ----------------------------------------------------------------
        # 8. Build repo health + dashboard metrics
        # ----------------------------------------------------------------
        freshness = compute_repo_freshness(drift_results)
        stale_count = sum(1 for r in drift_results if r.drift_score > 40)
        critical_count = sum(1 for r in drift_results if r.drift_score > 70)

        repo_health = RepoHealth(
            repo=commit.repo,
            freshness_score=freshness,
            total_doc_blocks=len(doc_blocks),
            stale_blocks=stale_count,
            critical_blocks=critical_count,
            last_analyzed=datetime.now(timezone.utc),
            analyzed_files=analyzed_files,
        )

        job.result = DashboardMetrics(
            repo_health=repo_health,
            drift_results=drift_results,
            recent_commits=[commit],
        )
        job.status = JobStatus.DONE
        job.completed_at = datetime.now(timezone.utc)
        save_job(job)
        logger.info(
            "Analysis done job=%s freshness=%.1f stale=%d",
            job.job_id, freshness, stale_count,
        )

    except Exception as exc:
        logger.exception("Analysis failed job=%s", job.job_id)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        save_job(job)
