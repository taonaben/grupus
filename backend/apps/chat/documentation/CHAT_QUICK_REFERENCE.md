# Chat System - Developer Quick Reference

## Quick Links

- [Full Overview](./CHAT_SYSTEM_OVERVIEW.md)
- [Step 1: Channels Setup](./STEP_1_CHANNELS_SETUP.md)
- [Step 2: WebSocket Consumer](./STEP_2_WEBSOCKET_CONSUMER.md)

---

## File Locations

```
backend/
├── apps/chat/
│   ├── models.py                # Message, MessageReaction, MessageType
│   ├── serializers.py           # MessageSerializer, WebSocketSerializer
│   ├── consumers.py             # ChatConsumer
│   ├── message_handlers.py      # Type-specific handlers
│   ├── routing.py               # WebSocket URLs
│   ├── views.py                 # REST endpoints (next)
│   ├── urls.py                  # REST URLs (next)
│   ├── migrations/0002_*.py     # Database schema
│   └── tests.py
├── main/
│   ├── asgi.py                  # ASGI with Channels
│   ├── settings.py              # CHANNEL_LAYERS config
│   └── wsgi.py
├── Dockerfile
├── entrypoint.sh
├── check_channels.py            # Validation script
└── test_chat_websocket.py       # Tests (12/12 pass)
```

---

## Common Tasks

### Create a Text Message Programmatically
```python
from apps.chat.models import Message
from apps.user.models import User
from apps.channel.models import Channel

user = User.objects.get(username='john_doe')
channel = Channel.objects.get(name='general')

message = Message.create_text_message(
    sender=user,
    channel=channel,
    content='Hello everyone!'
)
```

### Create a Reminder Message
```python
from apps.chat.models import Message
from datetime import datetime, timedelta

due_date = (datetime.now() + timedelta(days=1)).isoformat()

message = Message.create_reminder_message(
    sender=user,
    channel=channel,
    content='Complete quarterly review',
    reminder_data={
        'due_date': due_date,
        'priority': 'high',
        'tags': ['review', 'quarterly']
    }
)
```

### Create an Alert Message
```python
message = Message.create_alert_message(
    sender=user,
    channel=channel,
    content='System maintenance in 1 hour',
    alert_level='warning'
)
```

### Get Recent Messages from Channel
```python
from apps.chat.message_handlers import MessageUtils

messages = MessageUtils.get_channel_messages(
    channel_id='channel-uuid',
    limit=50,
    offset=0
)
```

### Search Messages
```python
results = MessageUtils.search_messages(
    channel_id='channel-uuid',
    search_term='project',
    limit=20
)
```

### Check if Reminder is Overdue
```python
from apps.chat.message_handlers import ReminderMessageHandler

message = Message.objects.get(id='message-uuid')
is_overdue = ReminderMessageHandler.is_overdue(message)
```

### Get Reaction Counts for Message
```python
reactions = MessageUtils.get_reactions_for_message('message-uuid')
# Returns: {'👍': 5, '❤️': 3, '😂': 2}
```

### Format Message for Display
```python
from apps.chat.message_handlers import MessageHandlerFactory

formatted = MessageHandlerFactory.format_message(message)
# Returns formatted dict based on message type
```

---

## WebSocket Examples

### JavaScript Client

```javascript
// Connect
const token = localStorage.getItem('auth_token');
const channelId = 'channel-uuid';
const socket = new WebSocket(
  `ws://localhost:8000/ws/chat/${channelId}/?token=${token}`
);

// Handle connection
socket.onopen = () => {
  console.log('Connected to chat');
};

// Send text message
function sendMessage(content) {
  socket.send(JSON.stringify({
    type: 'message',
    message_type: 'text',
    content: content
  }));
}

// Send reminder
function sendReminder(content, dueDate, priority) {
  socket.send(JSON.stringify({
    type: 'message',
    message_type: 'reminder',
    content: content,
    metadata: {
      due_date: dueDate,
      priority: priority
    }
  }));
}

// Send reaction
function addReaction(messageId, emoji) {
  socket.send(JSON.stringify({
    type: 'reaction',
    message_id: messageId,
    emoji: emoji
  }));
}

// Send typing indicator
function setTyping(isTyping) {
  socket.send(JSON.stringify({
    type: 'typing',
    is_typing: isTyping
  }));
}

// Receive messages
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'message':
      displayMessage(data.data);
      break;
    case 'user_joined':
      console.log(`${data.username} joined`);
      break;
    case 'user_left':
      console.log(`${data.username} left`);
      break;
    case 'typing':
      if(data.is_typing) {
        showTypingIndicator(data.username);
      }
      break;
    case 'reaction':
      addReactionToMessage(data.message_id, data.emoji, data.username);
      break;
    case 'error':
      console.error(data.message);
      break;
  }
};
```

### Python Client (for testing)
```python
import asyncio
import websockets
import json
from rest_framework_simplejwt.tokens import AccessToken

