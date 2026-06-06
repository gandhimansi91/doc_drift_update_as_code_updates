# API Reference

## Endpoints

### POST /payments/charge

Initiates a payment charge for a user.

**Request body:**
```json
{
  "user_id": "string",
  "amount": "decimal string",
  "currency": "USD",
  "idempotency_key": "optional string"
}
```

Internally calls `process_payment()`. Returns the transaction receipt on success.
Responds with HTTP 422 if `amount` is zero or negative.

---

### POST /payments/refund

Refunds a transaction. Requires `transaction_id` in the body.
Optional `reason` field for audit logging.

---

### GET /payments/{transaction_id}/status

Returns the current status of a transaction.
Response includes `transaction_id`, `status`, and `updated_at`.

---

## User Endpoints

### POST /users

Creates a new user account. Body requires `email`, `display_name`.
Optional `role` field (default: `member`).

Returns HTTP 409 if email is already registered.

---

### GET /users/{user_id}

Fetches a user record. Returns HTTP 404 if not found.

---

### PATCH /users/{user_id}/role

Updates the role of an existing user.
Body: `{ "role": "admin" | "member" | "viewer" }`

---

### DELETE /users/{user_id}

Permanently deletes a user account. This endpoint has no undo.

---

## Notification Endpoints

### POST /notifications/send

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

---

### POST /notifications/bulk

Sends the same message to multiple users.
Body: `{ "user_ids": [...], "message": "string", "channel": "string" }`

---

### GET /notifications/{notification_id}/status

Polls delivery status for a single notification.
