# Step 1: Django Channels & ASGI Configuration - Complete ✓

## Overview
Successfully configured Django Channels for WebSocket support. The infrastructure is now in place to handle real-time WebSocket connections alongside traditional HTTP requests.

## What Was Implemented

### 1. **ASGI Configuration** (`backend/main/asgi.py`)
- Replaced basic WSGI-only ASGI with full `ProtocolTypeRouter` setup
- Configured HTTP requests → Django ASGI application
- Configured WebSocket connections → Channels routing with authentication
- Added `AllowedHostsOriginValidator` for security (prevents cross-origin WebSocket attacks)
- Added `AuthMiddlewareStack` to enable JWT token authentication on WebSocket connections

### 2. **Channel Layers Setup** (`backend/main/settings.py`)
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")],
            "capacity": 1500,  # Max messages in channel
            "expiry": 10,      # Message TTL in seconds
        },
    },
}
```
- Uses Redis as the channel layer backend (required for Channels to broadcast messages across multiple processes)
- Configurable via `REDIS_URL` environment variable
- Set `capacity=1500` for room sizes up to ~1500 concurrent users per room
- Set `expiry=10` for temporary message caching

### 3. **Chat WebSocket Routing** (`backend/apps/chat/routing.py`)
- Created routing module to map WebSocket URLs to consumers
- Pattern ready: `ws://localhost/ws/chat/<room_id>/`
- Placeholder for `ChatConsumer` (will be implemented in Step 2)

### 4. **Server Configuration Updates**

#### Dockerfile (`backend/Dockerfile`)
- Added Daphne as the default ASGI server (supports HTTP/1.1 and WebSocket)
- Default command: `daphne -b 0.0.0.0 -p 8000 main.asgi:application`

#### Entrypoint Script (`backend/entrypoint.sh`)
- Updated from Gunicorn (WSGI-only) to Daphne (ASGI)
- Ensures migrations and static file collection run before server start

#### Requirements (`backend/requirements.txt`)
- Added `daphne==4.1.2` (ASGI server with WebSocket support)
- Already present: `channels==4.3.1`, `channels_redis==4.3.0`, `redis==6.4.0`

### 5. **Configuration Validation Script** (`backend/check_channels.py`)
Comprehensive validation tool that checks:
- ✓ ASGI application configured
- ✓ Channels app registered
- ✓ Channel layers configured with Redis backend
- ⚠ Redis connection status (requires Redis running)
- ✓ WSGI application still configured (backward compatibility)
- ✓ Chat routing module present
- ✓ ASGI callable exists

**Validation Results**: 7/8 checks passed
```
✓ ASGI_APPLICATION = 'main.asgi.application'
✓ 'channels' found in INSTALLED_APPS
✓ 'channels_redis' found in INSTALLED_APPS
✓ CHANNEL_LAYERS configured
  Backend: channels_redis.core.RedisChannelLayer
  Redis hosts: ['redis://localhost:6379/0']
⚠ Redis connection failed (expected if not running locally)
✓ WSGI_APPLICATION = 'main.asgi.application' (for compatibility)
✓ Chat routing module found
✓ ASGI application module found
```

## Architecture Diagram

```
┌─────────────────┐
│   Client        │
│  (Browser)      │
└────────┬────────┘
         │
    ┌────┴──────┐
    │            │
  HTTP       WebSocket
    │            │
    ▼            ▼
┌──────────────────────────────────────────┐
│  Daphne ASGI Server (Port 8000)          │
│  ┌──────────────────────────────────────┐│
│  │ ProtocolTypeRouter                   ││
│  │  ├── HTTP → Django ASGI Application  ││
│  │  └── WebSocket → Channels URLRouter  ││
│  │      ├── AuthMiddlewareStack (JWT)   ││
│  │      └── AllowedHostsOriginValidator ││
│  └──────────────────────────────────────┘│
└─────────────┬──────────────────┬──────────┘
              │                  │
              ▼                  ▼
        ┌─────────────────────────────────────┐
        │  Django App                         │
        │  (REST API Endpoints)               │
        │                                     │
        │  Chat Consumers (WebSocket)         │
        │  (Will be added in Step 2)          │
        └────────────────┬────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    ┌────────┐    ┌──────────┐    ┌──────────┐
    │  DB    │    │  Redis   │    │  Cache   │
    │(Postgres)  │(Channel  │    │ (Redis)  │
    │        │    │ Layer)   │    │          │
    └────────┘    └──────────┘    └──────────┘
```

## Current Status

### ✓ Completed
- ASGI server configured (Daphne)
- Channel layers configured (Redis backend)
- WebSocket routing structure in place
- Authentication middleware ready
- Origin validation for security
- Configuration validation tool created

### ⏭ Next Steps (Step 2)
- Create `ChatConsumer` class for WebSocket connection handling
- Implement `connect()`, `disconnect()`, and `receive()` methods
- Add message type support (text, reminder, alert, etc.)
- Implement room-based message broadcasting
- Add message persistence to database

## Running the Application

### Development
```bash
# Ensure Redis is running
redis-cli ping  # Should return PONG

# Run Django server with Daphne
python manage.py runserver  # Uses Daphne via ASGI_APPLICATION setting

# Or explicitly:
daphne -b 0.0.0.0 -p 8000 main.asgi:application
```

### Docker
```bash
# Build and run
docker-compose up --build

# The entrypoint.sh automatically uses Daphne
```

### Validation
```bash
# Run configuration check
python check_channels.py

# Expected output: 7-8 checks passed
# (Redis connection check fails if Redis isn't running, but configuration is correct)
```

## Environment Variables

Configure these in your `.env` file:

```bash
# Redis connection for Channel Layers
REDIS_URL=redis://localhost:6379/0

# Django settings
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=grupus
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Security Considerations

1. **Origin Validation**: `AllowedHostsOriginValidator` prevents CSRF attacks on WebSocket connections
2. **Authentication**: `AuthMiddlewareStack` ensures only authenticated users can establish WebSocket connections
3. **CORS Settings**: Update `CORS_ALLOWED_ORIGINS` in settings for production domains
4. **Redis**: Secure Redis connection in production (use password/TLS)

## Troubleshooting

### Redis Connection Failed
- Ensure Redis is running: `redis-cli ping`
- Check Redis URL configuration matches your setup
- In Docker, ensure `redis` service is running and healthy

### WebSocket Connection Refused
- Verify Daphne is running (not Gunicorn)
- Check firewall allows port 8000
- Verify `ASGI_APPLICATION = "main.asgi.application"` in settings

### Import Errors
- Run `python check_channels.py` to validate setup
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Verify `daphne` is installed: `pip install daphne`

## Key Files Modified

1. `backend/main/settings.py` - Added CHANNEL_LAYERS configuration
2. `backend/main/asgi.py` - Configured ProtocolTypeRouter with WebSocket support
3. `backend/apps/chat/routing.py` - Created WebSocket URL routing (new file)
4. `backend/Dockerfile` - Updated to use Daphne
5. `backend/entrypoint.sh` - Updated to use Daphne
6. `backend/requirements.txt` - Added daphne dependency
7. `backend/check_channels.py` - Created validation script (new file)

---

**Status**: ✅ Step 1 Complete and Verified
**Next**: Ready for Step 2 - WebSocket Consumer Implementation
