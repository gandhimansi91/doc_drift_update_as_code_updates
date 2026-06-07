"""
Confidence-gated auto-merge for doc-fix PRs.

STATUS: ✅ BUILT
  Heuristic safety gating and CI polling prior to merging PRs.
"""

from __future__ import annotations
import logging
import re
import httpx
from typing import Optional

from app.models.schemas import DriftResult, PRResponse

logger = logging.getLogger(__name__)

# Gate thresholds — tune conservatively; err on the side of human review
AUTO_MERGE_MAX_DRIFT = 45            # only auto-merge low-drift corrections
AUTO_MERGE_MIN_CONFIDENCE = 0.90     # LLM must be highly confident
AUTO_MERGE_REQUIRE_CI_PASS = True    # never merge if CI is failing


# ---------------------------------------------------------------------------
# Confidence scoring for a rewrite
# ---------------------------------------------------------------------------

async def score_rewrite_confidence(
    original_content: str,
    suggested_rewrite: str,
    diff_context: str,
    llm_api_key: Optional[str] = None,
) -> float:
    """
    Return a 0.0–1.0 confidence score for how safe the suggested rewrite is to auto-merge.
    """
    score = 1.0
    # Penalise large rewrites (more likely to introduce errors)
    size_ratio = len(suggested_rewrite) / max(len(original_content), 1)
    if size_ratio > 2.0: 
        score -= 0.3
    # Penalise rewrites that drop technical terms from the original
    original_terms = set(re.findall(r"`[^`]+`", original_content))
    rewrite_terms  = set(re.findall(r"`[^`]+`", suggested_rewrite))
    dropped = original_terms - rewrite_terms
    score -= 0.1 * len(dropped)
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Gate check
# ---------------------------------------------------------------------------

async def should_auto_merge(
    drift_result: DriftResult,
    pr_number: int,
    repo: str,
    github_token: Optional[str],
    confidence_score: Optional[float] = None,
) -> bool:
    """
    Return True if the doc-fix PR is safe to merge automatically.

    Checks (in order — all must pass):
      1. drift_score       < AUTO_MERGE_MAX_DRIFT
      2. confidence_score  > AUTO_MERGE_MIN_CONFIDENCE
      3. CI checks on the PR are all passing (if AUTO_MERGE_REQUIRE_CI_PASS)
    """
    logger.info("Evaluating auto-merge gates for PR #%d", pr_number)
    if drift_result.drift_score >= AUTO_MERGE_MAX_DRIFT:
        logger.info("Auto-merge rejected: drift score %.1f exceeds max %.1f", drift_result.drift_score, AUTO_MERGE_MAX_DRIFT)
        return False

    conf = confidence_score if confidence_score is not None else 0.0
    if conf < AUTO_MERGE_MIN_CONFIDENCE:
        logger.info("Auto-merge rejected: confidence %.2f below min %.2f", conf, AUTO_MERGE_MIN_CONFIDENCE)
        return False

    if AUTO_MERGE_REQUIRE_CI_PASS:
        ci_passed = await _check_ci_status(repo, pr_number, github_token)
        if not ci_passed:
            logger.info("Auto-merge rejected: CI checks not passing")
            return False

    logger.info("Auto-merge approved for PR #%d", pr_number)
    return True


async def _check_ci_status(
    repo: str,
    pr_number: int,
    github_token: Optional[str],
) -> bool:
    """
    Return True if all required CI checks on the PR have passed.
    """
    if not github_token:
        return False
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {github_token}", 
            "Accept": "application/vnd.github.v3+json"
        }
        
        pr_resp = await client.get(f"https://api.github.com/repos/{repo}/pulls/{pr_number}", headers=headers)
        if pr_resp.status_code != 200: 
            return False
        sha = pr_resp.json()["head"]["sha"]

        checks_resp = await client.get(f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs", headers=headers)
        if checks_resp.status_code != 200: 
            return False
            
        runs = checks_resp.json().get("check_runs", [])
        if not runs:
            return False # Unsafe to merge without established CI checks
        return all(run.get("conclusion") == "success" for run in runs)


# ---------------------------------------------------------------------------
# Merge action
# ---------------------------------------------------------------------------

async def merge_pr(
    repo: str,
    pr_number: int,
    github_token: str,
    merge_method: str = "squash",   # "merge" | "squash" | "rebase"
    commit_title: Optional[str] = None,
) -> bool:
    """
    Merge a pull request via the GitHub API.
    """
    if not github_token: 
        return False
    owner, name = repo.split("/", 1)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.put(
            f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}/merge",
            json={
                "merge_method": merge_method,
                "commit_title": commit_title or f"docs: auto-merge fix #{pr_number}",
            },
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        if resp.status_code == 200:
            logger.info("Auto-merged PR #%d in %s", pr_number, repo)
            return True
        logger.warning("Auto-merge failed: %s", resp.text)
        return False
