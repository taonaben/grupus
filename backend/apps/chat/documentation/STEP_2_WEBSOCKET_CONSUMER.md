# Step 2: WebSocket Consumer & Modular Message Types - Complete ✓

## Overview
Successfully implemented a robust WebSocket consumer with support for multiple message types, JWT authentication, and room-based subscriptions. The system is designed to be extensible and efficient.

## What Was Implemented

### 1. **Enhanced Chat Models** (`backend/apps/chat/models.py`)

#### MessageType Enumeration
```python
MessageType = [TEXT, REMINDER, ALERT, NOTIFICATION, FILE, MENTION, REACTION]
```
Allows different message formats to be handled differently without schema changes.

#### Message Model Extensions
- **`message_type`**: CharField with MessageType choices
- **`metadata`**: JSONField for type-specific data (reminders, alerts, etc.)
- **`is_edited`**: Track if message was edited
- **`edited_at`**: Timestamp of last edit
- **Database Indexes**: On (channel, created_at), (sender, created_at), and message_type for performance

#### MessageReaction Model
- Stores emoji reactions to messages
- Unique constraint on (message, user, emoji) for idempotence
- Supports emoji aggregation queries

#### Factory Methods
```python
Message.create_text_message(sender, channel, content)
Message.create_reminder_message(sender, channel, content, reminder_data)
Message.create_alert_message(sender, channel, content, alert_level)
```
Makes it easy to create properly-typed messages.

### 2. **Polymorphic Serializers** (`backend/apps/chat/serializers.py`)

#### MessageSerializer
- Full serialization with related object data
- Includes reactions count
- Supports nested reaction data
- Read-only validation of message types

#### MessageWebSocketSerializer
- Lightweight for real-time transmission
- Includes only essential fields (id, type, content, sender, created_at)
- Optimized payload size for low-latency delivery

#### MessageReactionSerializer
- Serializes individual reactions with user info
- Read-only timestamps

#### BulkMessageSerializer
- For message history and batch operations
- Supports pagination

### 3. **WebSocket Consumer** (`backend/apps/chat/consumers.py`)

#### Connection Handling
- **JWT Authentication**: Validates tokens from query string or middleware
- **Channel Access Verification**: Ensures user has access to the room
- **Automatic Join**: Adds user to Channels group on connect
- **Presence Notification**: Broadcasts "user_joined" event

#### Message Handling
Supports multiple message types via JSON:
```json
{
  "type": "message",
  "message_type": "text|reminder|alert|notification",
  "content": "...",
  "metadata": {...}
}
```

Features:
- Content validation
- Message persistence to database
- Type-specific metadata storage
- Broadcasting to room group
- Automatic serialization

#### Real-Time Features
- **Typing Indicators**: Broadcasts when user is typing without database persistence
- **Message Reactions**: Handles emoji reactions with idempotence
- **User Presence**: Join/leave notifications
- **Error Handling**: Graceful error messages sent to client

#### Database Operations
All database operations run async-to-sync via `@database_sync_to_async` to prevent blocking:
- `_save_message()`: Persist messages
- `_save_reaction()`: Persist reactions
- `_get_user()`: Load user from token
- `_get_channel()`: Load channel and verify access

#### Broadcast Handlers
Consumer methods for handling group messages:
- `chat_message`: Broadcast saved messages
- `user_joined`: Notify of new participant
- `user_left`: Notify of participant leaving
- `user_typing`: Broadcast typing indicator
- `message_reaction`: Broadcast emoji reaction

### 4. **Message Handlers & Utilities** (`backend/apps/chat/message_handlers.py`)

#### Handler Classes
Each message type has a dedicated handler with validation and formatting:

**TextMessageHandler**
- Minimal metadata (none required)
- Factory: `TextMessageHandler.create(sender, channel, content)`

**ReminderMessageHandler**
- Requires: `due_date`, Optional: `assigned_to`, `priority`, `tags`
- Includes overdue detection: `ReminderMessageHandler.is_overdue(message)`
- Factory: `ReminderMessageHandler.create(..., due_date, priority, tags)`

