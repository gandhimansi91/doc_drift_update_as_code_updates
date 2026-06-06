"""
Mock implementations of all external API boundaries.
Each mock matches the real response schema exactly.
Toggle with USE_MOCKS=True in config.

Boundaries mocked:
  1. Git webhook + diff payload
  2. LLM doc rewrite
  3. PR creation (GitHub API)
  4. Dashboard read-count metrics
"""

from __future__ import annotations
import asyncio
import random
import textwrap
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from app.models.schemas import (
    CommitPayload,
    FileDiff,
    DriftResult,
    PRRequest,
    PRResponse,
)
from app.core.config import settings


# ============================================================
# 1. Git Webhook + Diff Mock
# ============================================================

# Pre-authored realistic diffs for our sample repo
_MOCK_DIFFS: List[Dict] = [
    {
        "path": "src/payments.py",
        "additions": 8,
        "deletions": 3,
        "patch": textwrap.dedent("""\
            @@ -18,7 +18,12 @@ def process_payment(
                 idempotency_key: Optional[str] = None,
             ) -> dict:
            -    Validates the amount, selects the correct payment gateway,
            -    and returns a transaction receipt.
            +    Validates the amount, applies regional tax rules,
            +    selects the correct payment gateway based on currency,
            +    and returns a PCI-compliant transaction receipt.
            +
            +    New: supports multi-currency routing via currency param.
             
                 Args:
                     user_id: The ID of the user to charge.
                     amount: Decimal amount to charge (must be > 0).
            -        currency: ISO 4217 currency code (default USD).
            +        currency: ISO 4217 currency code. Routing varies by region.
            +        tax_inclusive: If True, amount includes tax (default False).
        """),
    },
    {
        "path": "src/users.py",
        "additions": 5,
        "deletions": 2,
        "patch": textwrap.dedent("""\
            @@ -30,6 +30,9 @@ def deactivate_user(user_id: str, reason: Optional[str] = None) -> bool:
            -    Soft-delete a user account.
            +    Hard-delete a user account and purge PII from all tables.
            +    This action is irreversible and triggers a GDPR erasure event.
             
                 Args:
                     user_id: User to deactivate.
            -        reason: Optional audit-log reason.
            +        reason: Mandatory audit-log reason (now required for compliance).
            +        notify_user: If True, sends a deletion confirmation email (default True).
        """),
    },
    {
        "path": "src/notifications.py",
        "additions": 4,
        "deletions": 1,
        "patch": textwrap.dedent("""\
            @@ -22,5 +22,8 @@ def send_notification(
             ) -> dict:
            -    Sends a message to a single user. Supports email, sms, push, and webhook channels.
            +    Sends a message to a single user.
            +    Supported channels: email, sms, push, slack (webhook removed in v2).
            +    Rate limit: 100/min per user on normal priority, unlimited on high.
        """),
    },
]

_MOCK_COMMITS: List[Dict] = [
    {
        "sha": "a1b2c3d",
        "author": "alice@acme.com",
        "message": "feat: multi-currency payment routing + regional tax support",
        "branch": "main",
        "minutes_ago": 5,
        "files": [_MOCK_DIFFS[0]],
    },
    {
        "sha": "e4f5a6b",
        "author": "bob@acme.com",
        "message": "fix: harden deactivate_user – hard delete + GDPR erasure",
        "branch": "main",
        "minutes_ago": 45,
        "files": [_MOCK_DIFFS[1]],
    },
    {
        "sha": "c7d8e9f",
        "author": "carol@acme.com",
        "message": "refactor: drop webhook channel, add slack, enforce rate limits",
        "branch": "main",
        "minutes_ago": 120,
        "files": [_MOCK_DIFFS[2]],
    },
    {
        "sha": "f0a1b2c",
        "author": "alice@acme.com",
        "message": "feat: multi-currency payment routing + regional tax support",
        "branch": "feature/payment-v2",
        "minutes_ago": 200,
        "files": [_MOCK_DIFFS[0], _MOCK_DIFFS[1]],
    },
]


def get_mock_commit(index: int = 0) -> CommitPayload:
    """Return a pre-authored mock commit payload (index 0-3)."""
    c = _MOCK_COMMITS[index % len(_MOCK_COMMITS)]
    return CommitPayload(
        repo=settings.MOCK_GITHUB_REPO,
        commit_sha=c["sha"],
        branch=c["branch"],
        author=c["author"],
        message=c["message"],
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=c["minutes_ago"]),
        changed_files=[
            FileDiff(
                path=f["path"],
                patch=f["patch"],
                additions=f["additions"],
                deletions=f["deletions"],
            )
            for f in c["files"]
        ],
    )


def list_mock_commits() -> List[CommitPayload]:
    return [get_mock_commit(i) for i in range(len(_MOCK_COMMITS))]


# ============================================================
# 2. LLM Doc Rewrite Mock
# ============================================================

