"""
Per-author doc-debt report.

STATUS: ✅ BUILT
  Correlates codebase authors via Git history to identify the accumulation of doc debt.
"""

from __future__ import annotations
import httpx
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.models.schemas import DriftResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AuthorDebt:
    """Accumulated doc debt for a single author."""
    author: str
    total_drift_score: float = 0.0
    stale_sections: List[str] = field(default_factory=list)   # section_heading strings
    doc_paths: List[str] = field(default_factory=list)         # unique doc file paths
    changed_symbols: List[str] = field(default_factory=list)   # symbols they changed


@dataclass
class DocDebtReport:
    """Full doc-debt report for a repo at a point in time."""
    repo: str
    commit_sha: str
    authors: List[AuthorDebt] = field(default_factory=list)    # sorted by total_drift_score desc
    total_stale_blocks: int = 0
    generated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

async def generate_doc_debt_report(
    repo: str,
    commit_sha: str,
    drift_results: List[DriftResult],
    github_token: Optional[str] = None,
) -> DocDebtReport:
    """
    Build a per-author doc-debt report from drift results.
    """
    stale = [r for r in drift_results if r.drift_score > 40]
    logger.info("Generating doc-debt report for %d stale blocks", len(stale))
    author_map: Dict[str, AuthorDebt] = {}
    
    for result in stale:
        for symbol in result.changed_symbols:
            author = await _get_symbol_author(repo, symbol, result.doc_path, github_token)
            if author not in author_map:
                author_map[author] = AuthorDebt(author=author)
                
            author_map[author].total_drift_score += result.drift_score
            if result.section_heading not in author_map[author].stale_sections:
                author_map[author].stale_sections.append(result.section_heading)
            if result.doc_path not in author_map[author].doc_paths:
                author_map[author].doc_paths.append(result.doc_path)
            if symbol not in author_map[author].changed_symbols:
                author_map[author].changed_symbols.append(symbol)
                
    sorted_authors = sorted(author_map.values(), key=lambda a: a.total_drift_score, reverse=True)

    return DocDebtReport(
        repo=repo,
        commit_sha=commit_sha,
        authors=sorted_authors,
        total_stale_blocks=len(stale),
    )


async def _get_symbol_author(
    repo: str,
    symbol_name: str,
    doc_path: str,
    github_token: Optional[str],
) -> str:
    """
    Return the GitHub login or email of the engineer who last changed symbol_name.
    """
    if not github_token:
        return "unknown"
        
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"https://api.github.com/repos/{repo}/commits?path={doc_path}&per_page=1"
        headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and "author" in data[0] and data[0]["author"]:
                return data[0]["author"].get("login", "unknown")
            elif data and isinstance(data, list) and "commit" in data[0] and "author" in data[0]["commit"]:
                return data[0]["commit"]["author"].get("name", "unknown")
                
    return "unknown"