**AlertMessageHandler**
- Levels: info, warning, critical
- CSS class mapping for frontend styling
- Optional: `action_url` for clickable alerts
- Factory: `AlertMessageHandler.create(..., alert_level, action_url)`

**NotificationMessageHandler**
- Flexible notification types (general, assignment, mention, etc.)
- Target user support
- Factory: `NotificationMessageHandler.create(..., notification_type, target_user_id)`

#### MessageHandlerFactory
```python
# Get appropriate handler
handler = MessageHandlerFactory.get_handler(MessageType.REMINDER)

# Validate metadata for type
is_valid = MessageHandlerFactory.validate_message(MessageType.REMINDER, metadata)

# Format message for display
formatted = MessageHandlerFactory.format_message(message)

# Register custom handlers
MessageHandlerFactory.register_handler("custom_type", CustomHandler)
```

#### MessageUtils
Utility functions for common operations:
- `get_message_by_id(message_id)`
- `get_channel_messages(channel_id, limit, offset, message_type)`
- `search_messages(channel_id, search_term, limit)`
- `get_reactions_for_message(message_id)`
- `delete_message(message_id, user_id)` - Only sender can delete
- `edit_message(message_id, user_id, new_content)` - With 5-minute edit limit

### 5. **WebSocket Routing** (`backend/apps/chat/routing.py`)

```python
websocket_urlpatterns = [
    path("ws/chat/<str:room_id>/", ChatConsumer.as_asgi()),
]
```

Maps WebSocket connections to ChatConsumer. Room ID should be a Channel UUID.

### 6. **Comprehensive Testing** (`backend/test_chat_websocket.py`)

**Test Suites** (12 tests, all passing ✓):
- **ChatModelTests**: Message creation, reactions, types
- **SerializerTests**: Full and lightweight serialization
- **MessageHandlerTests**: Factory, handlers, type-specific logic
- **RoutingTests**: WebSocket URL configuration
- **ConsumerTests**: Consumer methods available

## WebSocket Protocol

### Client → Server Messages

#### Text Message
```json
{
  "type": "message",
  "message_type": "text",
  "content": "Hello everyone!",
  "metadata": {}
}
```

#### Reminder
```json
{
  "type": "message",
  "message_type": "reminder",
  "content": "Complete project report",
  "metadata": {
    "due_date": "2026-02-15T10:00:00Z",
    "priority": "high",
    "tags": ["important", "deadline"]
  }
}
```

#### Alert
```json
{
  "type": "message",
  "message_type": "alert",
  "content": "System maintenance in 30 minutes",
  "metadata": {
    "alert_level": "warning"
  }
}
```

#### Typing Indicator
```json
{
  "type": "typing",
  "is_typing": true
}
```

#### Reaction
```json
{
  "type": "reaction",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "emoji": "👍"
}
```

### Server → Client Messages

#### Message Broadcast
```json
{
  "type": "message",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "content": "Hello!",
    "message_type": "text",
    "sender": {
      "id": "user-uuid",
      "username": "john_doe"
    },
    "channel_id": "channel-uuid",
    "created_at": "2026-02-01T12:00:00Z"
  }
}
```

#### User Joined
```json
{
  "type": "user_joined",
  "user_id": "user-uuid",
  "username": "john_doe",
  "timestamp": "2026-02-01T12:00:00Z"
}
```

#### Error
```json
{
  "type": "error",
  "message": "Invalid message format"
}
```

## Authentication Flow

1. **Client connects with token**:
   ```
   ws://localhost:8000/ws/chat/channel-uuid/?token=eyJhbGc...
   ```

2. **Consumer validates JWT**:
   - Extracts token from query string or middleware
   - Validates token signature and expiration
   - Loads User from token claims

3. **Consumer verifies channel access**:
   - Loads Channel object
   - Checks if public or user is owner/member

