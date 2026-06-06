"""Shared Pydantic models / schemas used across the app."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Git / Webhook models
# ---------------------------------------------------------------------------

class FileDiff(BaseModel):
    path: str
    patch: str          # unified diff text
    additions: int
    deletions: int


class CommitPayload(BaseModel):
    repo: str
    commit_sha: str
    branch: str
    author: str
    message: str
    timestamp: datetime
    changed_files: List[FileDiff]


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

class CodeSymbol(BaseModel):
    name: str
    kind: str           # function | class | method | endpoint
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


# ---------------------------------------------------------------------------
# Documentation models
# ---------------------------------------------------------------------------

class DocBlock(BaseModel):
    id: str
    doc_path: str
    section_heading: str
    content: str
    symbols: List[str]  # symbol names this block references
    read_count: int = 0
    last_updated: datetime


class DocPRPreview(BaseModel):
    """Local mock PR payload for manual review (no external GitHub links)."""
    pr_number: int
    repo: str
    title: str
    body: str
    base_branch: str
    head_branch: str
    status: str
    author: str
    doc_path: str
    section_heading: str
    diff: str
    additions: int
    deletions: int


class DriftResult(BaseModel):
    doc_block_id: str
    doc_path: str
    section_heading: str
    drift_score: float          # 0–100
    changed_symbols: List[str]
    original_content: str
    suggested_rewrite: Optional[str] = None
    pr_url: Optional[str] = None          # deprecated; kept for API compat
    pr_preview: Optional[DocPRPreview] = None


# ---------------------------------------------------------------------------
# Dashboard / metrics
# ---------------------------------------------------------------------------

class RepoHealth(BaseModel):
    repo: str
    freshness_score: float      # 0–100 (100 = fully fresh)
    total_doc_blocks: int
    stale_blocks: int           # drift_score > 40
    critical_blocks: int        # drift_score > 70
    last_analyzed: datetime
    analyzed_files: List[str] = []   # markdown files scanned


class DashboardMetrics(BaseModel):
    repo_health: RepoHealth
    drift_results: List[DriftResult]
    recent_commits: List[CommitPayload]


# ---------------------------------------------------------------------------
# PR creation
# ---------------------------------------------------------------------------

class PRRequest(BaseModel):
    repo: str
    base_branch: str
    head_branch: str
    title: str
    body: str
    file_changes: Dict[str, str]    # path -> new content


class PRResponse(BaseModel):
    pr_number: int
    pr_url: str
    head_branch: str
    status: str


# ---------------------------------------------------------------------------
# Analysis job
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AnalysisJob(BaseModel):
    job_id: str
    repo: str
    commit_sha: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[DashboardMetrics] = None
    error: Optional[str] = None
