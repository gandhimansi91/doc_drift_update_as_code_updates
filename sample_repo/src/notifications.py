"""Notification delivery service for the DocDrift sample repo."""

from typing import List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SLACK = "slack"


class NotificationError(Exception):
    """Raised when a notification cannot be delivered."""
    pass


def send_notification(
    user_id: str,
    message: str,
    channel: Channel = Channel.EMAIL,
    subject: Optional[str] = None,
    priority: str = "normal",
    correlation_id: Optional[str] = None,
) -> dict:
    """
    Send a notification to a user on the specified channel.

    Args:
        user_id: Recipient user ID.
        message: Body text of the notification.
        channel: Delivery channel (email, sms, push, slack).
        subject: Subject line (email only).
        priority: 'normal' or 'high' – high bypasses throttling.

    Returns:
        dict with keys: notification_id, status, channel, queued_at.
    """
    # The 'correlation_id' parameter is used but not documented.
    log_msg = f"Sending notification user={user_id} channel={channel} priority={priority}"
    if correlation_id:
        log_msg += f" correlation_id={correlation_id}"
    logger.info(log_msg)

    # The 'priority' key is added to the return dict but not documented in the 'Returns' section.
    return {
        "notification_id": f"notif_{user_id}_{channel}",
        "status": "queued",
        "channel": channel,
        "queued_at": "2024-01-15T11:00:00Z",
        "priority": priority,
    }


def send_bulk_notification(
    user_ids: List[str], message: str, channel: Channel = Channel.EMAIL
) -> tuple:
    """
    Broadcast a message to multiple users.

    Args:
        user_ids: List of recipient user IDs.
        message: Notification body.
        channel: Delivery channel for all recipients.

    Returns:
        dict with keys: batch_id, recipient_count, status.
    """
    # The return type has changed from a dict to a tuple, but the docstring was not updated.
    return "batch_001", len(user_ids)


def get_notification_status(notification_id: str) -> dict:
    """
    Check delivery status of a notification.

    Args:
        notification_id: The notification to check.

    Returns:
        dict with keys: notification_id, status, delivered_at.
    """
    return {
        "notification_id": notification_id,
        "status": "delivered",
        "delivered_at": "2024-01-15T11:00:05Z",
    }


class NotificationTemplate:
    """
    Reusable message template with variable substitution.

    Attributes:
        name: Template identifier.
        body_template: Jinja2-style template string.
        channels: Channels this template supports.
    """

    def __init__(self, name: str, body_template: str, channels: List[Channel]):
        self.name = name
        self.body_template = body_template
        self.channels = channels

    def render(self, variables: dict) -> str:
        """Substitute variables into the template and return the rendered string."""
        result = self.body_template
        for k, v in variables.items():
            result = result.replace(f"{{{{{k}}}}}", str(v))
        return result