4. **Connection accepted** or closed with error code:
   - `4001`: Authentication failed
   - `4003`: Access denied

## Message Type Extension

Adding a new message type is simple:

1. Add to `MessageType` enum:
   ```python
   class MessageType(models.TextChoices):
       CUSTOM = "custom", "Custom Message Type"
   ```

2. Create handler:
   ```python
   class CustomMessageHandler(BaseMessageHandler):
       message_type = MessageType.CUSTOM
       
       @staticmethod
       def validate_metadata(metadata):
           return "required_field" in metadata
       
       @staticmethod
       def create(sender, channel, content, custom_field):
           return Message.objects.create(
               sender=sender,
               channel=channel,
               content=content,
               message_type=MessageType.CUSTOM,
               metadata={"custom_field": custom_field}
           )
   ```

3. Register handler:
   ```python
   MessageHandlerFactory.register_handler(
       MessageType.CUSTOM,
       CustomMessageHandler
   )
   ```

No database migration needed!

## Performance Optimizations

1. **Database Indexes**: On (channel, -created_at), (sender, -created_at), message_type
2. **Lightweight WebSocket Serializer**: Minimal payload for real-time messages
3. **Async Database Operations**: Non-blocking persistence via `@database_sync_to_async`
4. **Redis Channel Layer**: Broadcast across multiple processes
5. **Reaction Idempotence**: `get_or_create` prevents duplicate reactions
6. **Lazy Serialization**: Only serialize when broadcasting

## Security Features

1. **JWT Authentication**: Validates tokens on WebSocket connect
2. **Origin Validation**: `AllowedHostsOriginValidator` prevents CSRF
3. **Access Control**: Verifies user has channel access
4. **Data Validation**: Input validation on all message types
5. **Delete Protection**: Only message sender can delete
6. **Edit Time Limit**: 5-minute window for edits

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Client (WebSocket)                        │
└────────────────┬────────────────────────────────────────────┘
                 │ ws://localhost/ws/chat/<room_id>/
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  ChatConsumer                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ connect()                                              │ │
│  │  - JWT Token Validation                               │ │
│  │  - Channel Access Verification                        │ │
│  │  - Join Room Group                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ receive(text_data)                                     │ │
│  │  - Parse JSON message                                  │ │
│  │  - Route by type (message|typing|reaction)            │ │
│  │  - Validate & Process                                 │ │
│  │  - Save to DB (async)                                │ │
│  │  - Broadcast to Group                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Group Message Handlers                                 │ │
│  │  - chat_message (broadcast)                           │ │
│  │  - user_joined (presence)                             │ │
│  │  - user_typing (typing indicator)                     │ │
│  │  - message_reaction (emoji reactions)                 │ │
│  └────────────────────────────────────────────────────────┘ │
└────────┬─────────────────────────────────────┬────────────────┘
         │                                     │
         ▼                                     ▼
    ┌─────────────┐                   ┌───────────────┐
    │ PostgreSQL  │                   │ Redis Channels│
    │ (Persistence)                  │ (Broadcasting)│
    └─────────────┘                   └───────────────┘
```

## Usage Examples

### Sending a Message via WebSocket
```javascript
// Connect
const socket = new WebSocket('ws://localhost/ws/chat/channel-id/?token=JWT_TOKEN');

// Send text message
socket.send(JSON.stringify({
  type: 'message',
  message_type: 'text',
  content: 'Hello team!'
}));

// Send reminder
socket.send(JSON.stringify({
  type: 'message',
  message_type: 'reminder',
  content: 'Review quarterly report',
  metadata: {
    due_date: '2026-02-15T10:00:00Z',
    priority: 'high',
    tags: ['quarterly', 'review']
  }
}));

// Send alert
socket.send(JSON.stringify({
  type: 'message',
  message_type: 'alert',
  content: 'Server maintenance scheduled',
  metadata: {
    alert_level: 'warning'
  }
}));

