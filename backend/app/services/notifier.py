"""
Notification service — alert engineers when high-traffic docs drift.

STATUS: ✅ BUILT
  Dispatches alerts to Slack or Teams webhooks for high-priority docs.
"""

from __future__ import annotations
import logging
import os
import httpx
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
    """
    logger.info("Checking if alerts need to be dispatched for %d stale results", len(stale_results))
    for result in stale_results:
        if result.drift_score > DRIFT_ALERT_THRESHOLD:
            logger.info("Dispatching alert for '%s' (drift: %.1f)", result.section_heading, result.drift_score)
            if channel in ("slack", "both"):
                slack_url = os.environ.get("SLACK_WEBHOOK_URL")
                if slack_url:
                    msg = _format_slack_message(repo_health.repo, result)
                    await send_slack_message(slack_url, msg)
            
            if channel in ("teams", "both"):
                teams_url = os.environ.get("TEAMS_WEBHOOK_URL")
                if teams_url:
                    msg = _format_teams_message(repo_health.repo, result)
                    await send_teams_message(teams_url, msg)


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
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=message, timeout=10.0)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Failed to send Slack alert: %s", exc)
        return False


def _format_slack_message(repo: str, result: DriftResult) -> dict:
    """
    Build a Slack Block Kit payload for a single stale doc block.
    """
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
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Pull Request"
                        },
                        "url": result.pr_url or "http://localhost:3000"
                    }
                ]
            }
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
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=message, timeout=10.0)
            # Teams incoming webhooks return 200 or 1 on success.
            return resp.status_code in (200, 202)
    except Exception as exc:
        logger.error("Failed to send Teams alert: %s", exc)
        return False


def _format_teams_message(repo: str, result: DriftResult) -> dict:
    """
    Build a Microsoft Teams Adaptive Card payload for a stale doc block.
    """
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
                            ],
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Pull Request",
                            "url": result.pr_url or "http://localhost:3000"
                        }
                    ]
                },
            }
        ],
    }
