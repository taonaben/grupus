from django.db import models
from django.core.exceptions import ValidationError
from apps.user.models import User
from apps.channel.models import Channel
import uuid


class MessageType(models.TextChoices):
    """Enumeration of supported message types for modularity."""

    TEXT = "text", "Plain Text Message"
    REMINDER = "reminder", "Task/Event Reminder"
    ALERT = "alert", "System Alert"
    NOTIFICATION = "notification", "User Notification"
    FILE = "file", "File Attachment"
    MENTION = "mention", "User Mention"
    REACTION = "reaction", "Message Reaction"


class Message(models.Model):
    """
    Core message model supporting multiple message types.

    The 'message_type' field determines how the message should be displayed/processed.
    The 'metadata' JSONField stores type-specific data without schema migrations.

    This design allows new message types to be added without database changes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField(
        help_text="Main message content (plain text or base content)"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        help_text="Type of message determines how it should be displayed/processed",
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="messages"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Type-specific metadata (e.g., reminder_time, alert_level, file_url, etc.)",
    )
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
            models.Index(fields=["message_type"]),
        ]

    def __str__(self):
        return f"{self.get_message_type_display()} from {self.sender} in {self.channel}"

    def clean(self):
        """Validate message based on type."""
        if not self.content and self.message_type == MessageType.TEXT:
            raise ValidationError("Text messages must have content")

        if self.message_type == MessageType.REMINDER and not self.metadata:
            raise ValidationError(
                "Reminder messages must have metadata with reminder details"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def create_text_message(sender, channel, content):
        """Factory method: Create a plain text message."""
        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.TEXT,
        )

    @staticmethod
    def create_reminder_message(sender, channel, content, reminder_data):
        """
        Factory method: Create a reminder message.

        Args:
            reminder_data: dict with keys like {
                'due_date': '2026-02-15T10:00:00Z',
                'assigned_to': '<user_id>',
                'priority': 'high|medium|low'
            }
        """
        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.REMINDER,
            metadata=reminder_data,
        )

    @staticmethod
    def create_alert_message(sender, channel, content, alert_level="info"):
        """
        Factory method: Create an alert message.

        Args:
            alert_level: 'info', 'warning', 'critical'
        """
        return Message.objects.create(
            sender=sender,
            channel=channel,
            content=content,
            message_type=MessageType.ALERT,
            metadata={"alert_level": alert_level},
        )


class MessageReaction(models.Model):
    """
    Store user reactions to messages (e.g., emoji reactions).
    Allows non-invasive message replies without cluttering the message stream.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reactions")
    emoji = models.CharField(max_length=10, help_text="Unicode emoji character")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["message", "user", "emoji"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} reacted {self.emoji} to {self.message.id}"