// Send reaction
socket.send(JSON.stringify({
  type: 'reaction',
  message_id: '550e8400-e29b-41d4-a716-446655440000',
  emoji: '👍'
}));

// Typing indicator
socket.send(JSON.stringify({
  type: 'typing',
  is_typing: true
}));
```

### Receive Messages
```javascript
socket.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'message':
      console.log('New message:', data.data);
      break;
    case 'user_joined':
      console.log(`${data.username} joined`);
      break;
    case 'typing':
      if(data.is_typing) {
        console.log(`${data.username} is typing...`);
      }
      break;
    case 'reaction':
      console.log(`${data.username} reacted ${data.emoji}`);
      break;
    case 'error':
      console.error('Error:', data.message);
      break;
  }
};
```

## File Structure

```
backend/apps/chat/
├── __init__.py
├── admin.py
├── apps.py
├── models.py                    # Message, MessageReaction, MessageType
├── serializers.py               # MessageSerializer, WebSocketSerializer
├── consumers.py                 # ChatConsumer (WebSocket handler)
├── routing.py                   # WebSocket URL patterns
├── message_handlers.py          # Type-specific handlers & utilities
├── views.py                     # REST API endpoints (next step)
├── urls.py                      # REST API URL patterns (next step)
├── tests.py                     # Unit tests
├── migrations/
│   ├── 0001_initial.py
│   └── 0002_messagereaction_alter_message_options_and_more.py
└── __pycache__/
```

## Test Results

```
✓ ALL TESTS PASSED (12/12)

✓ Message Types
✓ Text Message Creation
✓ Reminder Message Creation
✓ Alert Message Creation
✓ Message Reactions
✓ Message Serializer
✓ WebSocket Serializer
✓ Handler Factory
✓ Reminder Handler
✓ Alert Handler
✓ WebSocket Routing
✓ WebSocket Consumer
```

## Current Status

### ✓ Completed
- Enhanced Message model with type support
- Message metadata for type-specific data
- Message reactions model
- Polymorphic serializers
- ChatConsumer with authentication
- Message handlers for text, reminder, alert, notification
- MessageHandlerFactory for extensibility
- WebSocket routing configured
- Comprehensive test suite (12/12 passing)
- Database migrations applied

### ⏭ Next Steps (Step 3 - REST API)
- Create REST endpoints for message history
- Implement message filtering and search
- Add bulk operations
- Create admin interface for moderation
- Add rate limiting and pagination

## Troubleshooting

### WebSocket Connection Refused
- Ensure Daphne is running (not Gunicorn)
- Verify JWT token is valid
- Check `REDIS_URL` environment variable

### Channel Access Denied
- Verify user is authenticated
- Check if channel is private
- Confirm user is member/owner

### Messages Not Persisting
- Verify database connection
- Check `CHANNEL_LAYERS` Redis configuration
- Ensure migrations applied

## Key Files Modified/Created

1. **Models**: [backend/apps/chat/models.py](backend/apps/chat/models.py) - Added MessageType, metadata, reactions
2. **Serializers**: [backend/apps/chat/serializers.py](backend/apps/chat/serializers.py) - Added polymorphic serializers
3. **Consumer**: [backend/apps/chat/consumers.py](backend/apps/chat/consumers.py) - New WebSocket handler (new file)
4. **Handlers**: [backend/apps/chat/message_handlers.py](backend/apps/chat/message_handlers.py) - Message type handlers (new file)
5. **Routing**: [backend/apps/chat/routing.py](backend/apps/chat/routing.py) - Updated with ChatConsumer
6. **Tests**: [backend/test_chat_websocket.py](backend/test_chat_websocket.py) - Comprehensive test suite (new file)
7. **Migrations**: [backend/apps/chat/migrations/0002_*](backend/apps/chat/migrations/) - Database schema updates (new file)

---

**Status**: ✅ Step 2 Complete and Tested (12/12 ✓)
**Next**: Ready for Step 3 - REST API Endpoints & Message Management
