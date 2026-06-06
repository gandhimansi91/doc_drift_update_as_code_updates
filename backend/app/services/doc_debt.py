"""
Per-author doc-debt report.

STATUS: 🔶 STUB
  All functions return empty data. No attribution is computed.

The doc-debt report answers: "Which engineer owns the most stale documentation
right now, and which specific sections are they responsible for?"

It works by:
  1. For each stale doc block, find the code symbol it references
  2. Call git blame (or GitHub Commits API) to find who last changed that symbol
  3. Accumulate a debt score per author (sum of drift_scores they own)
  4. Return a ranked list: author → [stale blocks they own, total debt score]

TODO:
  Implement generate_doc_debt_report() and wire it into the analysis pipeline
  (call it in analysis_worker.py after step 5 — drift scoring — and include
  the report in DashboardMetrics or expose it via a new GET /api/report/debt endpoint).
"""

from __future__ import annotations
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
# STUB — main entrypoint
# ---------------------------------------------------------------------------

async def generate_doc_debt_report(
    repo: str,
    commit_sha: str,
    drift_results: List[DriftResult],
    github_token: Optional[str] = None,
) -> DocDebtReport:
    """
    Build a per-author doc-debt report from drift results.

    For each stale DriftResult:
      1. Look up which symbols the block references (result.changed_symbols)
      2. Call _get_symbol_author() to find who last changed each symbol
      3. Accumulate AuthorDebt objects keyed by author email/login
      4. Sort by total_drift_score descending

    Returns a DocDebtReport — currently empty because _get_symbol_author() is a stub.

    TODO: implement _get_symbol_author() below, then fill in
    the accumulation logic here.
    """
    # ── TODO: implement per-author accumulation ──
    stale = [r for r in drift_results if r.drift_score > 40]

    # TODO: replace this placeholder with real author attribution
    # Example of the accumulation logic candidates should implement:
    #
    # author_map: Dict[str, AuthorDebt] = {}
    # for result in stale:
    #     for symbol in result.changed_symbols:
    #         author = await _get_symbol_author(repo, symbol, github_token)
    #         if author not in author_map:
    #             author_map[author] = AuthorDebt(author=author)
    #         author_map[author].total_drift_score += result.drift_score
    #         author_map[author].stale_sections.append(result.section_heading)
    #         author_map[author].doc_paths.append(result.doc_path)
    #         author_map[author].changed_symbols.append(symbol)
    # sorted_authors = sorted(author_map.values(), key=lambda a: a.total_drift_score, reverse=True)

    return DocDebtReport(
        repo=repo,
        commit_sha=commit_sha,
        authors=[],          # TODO: replace with sorted_authors
        total_stale_blocks=len(stale),
    )


async def _get_symbol_author(
    repo: str,
    symbol_name: str,
    github_token: Optional[str],
) -> str:
    """
    Return the GitHub login or email of the engineer who last changed symbol_name.

    TODO — implement one of these approaches:

    Option A — GitHub Commits API (search by file + grep for symbol):
        GET /repos/{owner}/{repo}/commits?path={file_path}&per_page=1
        Extract commit.author.login from the first result.
        Limitation: attributes blame to last committer of the file, not the symbol.

    Option B — Git blame via subprocess (most accurate, requires local clone):
        result = subprocess.run(
            ["git", "blame", "-L", f"{start_line},{end_line}", "--porcelain", file_path],
            capture_output=True, text=True, cwd=repo_path
        )
        Parse the "author-mail" line from the porcelain output.

    Option C — GitHub GraphQL blame API:
        POST https://api.github.com/graphql
        Query: repository.object.blame.ranges[].commit.author.user.login
        Reference: https://docs.github.com/en/graphql/reference/objects#blame

    Returns "unknown" if attribution cannot be determined.
    """
    # ── TODO: implement symbol-to-author attribution ──
    return "unknown"  # TODO: implement git blame or GitHub Commits API lookup
