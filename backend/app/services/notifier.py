"""
Notification service — alert engineers when high-traffic docs drift.

STATUS: 🔶 STUB
  All functions raise NotImplementedError. No notifications are sent.

TODO:
  Implement at least one channel (Slack or Teams) so that when a doc block
  with read_count > READ_COUNT_ALERT_THRESHOLD drifts above DRIFT_ALERT_THRESHOLD,
  a message is posted automatically after the analysis job completes.

  Wire notify_drift_detected() into analysis_worker.py after step 6 (LLM rewrites).
"""

from __future__ import annotations
import logging
from typing import List, Optional

from app.models.schemas import DriftResult, RepoHealth

logger = logging.getLogger(__name__)

# Thresholds — tune these in production
DRIFT_ALERT_THRESHOLD = 60       # drift_score above which we alert
READ_COUNT_ALERT_THRESHOLD = 500  # only alert for high-traffic doc sections


# ---------------------------------------------------------------------------
# Main entrypoint — called by analysis_worker after rewrites are ready
# ---------------------------------------------------------------------------

async def notify_drift_detected(
    repo_health: RepoHealth,
    stale_results: List[DriftResult],
    channel: str = "slack",  # "slack" | "teams" | "both"
) -> None:
    """
    Send a notification for every high-traffic stale doc block.

    Filters stale_results to blocks where:
      - drift_score   > DRIFT_ALERT_THRESHOLD
      - read_count    > READ_COUNT_ALERT_THRESHOLD  (requires real read-count data)

    Then routes to the appropriate channel implementation.

    TODO:
      1. Filter results using the thresholds above
      2. Build a human-readable message (see _format_slack_message below)
      3. Call send_slack_message() or send_teams_message() based on channel param
      4. Log successes and failures — never let a notification error crash the pipeline
    """
    # ── TODO: implement notification routing ──
    raise NotImplementedError(
        "notify_drift_detected() is not implemented. "
        "See the docstring and the send_*_message stubs below."
    )


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

async def send_slack_message(webhook_url: str, message: dict) -> bool:
    """
    POST a Block Kit message payload to a Slack incoming webhook URL.

    Args:
        webhook_url: Slack incoming webhook URL from environment / config.
        message: Slack Block Kit payload dict (see _format_slack_message).

    Returns True on success, False on failure.

    TODO:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=message, timeout=10.0)
            return resp.status_code == 200

    Reference: https://api.slack.com/messaging/webhooks
    """
    # ── TODO: implement Slack HTTP POST ──
    raise NotImplementedError(
        "send_slack_message() is not implemented. "
        "POST the message dict to the Slack incoming webhook URL."
    )


def _format_slack_message(repo: str, result: DriftResult) -> dict:
    """
    Build a Slack Block Kit payload for a single stale doc block.

    TODO: customise the blocks list to match your team's style.
    The structure below is a valid starting point — fill in the values.

    Reference: https://app.slack.com/block-kit-builder
    """
    # ── TODO: customise the Slack message format ──
    return {
        "text": f"DocDrift alert: stale docs in {repo}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":warning: Doc drift detected in {repo}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Section:*\n{result.section_heading}"},
                    {"type": "mrkdwn", "text": f"*Drift score:*\n{result.drift_score:.0f} / 100"},
                    {"type": "mrkdwn", "text": f"*File:*\n`{result.doc_path}`"},
                    # TODO: add read_count field once real analytics are wired
                ],
            },
            # TODO: add an "actions" block with "View PR" button
        ],
    }


# ---------------------------------------------------------------------------
# Microsoft Teams
# ---------------------------------------------------------------------------

async def send_teams_message(webhook_url: str, message: dict) -> bool:
    """
    POST an Adaptive Card payload to a Microsoft Teams incoming webhook.

    Args:
        webhook_url: Teams channel webhook URL from environment / config.
        message: Teams Adaptive Card payload dict (see _format_teams_message).

    Returns True on success, False on failure.

    TODO:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=message, timeout=10.0)
            return resp.status_code == 200  # Teams returns 1 on success (not 200)

    Reference: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
    """
    # ── TODO: implement Teams HTTP POST ──
    raise NotImplementedError(
        "send_teams_message() is not implemented. "
        "POST the message dict to the Teams incoming webhook URL."
    )


def _format_teams_message(repo: str, result: DriftResult) -> dict:
    """
    Build a Microsoft Teams Adaptive Card payload for a stale doc block.

    TODO: fill in the body items with real values.
    Reference: https://adaptivecards.io/designer/
    """
    # ── TODO: customise the Teams message format ──
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Doc drift detected in {repo}",
                            "weight": "bolder",
                            "size": "medium",
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Section", "value": result.section_heading},
                                {"title": "Drift score", "value": f"{result.drift_score:.0f}/100"},
                                # TODO: add more facts
                            ],
                        },
                    ],
                    # TODO: add actions block with "View PR" button
                },
            }
        ],
    }
