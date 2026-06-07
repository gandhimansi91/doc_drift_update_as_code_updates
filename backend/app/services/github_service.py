"""
GitHub API integration — real pull request creation.

STATUS: ✅ BUILT
  Creates git blobs, constructs a tree, commits to a branch, and opens a pull request.
"""

from __future__ import annotations
import base64
import logging
from typing import Dict, Optional

import httpx

from app.core.config import settings
from app.models.schemas import PRRequest, PRResponse

logger = logging.getLogger(__name__)

_HEADERS_BASE = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _auth_headers(token: str) -> dict:
    return {**_HEADERS_BASE, "Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------

async def _push_file_changes_to_branch(
    owner: str,
    repo: str,
    base_branch: str,
    head_branch: str,
    file_changes: Dict[str, str],  # {path: new_content}
    commit_message: str,
    token: str,
) -> str:
    """
    Push file_changes to a new branch and return the new branch name.

    This function must:
      1. Resolve the SHA of base_branch HEAD
      2. Create blobs for every file in file_changes
      3. Build a new Git tree containing those blobs
      4. Create a commit on top of the base HEAD
      5. Create (or update) head_branch pointing at that commit
      6. Return head_branch on success

    Returns the head_branch name so github_create_pr() can use it.

    """
    api_base = f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}"
    async with httpx.AsyncClient(headers=_auth_headers(token), timeout=30.0) as client:
        # 1. Get the SHA of the base branch
        ref_resp = await client.get(f"{api_base}/git/ref/heads/{base_branch}")
        ref_resp.raise_for_status()
        base_sha = ref_resp.json()["object"]["sha"]

        # 2. Create blobs for the changed files
        tree_items = []
        for file_path, content in file_changes.items():
            encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            blob_resp = await client.post(
                f"{api_base}/git/blobs",
                json={"content": encoded_content, "encoding": "base64"}
            )
            blob_resp.raise_for_status()
            tree_items.append({
                "path": file_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_resp.json()["sha"]
            })

        # 3. Create a new tree on top of the base commit
        tree_resp = await client.post(
            f"{api_base}/git/trees",
            json={"base_tree": base_sha, "tree": tree_items}
        )
        tree_resp.raise_for_status()
        new_tree_sha = tree_resp.json()["sha"]

        # 4. Create a new commit
        commit_resp = await client.post(
            f"{api_base}/git/commits",
            json={"message": commit_message, "tree": new_tree_sha, "parents": [base_sha]}
        )
        commit_resp.raise_for_status()
        new_commit_sha = commit_resp.json()["sha"]

        # 5. Create a new branch reference
        ref_create_resp = await client.post(
            f"{api_base}/git/refs",
            json={"ref": f"refs/heads/{head_branch}", "sha": new_commit_sha}
        )
        
        # Fallback to updating the branch if it already happens to exist (HTTP 422)
        if ref_create_resp.status_code == 422:
            ref_update_resp = await client.patch(
                f"{api_base}/git/refs/heads/{head_branch}",
                json={"sha": new_commit_sha, "force": True}
            )
            ref_update_resp.raise_for_status()
        else:
            ref_create_resp.raise_for_status()

    return head_branch


# ---------------------------------------------------------------------------
# PR creation
# ---------------------------------------------------------------------------

async def github_create_pr(
    request: PRRequest,
    github_token: str,
) -> PRResponse:
    """
    Open a real GitHub pull request with the doc fixes.

    """
    if not github_token:
        raise ValueError("GitHub token is required for real PR creation")

    repo_parts = request.repo.split("/")
    if len(repo_parts) != 2:
        raise ValueError(f"Invalid repo format: {request.repo}. Expected 'owner/repo'")
    owner, repo_name = repo_parts

    await _push_file_changes_to_branch(
        owner=owner,
        repo=repo_name,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        file_changes=request.file_changes,
        commit_message=f"docs: {request.title}",
        token=github_token,
    )

    pr_payload = {
        "title": request.title,
        "body": request.body,
        "head": request.head_branch,
        "base": request.base_branch,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo_name}/pulls",
            json=pr_payload,
            headers=_auth_headers(github_token),
        )
        resp.raise_for_status()
        data = resp.json()

    return PRResponse(
        pr_number=data["number"],
        pr_url=data["html_url"],
        head_branch=data["head"]["ref"],
        status="open",
    )


async def choose_github_pr(request: PRRequest, github_token: Optional[str]) -> PRResponse:
    """Create a real GitHub PR if token is provided, otherwise raise an error."""
    if not github_token:
        raise ValueError("No GitHub token provided for PR creation")
    return await github_create_pr(request, github_token)
