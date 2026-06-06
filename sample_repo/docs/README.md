# Sample App Documentation

## Payment Processing

The payment service handles all monetary transactions in the platform.

### process_payment

Charges a user for a specified amount. The function validates the amount,
selects the correct payment gateway, and returns a transaction receipt.

**Parameters:**
- `user_id` – The ID of the user to charge
- `amount` – Decimal amount (must be positive)
- `currency` – ISO 4217 code (default: USD)

**Returns:** A receipt dict with `transaction_id`, `status`, `amount`, `currency`.

Errors are raised as `PaymentError` if the amount is invalid or the charge is declined.

---

### refund_payment

Issues a refund on a completed transaction. Pass the original `transaction_id`
and an optional `reason` string.

Returns a dict with `refund_id`, `original_transaction_id`, and `status`.

---

### PaymentGateway

Low-level client that communicates with the upstream payment provider.
Constructed with an `api_key`, `base_url`, and optional `timeout` (seconds).

Use `charge(payload)` to initiate a charge and `refund(transaction_id)` for refunds.

---

## User Management

The user service manages account registration, lookup, and role assignment.

### create_user

Registers a new user account. The email must be unique across the system.

**Parameters:**
- `email` – User's email (unique identifier)
- `display_name` – Name shown in the UI
- `role` – One of `member`, `admin`, or `viewer` (default: `member`)

Raises `UserAlreadyExistsError` if the email is already taken.

---

### get_user

Fetches a user record by `user_id`. Raises `UserNotFoundError` if not found.

---

### deactivate_user

Permanently removes a user from the system. This action is **irreversible**.

---

## Notifications

The notification service delivers messages across multiple channels.

### send_notification

Sends a message to a single user. Supports `email`, `sms`, `push`, and `webhook` channels.

**Parameters:**
- `user_id` – Recipient
- `message` – Body text
- `channel` – Delivery channel (default: `email`)
- `subject` – Email subject (email channel only)

High-priority notifications skip the throttling queue.

---

### send_bulk_notification

Broadcasts to a list of user IDs. All recipients receive the same message
on the same channel.

---

### NotificationTemplate

A reusable template supporting Mustache-style `{{variable}}` substitution.
Construct with a `name`, `body_template`, and list of supported `channels`.
Call `render(variables)` to produce the final string.
