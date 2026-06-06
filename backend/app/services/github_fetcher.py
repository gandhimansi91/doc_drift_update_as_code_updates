"""
Fetch commits, diffs, and markdown docs from the GitHub REST API.
Used when a real GitHub token is provided instead of mock data.
"""

from __future__ import annotations
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from app.core.config import settings
from app.models.schemas import CommitPayload, FileDiff

logger = logging.getLogger(__name__)

_HEADERS_BASE = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _auth_headers(token: str) -> dict:
    return {**_HEADERS_BASE, "Authorization": f"Bearer {token}"}


async def fetch_repo_commits(repo: str, token: str, limit: int = 5) -> List[dict]:
    """
    Return recent commits from a GitHub repo as plain dicts suitable for the UI.
    Each dict has: sha, full_sha, author, message, branch, files (empty list at this stage).
    """
    owner, name = repo.split("/", 1)
    url = f"{settings.GITHUB_API_BASE}/repos/{owner}/{name}/commits"
    params = {"per_page": min(limit, 10)}

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, headers=_auth_headers(token), params=params)

        # Fine-grained PATs without explicit repo access return 404 even for public repos.
        # Fall back to unauthenticated so public repos always work.
        if resp.status_code == 404 and token:
            logger.info("Authenticated request returned 404 for %s; retrying unauthenticated", repo)
            resp = await client.get(url, headers=_HEADERS_BASE, params=params)

        resp.raise_for_status()
        raw_commits = resp.json()

    result = []
    for c in raw_commits:
        commit_info = c.get("commit", {})
        author_info = commit_info.get("author", {}) or {}
        github_author = c.get("author") or {}
        author = author_info.get("email") or github_author.get("login") or "unknown"
        result.append({
            "sha": c["sha"][:7],
            "full_sha": c["sha"],
            "author": author,
            "message": commit_info.get("message", "").split("\n")[0],
            "branch": "main",
            "files": [],
        })
    return result


async def build_commit_payload(repo: str, sha: str, token: str) -> CommitPayload:
    """
    Fetch a single commit's full diff and return a CommitPayload the analysis
    worker can consume directly.
    """
    owner, name = repo.split("/", 1)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{name}/commits/{sha}",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        data = resp.json()

    commit_info = data.get("commit", {})
    author_info = commit_info.get("author", {}) or {}
    github_author = data.get("author") or {}
    author = author_info.get("email") or github_author.get("login") or "unknown"

    raw_date = author_info.get("date", "")
    try:
        ts = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        ts = datetime.now(timezone.utc)

    changed_files: List[FileDiff] = []
    for f in data.get("files", []):
        patch = f.get("patch", "")
        if not patch:
            continue
        # Only include text files with diffs; skip very large patches
        if len(patch) > 50_000:
            patch = patch[:50_000]
        changed_files.append(FileDiff(
            path=f["filename"],
            patch=patch,
            additions=f.get("additions", 0),
            deletions=f.get("deletions", 0),
        ))

    return CommitPayload(
        repo=repo,
        commit_sha=sha[:7],
        branch="main",
        author=author,
        message=commit_info.get("message", "").split("\n")[0],
        timestamp=ts,
        changed_files=changed_files,
    )


# Directories that are unlikely to contain user-facing documentation.
# Filtering these prevents sample/test fixtures from polluting the analysis.
_EXCLUDED_DIR_PREFIXES = (
    "sample_", "samples/", "test/", "tests/", "test_",
    "vendor/", "node_modules/", ".github/", "fixtures/",
    "fixture_", "__pycache__/", ".venv/", "venv/", "dist/",
    "build/", "coverage/", "e2e/", "spec/", "mock/", "mocks/",
)


def _is_doc_path(path: str) -> bool:
    """Return True if the path looks like user-facing documentation."""
    low = path.lower()
    if not low.endswith(".md"):
        return False
    # Exclude paths whose first segment looks like a sample/test directory
    for prefix in _EXCLUDED_DIR_PREFIXES:
        if low.startswith(prefix) or ("/" + prefix) in low:
            return False
    return True


