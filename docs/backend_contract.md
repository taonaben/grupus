# Chat Backend Contract

This document records the current chat message API shape and the additions
needed before the frontend sync engine can safely support offline-first chat.

## Existing Contract

The backend already exposes message CRUD under `/chat/messages/`.

### Endpoints

```http
GET /chat/messages/?channel_id={channelId}
POST /chat/messages/?channel_id={channelId}
GET /chat/messages/{id}/
PUT /chat/messages/{id}/
PATCH /chat/messages/{id}/
DELETE /chat/messages/{id}/
```

`channel_id` currently stays as a query parameter for list and create.

### Existing Message Fields

```text
id
content
message_type
message_type_display
sender_id
sender_username
channel_id
channel_name
metadata
reactions
is_edited
edited_at
created_at
updated_at
```

### Existing Message Types

```text
text
reminder
alert
notification
file
mention
reaction
```

## Required Sync Additions

The current CRUD contract is useful, but it is not enough for safe offline
sync. The backend should add the fields and guarantees below.

### Sync Identity

```text
client_message_id
client_mutation_id
```

`client_message_id` identifies a client-created message and makes create
retries idempotent.

`client_mutation_id` identifies any queued create, edit, or delete mutation.
The server should use it to make retries safe.

The client will also persist an `installation_id` locally. It does not need to
become a primary backend model, but it should be allowed in mutation metadata
for debugging and traceability.

### Ordering And Versioning

```text
server_sequence
version
deleted_at
```

`server_sequence` is a monotonically increasing number per channel. It is the
canonical chat order for confirmed messages.

`version` increments on edits and deletes. Clients send their last known version
with edit/delete requests so the backend can reject stale mutations.

`deleted_at` is required if deletes are soft-deletes and must sync to offline or
secondary devices.

### Backfill And Pagination

```http
GET /chat/messages/?channel_id={channelId}&since_sequence={serverSequence}
GET /chat/messages/?channel_id={channelId}&before_sequence={serverSequence}&limit={limit}
```

`since_sequence` returns messages and delete/update events missed while the
client was offline or disconnected.

`before_sequence` supports older history pagination when the user scrolls up.

## Required Create Behavior

Message create should be idempotent.

Example request:

```json
{
  "client_message_id": "installation-id:message-uuid",
  "client_mutation_id": "mutation-uuid",
  "content": "Hello",
  "message_type": "text",
  "metadata": {
    "client_message_id": "installation-id:message-uuid"
  }
}
```

Server behavior:

- If `client_message_id` is new, create and return the saved message.
- If `client_message_id` was already processed, return the existing message.
- A retry must never create a duplicate message.

## Required Edit And Delete Behavior

Edit/delete requests should include the last known `version`.

Example edit request:

```json
{
  "client_mutation_id": "mutation-uuid",
  "version": 3,
  "content": "Updated message"
}
```

Required responses:

```text
200: mutation applied; return the updated message
403: permission lost; non-retryable
409: stale version conflict; non-retryable until user/server conflict is resolved
410: target is deleted or gone; non-retryable
422: validation failure; non-retryable
5xx: retryable
network failure: retryable
```

## Required WebSocket Events

WebSocket should broadcast server-confirmed events only. It should not be the
durable write path for offline queued messages.

Required event types:

```text
message.created
message.updated
message.deleted
```

Each event should include enough data for the client to upsert into Drift
without an immediate follow-up REST call.

Minimum event payload fields:

```text
id
channel_id
client_message_id
content
message_type
metadata
sender_id
sender_username
server_sequence
version
deleted_at
created_at
updated_at
```

`client_message_id` may be null for messages created by older clients or
server-side/system events.

## Metadata Format

`metadata` should be structured JSON, not an opaque display string. If the
backend must store it as a string internally, the API should still document that
the value is encoded JSON and preserve object structure on read/write.

The sync engine needs structured metadata so fields like `client_message_id`,
reminder settings, alert metadata, and future attachment details can be read
without fragile string parsing.