# Carefully hand-authored corrections that match the diff intent
_MOCK_REWRITES: Dict[str, str] = {
    "### process_payment": textwrap.dedent("""\
        Charges a user for a given amount, applying regional tax rules where applicable.
        Selects the correct payment gateway based on currency and region,
        and returns a PCI-compliant transaction receipt.

        **Parameters:**
        - `user_id` – The ID of the user to charge
        - `amount` – Decimal amount (must be positive)
        - `currency` – ISO 4217 code; routing varies by region (default: USD)
        - `tax_inclusive` – If `True`, the amount already includes tax (default: `False`)
        - `idempotency_key` – Optional key to prevent double charges

        **Returns:** A receipt dict with `transaction_id`, `status`, `amount`, `currency`.

        Errors are raised as `PaymentError` if the amount is invalid or the charge is declined.
    """),
    "### deactivate_user": textwrap.dedent("""\
        Hard-deletes a user account and purges all PII from associated tables.
        This action is **irreversible** and triggers a GDPR erasure event.

        **Parameters:**
        - `user_id` – User to delete
        - `reason` – Mandatory audit-log reason (required for compliance)
        - `notify_user` – If `True`, sends a deletion confirmation email (default: `True`)

        Returns `True` if the account was deleted successfully.
    """),
    "### DELETE /users/{user_id}": textwrap.dedent("""\
        Hard-deletes a user account and purges all PII. Triggers GDPR erasure.
        The `reason` query param is now **required**.
        Responds HTTP 204 on success; HTTP 400 if `reason` is missing.
    """),
    "### send_notification": textwrap.dedent("""\
        Sends a message to a single user on the specified channel.

        **Parameters:**
        - `user_id` – Recipient
        - `message` – Body text
        - `channel` – Delivery channel: `email`, `sms`, `push`, `slack`
          *(note: `webhook` channel was removed in v2)*
        - `subject` – Subject line (email only)
        - `priority` – `normal` (100/min rate limit) or `high` (unlimited)

        Returns a dict with `notification_id`, `status`, `channel`, `queued_at`.
    """),
    "### POST /notifications/send": textwrap.dedent("""\
        Sends a notification to a user.

        **Body:**
        ```json
        {
          "user_id": "string",
          "message": "string",
          "channel": "email | sms | push | slack",
          "subject": "optional string",
          "priority": "normal | high"
        }
        ```
        *Note: `webhook` channel removed in v2. Use `slack` instead.*
        Rate limit: 100/min per user at `normal` priority, unlimited at `high`.
    """),
}

_DEFAULT_REWRITE = textwrap.dedent("""\
    *(Auto-updated based on recent code changes)*

    This section has been revised to reflect the latest changes.
    Please review the diff and confirm accuracy before merging.
""")


async def mock_llm_rewrite(
    section_heading: str,
    original_content: str,
    diff_context: str,
) -> str:
    """
    Return a pre-authored mock rewrite for known sections,
    or a generic placeholder for unknown ones.
    Simulates LLM latency.
    """
    await asyncio.sleep(settings.MOCK_LLM_DELAY + random.uniform(0, 0.3))
    return _MOCK_REWRITES.get(section_heading, _DEFAULT_REWRITE)


# ============================================================
# 3. PR Creation Mock
# ============================================================

_pr_counter = 100


async def mock_create_pr(request: PRRequest) -> PRResponse:
    """Simulate opening a GitHub pull request."""
    global _pr_counter
    _pr_counter += 1
    await asyncio.sleep(0.2)
    return PRResponse(
        pr_number=_pr_counter,
        pr_url=f"local://docdrift/pr/{_pr_counter}",
        head_branch=request.head_branch,
        status="open",
    )


# ============================================================
# 4. Dashboard Read-Count Metrics Mock
# ============================================================

# Simulated page-view counts per section heading
MOCK_READ_COUNTS: Dict[str, int] = {
    "### process_payment": 1842,
    "### refund_payment": 934,
    "### PaymentGateway": 612,
    "### get_payment_status": 401,
    "### create_user": 1205,
    "### get_user": 889,
    "### deactivate_user": 2103,  # high because devs keep checking this
    "### update_user_role": 315,
    "### send_notification": 1556,
    "### send_bulk_notification": 728,
    "### NotificationTemplate": 492,
    "### POST /payments/charge": 1100,
    "### POST /payments/refund": 670,
    "### POST /users": 980,
    "### DELETE /users/{user_id}": 1890,
    "### POST /notifications/send": 1430,
    "### POST /notifications/bulk": 560,
}


def get_mock_read_counts() -> Dict[str, int]:
    """Return simulated page-view counts per section heading."""
    return MOCK_READ_COUNTS.copy()


# ============================================================
# STUB — candidates replace mock read counts with real analytics
# ============================================================

async def fetch_real_read_counts(repo: str, github_token: str) -> Dict[str, int]:
    """
    Fetch real page-view / traffic counts for documentation sections.

    Currently returns an empty dict — the pipeline falls back to zero read
    counts for all blocks, meaning the "most-read" prioritisation does not work.

    TODO — implement one of these approaches:

    Option A — GitHub Traffic API (counts views per file path):
        GET /repos/{owner}/{repo}/traffic/views
        Maps file-level view counts to section headings by doc_path prefix.
        Requires a token with the `repo` scope.
        Reference: https://docs.github.com/en/rest/metrics/traffic

    Option B — Custom analytics store (e.g. PostHog, Mixpanel, internal DB):
        Query your analytics store for page-view counts keyed by section heading.
        Return a dict matching the shape of MOCK_READ_COUNTS above.

    The returned dict must be keyed by section_heading strings
    (e.g. "### process_payment") and map to integer view counts.

    After implementing, update analysis_worker.py to call fetch_real_read_counts()
    instead of get_mock_read_counts() when a github_token is available.
    """
    # ── TODO: replace the return below with a real analytics fetch ──
    return {}  # TODO: fetch real read counts from GitHub Traffic API or analytics store