async def test_websocket():
    # Get token (in real scenario, from authentication)
    token = "your-jwt-token"
    channel_id = "channel-uuid"
    
    uri = f"ws://localhost:8000/ws/chat/{channel_id}/?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            'type': 'message',
            'message_type': 'text',
            'content': 'Hello from Python!'
        }))
        
        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(test_websocket())
```

---

## Message Type Reference

### TEXT (Default)
```json
{
  "type": "message",
  "message_type": "text",
  "content": "Any text content"
}
```
**Metadata**: None required

### REMINDER
```json
{
  "type": "message",
  "message_type": "reminder",
  "content": "Task description",
  "metadata": {
    "due_date": "2026-02-15T10:00:00Z",
    "priority": "high",
    "tags": ["important"]
  }
}
```
**Metadata**: 
- `due_date`: ISO 8601 (required)
- `priority`: low|medium|high|urgent
- `assigned_to`: user_id (optional)
- `tags`: list (optional)

### ALERT
```json
{
  "type": "message",
  "message_type": "alert",
  "content": "Alert message",
  "metadata": {
    "alert_level": "warning"
  }
}
```
**Metadata**:
- `alert_level`: info|warning|critical (required)
- `action_url`: string (optional)

### NOTIFICATION
```json
{
  "type": "message",
  "message_type": "notification",
  "content": "Notification content",
  "metadata": {
    "notification_type": "general",
    "target_user_id": "user-uuid"
  }
}
```
**Metadata**:
- `notification_type`: general|assignment|mention (required)
- `target_user_id`: user_id (optional)

### FILE (Reserved)
For future file attachment support

### MENTION (Reserved)
For @mentions and highlighting

### REACTION (Reserved)
For emoji reactions (handled via separate endpoint)

---

## API Response Format

### Message Object
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Message text",
  "message_type": "text",
  "message_type_display": "Plain Text Message",
  "sender_id": "user-uuid",
  "sender_username": "john_doe",
  "channel_id": "channel-uuid",
  "channel_name": "general",
  "metadata": {},
  "reactions": [
    {
      "id": "reaction-uuid",
      "emoji": "👍",
      "user_id": "other-user-uuid",
      "username": "jane_doe",
      "created_at": "2026-02-01T12:00:00Z"
    }
  ],
  "is_edited": false,
  "edited_at": null,
  "created_at": "2026-02-01T11:00:00Z",
  "updated_at": "2026-02-01T11:00:00Z"
}
```

### WebSocket Message Object (Lightweight)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Message text",
  "message_type": "text",
  "sender": {
    "id": "user-uuid",
    "username": "john_doe"
  },
  "channel_id": "channel-uuid",
  "metadata": {},
  "created_at": "2026-02-01T11:00:00Z"
}
```

---

## Validation

### Message Validation
```python
from apps.chat.message_handlers import MessageHandlerFactory

# Validate metadata for message type
metadata = {
    'due_date': '2026-02-15T10:00:00Z',
    'priority': 'high'
}

is_valid = MessageHandlerFactory.validate_message(
    'reminder',
    metadata
)
```

---

## Error Handling

### WebSocket Errors
```json
{
  "type": "error",
  "message": "Error description"
}
```

**Common Errors**:
- "Authentication failed" - Invalid JWT token
- "Access denied" - User doesn't have channel access
- "Invalid message type" - Unknown message_type
- "Message content cannot be empty" - Empty text message
- "Invalid JSON format" - Malformed JSON

---

## Testing

### Run Tests
```bash
# All chat tests
python test_chat_websocket.py

# Django tests
python manage.py test apps.chat

# With verbose output
python manage.py test apps.chat -v 2
```

### Validation Script
```bash
# Check Channels configuration
python check_channels.py
```

---

## Performance Tips

1. **Message Pagination**: Always use limit/offset for history
2. **Typing Indicators**: Use debouncing on client (don't send every keystroke)
3. **Reactions**: Batch reactions before sending
4. **Search**: Use indexed fields (channel, sender, message_type)
5. **Caching**: Cache message reactions and reaction counts

---

## Security Checklist

- ✅ JWT tokens validated on WebSocket connect
- ✅ Channel access verified before accepting connection
- ✅ All inputs validated before storage
- ✅ Only sender can delete/edit their messages
- ✅ CORS origins validated (AllowedHostsOriginValidator)
- ✅ Edit time limit (5 minutes) enforced
- ✅ Reactions use idempotent operations

---

## Debugging

### Enable Debug Logging
```python
# In settings.py
LOGGING = {
    'loggers': {
        'apps.chat.consumers': {
            'level': 'DEBUG',
        }
    }
}
```

### Check Consumer Connection
```javascript
// Browser console
socket.readyState  // 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
```

### Monitor Redis
```bash
redis-cli
> KEYS "chat_*"          # See all chat rooms
> LLEN "chat_room_id"   # Messages in room
> TTL "key"             # Time to live
```

---

## Version History

- **v2.0** (Feb 1, 2026): WebSocket Consumer & Message Types
- **v1.0** (Jan 2026): Initial model setup

---

**Last Updated**: February 1, 2026
**Maintained By**: Development Team
**Status**: Production Ready ✅
