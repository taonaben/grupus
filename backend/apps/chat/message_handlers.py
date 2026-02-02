"""
Message handler utilities for modular message type support.

Provides:
- Message factory classes for different message types
- Message validation utilities
- Message formatting utilities
- Type-specific handlers
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import Message, MessageType, MessageReaction
from apps.user.models import User
from apps.channel.models import Channel

logger = logging.getLogger(__name__)


class ReminderPriority(str, Enum):
    """Priority levels for reminder messages."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class BaseMessageHandler:
    """Base class for message type handlers."""

    message_type: MessageType = MessageType.TEXT

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> bool:
        """Override to validate type-specific metadata."""
        return True

    @staticmethod
    def format_display(message: Message) -> Dict[str, Any]:
        """Override to format message for display."""
        return {
            "id": str(message.id),
            "content": message.content,
            "type": message.get_message_type_display(),
            "sender": message.sender.username,
            "created_at": message.created_at.isoformat(),
        }


class TextMessageHandler(BaseMessageHandler):
    """Handler for plain text messages."""

    message_type = MessageType.TEXT

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> bool:
        """Text messages don't require metadata."""
        return True

    @staticmethod
    def create(sender: User, channel: Channel, content: str) -> Message:
        """Create a plain text message."""
        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.TEXT,
        )


class ReminderMessageHandler(BaseMessageHandler):
    """Handler for reminder/task messages."""

    message_type = MessageType.REMINDER

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> bool:
        """Validate reminder metadata."""
        required_fields = ["due_date"]
        return all(field in metadata for field in required_fields)

    @staticmethod
    def create(
        sender: User,
        channel: Channel,
        content: str,
        due_date: str,
        assigned_to: Optional[str] = None,
        priority: str = ReminderPriority.MEDIUM,
        tags: Optional[list] = None,
    ) -> Message:
        """
        Create a reminder message.

        Args:
            sender: User sending the reminder
            channel: Channel where reminder is posted
            content: Reminder text/description
            due_date: ISO 8601 formatted date (e.g., '2026-02-15T10:00:00Z')
            assigned_to: User ID to assign reminder to
            priority: 'low', 'medium', 'high', 'urgent'
            tags: Optional list of tags for categorization

        Returns:
            Message object
        """
        metadata = {
            "due_date": due_date,
            "priority": priority,
        }

        if assigned_to:
            metadata["assigned_to"] = str(assigned_to)

        if tags:
            metadata["tags"] = tags

        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.REMINDER,
            metadata=metadata,
        )

    @staticmethod
    def format_display(message: Message) -> Dict[str, Any]:
        """Format reminder message for display."""
        metadata = message.metadata or {}
        return {
            "id": str(message.id),
            "content": message.content,
            "type": message.get_message_type_display(),
            "sender": message.sender.username,
            "due_date": metadata.get("due_date"),
            "priority": metadata.get("priority", ReminderPriority.MEDIUM),
            "assigned_to": metadata.get("assigned_to"),
            "tags": metadata.get("tags", []),
            "created_at": message.created_at.isoformat(),
        }

    @staticmethod
    def is_overdue(message: Message) -> bool:
        """Check if reminder is past its due date."""
        metadata = message.metadata or {}
        due_date_str = metadata.get("due_date")

        if not due_date_str:
            return False

        try:
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
            return datetime.now(due_date.tzinfo) > due_date
        except (ValueError, TypeError):
            logger.warning(f"Invalid due_date format in reminder {message.id}")
            return False


class AlertMessageHandler(BaseMessageHandler):
    """Handler for system alert messages."""

    message_type = MessageType.ALERT

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> bool:
        """Validate alert metadata."""
        alert_level = metadata.get("alert_level")
        return alert_level in [level.value for level in AlertLevel]

    @staticmethod
    def create(
        sender: User,
        channel: Channel,
        content: str,
        alert_level: str = AlertLevel.INFO,
        action_url: Optional[str] = None,
    ) -> Message:
        """
        Create an alert message.

        Args:
            sender: User sending the alert
            channel: Channel to post alert in
            content: Alert message
            alert_level: 'info', 'warning', 'critical'
            action_url: Optional URL for action button

        Returns:
            Message object
        """
        metadata = {
            "alert_level": alert_level,
        }

        if action_url:
            metadata["action_url"] = action_url

        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.ALERT,
            metadata=metadata,
        )

    @staticmethod
    def format_display(message: Message) -> Dict[str, Any]:
        """Format alert message for display with styling hints."""
        metadata = message.metadata or {}
        alert_level = metadata.get("alert_level", AlertLevel.INFO)

        # CSS class hint based on alert level
        css_class_map = {
            AlertLevel.INFO: "alert-info",
            AlertLevel.WARNING: "alert-warning",
            AlertLevel.CRITICAL: "alert-danger",
        }

        return {
            "id": str(message.id),
            "content": message.content,
            "type": message.get_message_type_display(),
            "sender": message.sender.username,
            "alert_level": alert_level,
            "css_class": css_class_map.get(alert_level, "alert-info"),
            "action_url": metadata.get("action_url"),
            "created_at": message.created_at.isoformat(),
        }


