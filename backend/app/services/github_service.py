"""
GitHub API integration — real pull request creation.

STATUS: 🔶 PARTIAL
  - github_create_pr() calls the GitHub API to open a PR but the head branch
    must already exist with the doc changes committed to it.
  - _push_file_changes_to_branch() is a STUB. Must be implemented.
    Without it, the PR will be rejected by GitHub (422) because the branch
    does not exist or does not contain the new file content.

TODO — implement _push_file_changes_to_branch():
  The full flow to open a real doc-fix PR is:
    1. GET  /repos/{owner}/{repo}/git/ref/heads/{base_branch}
           → get the current HEAD SHA of the base branch
    2. GET  /repos/{owner}/{repo}/git/commits/{head_sha}
           → get the tree SHA of that commit
    3. For each file in file_changes:
       POST /repos/{owner}/{repo}/git/blobs
            body: { "content": <base64 content>, "encoding": "base64" }
           → get blob SHA for each file
    4. POST /repos/{owner}/{repo}/git/trees
            body: { "base_tree": <tree_sha>, "tree": [{path, mode, type, sha}...] }
           → get new tree SHA
    5. POST /repos/{owner}/{repo}/git/commits
            body: { "message": ..., "tree": <new_tree_sha>, "parents": [<head_sha>] }
           → get new commit SHA
    6. POST /repos/{owner}/{repo}/git/refs
            body: { "ref": "refs/heads/{head_branch}", "sha": <new_commit_sha> }
           → creates the new branch pointing at the commit
    7. Then call github_create_pr() which already handles the PR creation.

  Reference: https://docs.github.com/en/rest/git
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
# STUB — implement this
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
    """
    if not token:
        raise ValueError("GitHub token is required to push changes to a branch")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Resolve the base branch commit SHA
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        base_ref = resp.json()
        base_sha = base_ref["object"]["sha"]

        # 2. Get the tree SHA for the base commit
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/commits/{base_sha}",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        base_commit = resp.json()
        base_tree = base_commit["tree"]["sha"]

        # 3. Create blobs for the updated files
        tree: list[dict] = []
        for path, content in file_changes.items():
            encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            blob_resp = await client.post(
                f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/blobs",
                headers=_auth_headers(token),
                json={"content": encoded, "encoding": "base64"},
            )
            blob_resp.raise_for_status()
            blob_sha = blob_resp.json()["sha"]
            tree.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            })

        # 4. Create a new tree containing the updated blobs
        tree_resp = await client.post(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees",
            headers=_auth_headers(token),
            json={"base_tree": base_tree, "tree": tree},
        )
        tree_resp.raise_for_status()
        new_tree_sha = tree_resp.json()["sha"]

        # 5. Create a new commit on top of the base commit
        commit_resp = await client.post(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/commits",
            headers=_auth_headers(token),
            json={
                "message": commit_message,
                "tree": new_tree_sha,
                "parents": [base_sha],
            },
        )
        commit_resp.raise_for_status()
        new_commit_sha = commit_resp.json()["sha"]

        # 6. Create or update the branch reference
        ref_payload = {"ref": f"refs/heads/{head_branch}", "sha": new_commit_sha}
        create_ref_resp = await client.post(
            f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs",
            headers=_auth_headers(token),
            json=ref_payload,
        )
        if create_ref_resp.status_code == 422:
            # Branch already exists: update it instead of creating it.
            update_resp = await client.patch(
                f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs/heads/{head_branch}",
                headers=_auth_headers(token),
                json={"sha": new_commit_sha, "force": True},
            )
            update_resp.raise_for_status()
        else:
            create_ref_resp.raise_for_status()

    return head_branch


# ---------------------------------------------------------------------------
# PR creation — calls _push_file_changes_to_branch first (once implemented)
# ---------------------------------------------------------------------------

async def github_create_pr(
    request: PRRequest,
    github_token: str,
) -> PRResponse:
    """
    Open a real GitHub pull request with the doc fixes.

    Requires _push_file_changes_to_branch() to be implemented first —
    the PR will fail with HTTP 422 if the head branch does not exist.
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