async def fetch_markdown_files(repo: str, ref: str, token: str) -> Dict[str, str]:
    """
    Fetch Markdown files from a GitHub repo at the given ref (SHA or branch).
    Skips sample, test, vendor, and fixture directories.
    Returns {path: content} for up to 30 matching files.
    """
    owner, name = repo.split("/", 1)
    docs: Dict[str, str] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get the recursive tree
        tree_resp = await client.get(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{name}/git/trees/{ref}",
            headers=_auth_headers(token),
            params={"recursive": "1"},
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json()

        md_blobs = [
            item for item in tree.get("tree", [])
            if item["type"] == "blob" and _is_doc_path(item["path"])
        ][:30]

        logger.info("Fetching %d markdown files from %s@%s", len(md_blobs), repo, ref[:7])

        for item in md_blobs:
            try:
                blob_resp = await client.get(
                    f"{settings.GITHUB_API_BASE}/repos/{owner}/{name}/git/blobs/{item['sha']}",
                    headers=_auth_headers(token),
                )
                blob_resp.raise_for_status()
                blob_data = blob_resp.json()
                raw = blob_data.get("content", "").replace("\n", "")
                content = base64.b64decode(raw).decode("utf-8", errors="replace")
                docs[item["path"]] = content
            except Exception as exc:
                logger.warning("Could not fetch %s: %s", item["path"], exc)

    return docs


# ---------------------------------------------------------------------------
# STUB — candidates add GitLab support
# ---------------------------------------------------------------------------

async def fetch_gitlab_commits(
    repo: str,          # "namespace/project" e.g. "myorg/myrepo"
    token: str,         # GitLab personal access token
    gitlab_base: str = "https://gitlab.com/api/v4",
    limit: int = 5,
) -> List[dict]:
    """
    Fetch recent commits from a GitLab project.

    Should return the same dict shape as fetch_repo_commits():
        [{ "sha", "full_sha", "author", "message", "branch", "files" }, ...]

    TODO:
        GET {gitlab_base}/projects/{encoded_repo}/repository/commits
        Headers: { "PRIVATE-TOKEN": token }
        Map GitLab response fields:
          - id          → full_sha / sha[:7]
          - author_email → author
          - title       → message
        Reference: https://docs.gitlab.com/ee/api/commits.html
    """
    # ── TODO: implement GitLab commit fetching ──
    raise NotImplementedError(
        "fetch_gitlab_commits() is not implemented. "
        "See the docstring for the GitLab API endpoint and field mapping."
    )


async def build_commit_payload_gitlab(
    repo: str,
    sha: str,
    token: str,
    gitlab_base: str = "https://gitlab.com/api/v4",
) -> "CommitPayload":
    """
    Fetch a single commit's diff from GitLab and return a CommitPayload.

    TODO:
        GET {gitlab_base}/projects/{encoded_repo}/repository/commits/{sha}/diff
        Then assemble a CommitPayload using the same structure as
        build_commit_payload() above.
        Reference: https://docs.gitlab.com/ee/api/commits.html#get-the-diff-of-a-commit
    """
    # ── TODO: implement GitLab diff fetching ──
    raise NotImplementedError(
        "build_commit_payload_gitlab() is not implemented. "
        "See the docstring for the GitLab diff API."
    )


# ---------------------------------------------------------------------------
# STUB — candidates add Azure DevOps support
# ---------------------------------------------------------------------------

async def fetch_azuredevops_commits(
    organization: str,   # e.g. "myorg"
    project: str,        # e.g. "myproject"
    repo: str,           # e.g. "myrepo"
    token: str,          # Azure DevOps personal access token
    limit: int = 5,
) -> List[dict]:
    """
    Fetch recent commits from an Azure DevOps Git repository.

    Should return the same dict shape as fetch_repo_commits():
        [{ "sha", "full_sha", "author", "message", "branch", "files" }, ...]

    TODO:
        GET https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/commits
        Headers: { "Authorization": "Basic " + base64(":token") }
        Query params: { "api-version": "7.1", "$top": limit }
        Map Azure fields:
          - commitId   → full_sha / sha[:7]
          - author.email → author
          - comment    → message
        Reference: https://learn.microsoft.com/en-us/rest/api/azure/devops/git/commits/get-commits
    """
    # ── TODO: implement Azure DevOps commit fetching ──
    raise NotImplementedError(
        "fetch_azuredevops_commits() is not implemented. "
        "See the docstring for the Azure DevOps REST API endpoint and field mapping."
    )