class NotificationMessageHandler(BaseMessageHandler):
    """Handler for user notification messages."""

    message_type = MessageType.NOTIFICATION

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> bool:
        """Validate notification metadata."""
        return True

    @staticmethod
    def create(
        sender: User,
        channel: Channel,
        content: str,
        notification_type: str = "general",
        target_user_id: Optional[str] = None,
    ) -> Message:
        """
        Create a notification message.

        Args:
            sender: User sending the notification
            channel: Channel to post notification in
            content: Notification message
            notification_type: Type of notification (e.g., 'general', 'assignment', 'mention')
            target_user_id: User this notification is targeted to

        Returns:
            Message object
        """
        metadata = {
            "notification_type": notification_type,
        }

        if target_user_id:
            metadata["target_user_id"] = str(target_user_id)

        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.NOTIFICATION,
            metadata=metadata,
        )


class MessageHandlerFactory:
    """Factory for creating appropriate message handlers."""

    _handlers = {
        MessageType.TEXT: TextMessageHandler,
        MessageType.REMINDER: ReminderMessageHandler,
        MessageType.ALERT: AlertMessageHandler,
        MessageType.NOTIFICATION: NotificationMessageHandler,
    }

    @classmethod
    def get_handler(cls, message_type: str) -> Optional[BaseMessageHandler]:
        """Get handler for message type."""
        return cls._handlers.get(message_type)

    @classmethod
    def register_handler(cls, message_type: str, handler: BaseMessageHandler):
        """Register a new message type handler."""
        cls._handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")

    @classmethod
    def format_message(cls, message: Message) -> Dict[str, Any]:
        """Format message using appropriate handler."""
        handler = cls.get_handler(message.message_type)

        if handler:
            return handler.format_display(message)

        # Fallback to basic formatting
        return {
            "id": str(message.id),
            "content": message.content,
            "type": message.get_message_type_display(),
            "sender": message.sender.username,
            "created_at": message.created_at.isoformat(),
        }

    @classmethod
    def validate_message(cls, message_type: str, metadata: Dict[str, Any]) -> bool:
        """Validate message metadata using appropriate handler."""
        handler = cls.get_handler(message_type)

        if not handler:
            logger.warning(f"No handler found for message type: {message_type}")
            return False

        return handler.validate_metadata(metadata)


class MessageUtils:
    """Utility functions for message operations."""

    @staticmethod
    def get_message_by_id(message_id: str) -> Optional[Message]:
        """Retrieve message by ID."""
        try:
            return Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return None

    @staticmethod
    def get_channel_messages(
        channel_id: str,
        limit: int = 50,
        offset: int = 0,
        message_type: Optional[str] = None,
    ) -> list:
        """
        Retrieve messages from a channel.

        Args:
            channel_id: Channel UUID
            limit: Number of messages to retrieve
            offset: Pagination offset
            message_type: Filter by message type (optional)

        Returns:
            List of Message objects
        """
        query = Message.objects.filter(channel_id=channel_id)

        if message_type:
            query = query.filter(message_type=message_type)

        return list(query.order_by("-created_at")[offset : offset + limit])

    @staticmethod
    def search_messages(
        channel_id: str,
        search_term: str,
        limit: int = 50,
    ) -> list:
        """
        Search messages in a channel.

        Args:
            channel_id: Channel UUID
            search_term: Search query
            limit: Maximum results

        Returns:
            List of matching Message objects
        """
        from django.db.models import Q

        return list(
            Message.objects.filter(
                Q(channel_id=channel_id) & Q(content__icontains=search_term)
            ).order_by("-created_at")[:limit]
        )

    @staticmethod
    def get_reactions_for_message(message_id: str) -> Dict[str, int]:
        """
        Get reaction counts for a message.

        Args:
            message_id: Message UUID

        Returns:
            Dict mapping emoji to count
        """
        reactions = (
            MessageReaction.objects.filter(message_id=message_id)
            .values("emoji")
            .annotate(count=models.Count("id"))
        )

        return {r["emoji"]: r["count"] for r in reactions}

    @staticmethod
    def delete_message(message_id: str, user_id: str) -> bool:
        """
        Delete a message (only by sender).

        Args:
            message_id: Message UUID
            user_id: User attempting to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            message = Message.objects.get(id=message_id)

            # Only allow deletion by sender
            if str(message.sender_id) != str(user_id):
                logger.warning(
                    f"User {user_id} attempted to delete message by {message.sender_id}"
                )
                return False

            message.delete()
            logger.info(f"Message {message_id} deleted by {user_id}")
            return True
        except Message.DoesNotExist:
            logger.warning(f"Attempt to delete non-existent message {message_id}")
            return False

    @staticmethod
    def edit_message(
        message_id: str,
        user_id: str,
        new_content: str,
    ) -> Optional[Message]:
        """
        Edit a message (only by sender, within time limit).

        Args:
            message_id: Message UUID
            user_id: User attempting to edit
            new_content: New message content

        Returns:
            Updated Message object or None
        """
        try:
            message = Message.objects.get(id=message_id)

            # Only allow editing by sender
            if str(message.sender_id) != str(user_id):
                logger.warning(
                    f"User {user_id} attempted to edit message by {message.sender_id}"
                )
                return None

            # Optional: Enforce edit time limit (e.g., 5 minutes)
            edit_limit = timedelta(minutes=5)
            if (
                datetime.now(message.created_at.tzinfo) - message.created_at
                > edit_limit
            ):
                logger.warning(f"Edit time limit exceeded for message {message_id}")
                return None

            message.content = new_content
            message.is_edited = True
            message.edited_at = datetime.now()
            message.save()

            logger.info(f"Message {message_id} edited by {user_id}")
            return message
        except Message.DoesNotExist:
            logger.warning(f"Attempt to edit non-existent message {message_id}")
            return None


# Import models for annotation
from django.db import models  # noqa: E402
