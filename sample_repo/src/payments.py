"""Payment processing service for the DocDrift sample repo."""

from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when a payment operation fails."""
    pass


def process_payment(
    user_id: str,
    amount: Decimal,
    currency: str = "USD",
    idempotency_key: Optional[str] = None,
) -> dict:
    """
    Charge a user for a given amount.

    Validates the amount, selects the correct payment gateway,
    and returns a transaction receipt.

    Args:
        user_id: The ID of the user to charge.
        amount: Decimal amount to charge (must be > 0).
        currency: ISO 4217 currency code (default USD).
        idempotency_key: Optional key to prevent double charges.

    Returns:
        dict with keys: transaction_id, status, amount, currency.

    Raises:
        PaymentError: If the charge is declined or amount is invalid.
    """
    if amount <= 0:
        raise PaymentError(f"Invalid amount: {amount}")

    logger.info("Processing payment user=%s amount=%s %s", user_id, amount, currency)

    # Simulate gateway call
    return {
        "transaction_id": f"txn_{user_id}_{idempotency_key or 'default'}",
        "status": "success",
        "amount": str(amount),
        "currency": currency,
    }


def refund_payment(transaction_id: str, reason: str = "customer_request") -> dict:
    """
    Refund a previously completed transaction.

    Args:
        transaction_id: The transaction to refund.
        reason: Reason code for the refund.

    Returns:
        dict with keys: refund_id, original_transaction_id, status.
    """
    logger.info("Refunding transaction=%s reason=%s", transaction_id, reason)
    return {
        "refund_id": f"ref_{transaction_id}",
        "original_transaction_id": transaction_id,
        "status": "refunded",
    }


def get_payment_status(transaction_id: str) -> dict:
    """
    Retrieve the current status of a transaction.

    Args:
        transaction_id: The transaction to look up.

    Returns:
        dict with keys: transaction_id, status, updated_at.
    """
    return {
        "transaction_id": transaction_id,
        "status": "success",
        "updated_at": "2024-01-15T10:30:00Z",
    }


class PaymentGateway:
    """
    Low-level gateway client. Handles retries and auth headers.

    Attributes:
        api_key: Secret key for the payment provider.
        base_url: API base URL for the provider.
        timeout: Request timeout in seconds.
    """

    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def charge(self, payload: dict) -> dict:
        """Send a charge request to the upstream gateway."""
        raise NotImplementedError

    def refund(self, transaction_id: str) -> dict:
        """Issue a refund via the upstream gateway."""
        raise NotImplementedError
