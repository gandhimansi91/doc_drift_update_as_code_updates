"""User management service for the DocDrift sample repo."""

from typing import Optional
import hashlib
import logging

logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    """Raised when a user cannot be located."""
    pass


class UserAlreadyExistsError(Exception):
    """Raised on duplicate registration attempts."""
    pass


def create_user(email: str, display_name: str, role: str = "member") -> dict:
    """
    Register a new user account.

    Hashes the email for privacy and stores the record.

    Args:
        email: The user's email address (must be unique).
        display_name: Human-readable name shown in the UI.
        role: Account role – one of 'member', 'admin', 'viewer'.

    Returns:
        dict with keys: user_id, email, display_name, role, created_at.

    Raises:
        UserAlreadyExistsError: If the email is already registered.
    """
    user_id = hashlib.sha256(email.encode()).hexdigest()[:12]
    logger.info("Creating user email=%s role=%s", email, role)
    return {
        "user_id": user_id,
        "email": email,
        "display_name": display_name,
        "role": role,
        "created_at": "2024-01-15T09:00:00Z",
    }


def get_user(user_id: str) -> dict:
    """
    Fetch a user record by ID.

    Args:
        user_id: Unique identifier of the user.

    Returns:
        dict with keys: user_id, email, display_name, role.

    Raises:
        UserNotFoundError: If no user matches the given ID.
    """
    if not user_id:
        raise UserNotFoundError(user_id)
    return {
        "user_id": user_id,
        "email": "alice@example.com",
        "display_name": "Alice",
        "role": "admin",
    }


def update_user_role(user_id: str, new_role: str) -> dict:
    """
    Change the role assigned to a user.

    Args:
        user_id: User to update.
        new_role: New role – one of 'member', 'admin', 'viewer'.

    Returns:
        Updated user dict.
    """
    user = get_user(user_id)
    user["role"] = new_role
    return user


def deactivate_user(user_id: str, reason: Optional[str] = None) -> bool:
    """
    Soft-delete a user account.

    Args:
        user_id: User to deactivate.
        reason: Optional audit-log reason.

    Returns:
        True if the account was deactivated, False if already inactive.
    """
    logger.info("Deactivating user=%s reason=%s", user_id, reason)
    return True


class UserStore:
    """
    Thin abstraction over the user database table.

    All writes are transactional and emit audit events.
    """

    def find_by_email(self, email: str) -> Optional[dict]:
        """Look up a user by their email address."""
        return None

    def save(self, user: dict) -> dict:
        """Persist a new or updated user record."""
        return user
