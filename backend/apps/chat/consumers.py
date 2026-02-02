"""
WebSocket Consumer for real-time chat functionality.

Handles:
- User connections/disconnections to chat rooms
- Message broadcasting to room participants
- JWT token authentication
- Room-based subscriptions
- Multiple message types (text, reminders, alerts, etc.)
"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import Message, MessageType
from .serializers import MessageWebSocketSerializer
from apps.channel.models import Channel
from apps.user.models import User

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for chat rooms.

    Handles real-time messaging with JWT authentication, room-based subscriptions,
    and support for multiple message types.

    WebSocket URL: ws://localhost/ws/chat/<room_id>/
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        - Extracts and validates JWT token from query string
        - Verifies user has access to the channel
        - Joins the user to the chat room group
        """
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope.get("user", AnonymousUser())
        self.user_id = None
        self.channel = None

        logger.info(
            f"WebSocket connect attempt - Room: {self.room_id}, User: {self.user}"
        )

        # Authenticate user
        try:
            await self._authenticate_user()
        except Exception as e:
            logger.error(f"Authentication failed for room {self.room_id}: {str(e)}")
            await self.close(code=4001, reason="Authentication failed")
            return

        # Verify channel access
        try:
            await self._verify_channel_access()
        except Exception as e:
            logger.error(f"Channel access denied for {self.user_id}: {str(e)}")
            await self.close(code=4003, reason="Access denied")
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()
        logger.info(f"User {self.user_id} joined room {self.room_id}")

        # Notify others in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user_id": str(self.user_id),
                "username": self.user.username,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        - Removes user from room group
        - Notifies other participants
        """
        if hasattr(self, "room_group_name"):
            # Notify room that user left
            if self.user_id:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_left",
                        "user_id": str(self.user_id),
                        "username": self.user.username,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        logger.info(
            f"User {self.user_id} left room {self.room_id} (code: {close_code})"
        )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket message.

        Expected JSON format:
        {
            "type": "message",
            "message_type": "text|reminder|alert|...",
            "content": "...",
            "metadata": { ... }  // optional, depends on message_type
        }
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from {self.user_id}")
            await self.send_error("Invalid JSON format")
            return

        message_type = data.get("type", "message")

        if message_type == "message":
            await self._handle_message(data)
        elif message_type == "typing":
            await self._handle_typing(data)
        elif message_type == "reaction":
            await self._handle_reaction(data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await self.send_error(f"Unknown message type: {message_type}")

    async def _authenticate_user(self):
        """
        Authenticate user via JWT token.

        Extracts token from query string, validates it, and loads the user.
        """
        # Try to get user from scope (set by AuthMiddlewareStack)
        user = self.scope.get("user")

        if not user or user.is_anonymous:
            # Try to extract token from query string as fallback
            query_string = self.scope.get("query_string", b"").decode()
            token = None

            if "token=" in query_string:
                token = query_string.split("token=")[1].split("&")[0]
            elif "Authorization=" in query_string:
                auth = query_string.split("Authorization=")[1].split("&")[0]
                if auth.startswith("Bearer%20"):
                    token = auth.replace("Bearer%20", "")

            if not token:
                raise Exception("No authentication token provided")

            try:
                access_token = AccessToken(token)
                user_id = access_token["user_id"]
                user = await self._get_user(user_id)

                if not user:
                    raise Exception("User not found")

                self.user = user
            except (InvalidToken, TokenError) as e:
                raise Exception(f"Invalid token: {str(e)}")

        if not user or user.is_anonymous:
            raise Exception("User not authenticated")

        self.user = user
        self.user_id = user.id

    async def _verify_channel_access(self):
        """
        Verify that the user has access to the channel.

        Currently allows access if:
        - Channel is not private, OR
        - User is the channel creator, OR
        - User has explicit access (can be extended)
        """
        self.channel = await self._get_channel(self.room_id)

        if not self.channel:
            raise Exception(f"Channel {self.room_id} not found")

        # Allow access if channel is not private
        if not self.channel.is_private:
            return

        # Allow if user is the creator
        if self.channel.created_by_id == self.user_id:
            return

        # TODO: Add workspace/group membership checks for private channels
        raise Exception("Access denied to private channel")

    async def _handle_message(self, data: Dict[str, Any]):
        """
        Handle incoming chat message.

        - Validates message content
        - Saves to database
        - Broadcasts to room
        """
        message_type = data.get("message_type", MessageType.TEXT)
        content = data.get("content", "").strip()
        metadata = data.get("metadata", {})

        # Validate message
        if not content:
            await self.send_error("Message content cannot be empty")
            return

        if message_type not in dict(MessageType.choices):
            await self.send_error(f"Invalid message type: {message_type}")
            return

        # Save message to database
        try:
            message = await self._save_message(
                content=content, message_type=message_type, metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            await self.send_error("Failed to save message")
            return

        # Serialize message for broadcast
        serializer = MessageWebSocketSerializer(message)
        message_data = serializer.data

        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_data,
            },
        )

        logger.info(f"Message saved: {message.id} from {self.user_id}")

    async def _handle_typing(self, data: Dict[str, Any]):
        """
        Handle typing indicator.

        Broadcast to room that user is typing without saving to database.
        """
        is_typing = data.get("is_typing", False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_typing",
                "user_id": str(self.user_id),
                "username": self.user.username,
                "is_typing": is_typing,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _handle_reaction(self, data: Dict[str, Any]):
        """
        Handle message reaction (emoji).

        - Validates reaction data
        - Saves to database
        - Broadcasts to room
        """
        message_id = data.get("message_id")
        emoji = data.get("emoji", "").strip()

        if not message_id or not emoji:
            await self.send_error("message_id and emoji are required for reactions")
            return

        if len(emoji) > 10:
            await self.send_error("Emoji must be 10 characters or less")
            return

        try:
            reaction = await self._save_reaction(message_id, emoji)
        except Exception as e:
            logger.error(f"Error saving reaction: {str(e)}")
            await self.send_error("Failed to save reaction")
            return

        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_reaction",
                "message_id": message_id,
                "user_id": str(self.user_id),
                "username": self.user.username,
                "emoji": emoji,
                "timestamp": datetime.now().isoformat(),
            },
        )

    # ========== Group Message Handlers (Channels) ==========

    async def chat_message(self, event):
        """
        Broadcast chat message to WebSocket.

        Called by group_send with type='chat_message'
        """
        message = event["message"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "data": message,
                }
            )
        )

    async def user_joined(self, event):
        """
        Broadcast user join notification.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_joined",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_left(self, event):
        """
        Broadcast user leave notification.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_left",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_typing(self, event):
        """
        Broadcast typing indicator.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "is_typing": event["is_typing"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def message_reaction(self, event):
        """
        Broadcast message reaction.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "reaction",
                    "message_id": event["message_id"],
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "emoji": event["emoji"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def send_error(self, error_message: str):
        """
        Send error message to client.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "message": error_message,
                }
            )
        )

    # ========== Database Operations (Sync to Async) ==========

    @database_sync_to_async
    def _get_user(self, user_id: str) -> Optional[User]:
        """Retrieve user from database."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_channel(self, channel_id: str) -> Optional[Channel]:
        """Retrieve channel from database."""
        try:
            return Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            return None

    @database_sync_to_async
    def _save_message(
        self, content: str, message_type: str, metadata: Dict[str, Any] = None
    ) -> Message:
        """Save message to database."""
        if metadata is None:
            metadata = {}

        message = Message.objects.create(
            sender=self.user,
            channel=self.channel,
            content=content,
            message_type=message_type,
            metadata=metadata,
        )
        return message

    @database_sync_to_async
    def _save_reaction(self, message_id: str, emoji: str):
        """Save message reaction to database."""
        from .models import MessageReaction

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            raise Exception(f"Message {message_id} not found")

        # Use get_or_create for idempotence (if reaction already exists, just return it)
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=self.user,
            emoji=emoji,
        )
        return reaction
