from rest_framework import serializers
from .models import Message, MessageReaction, MessageType


class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for message reactions."""

    user_id = serializers.StringRelatedField(source="user.id", read_only=True)
    username = serializers.StringRelatedField(source="user.username", read_only=True)

    class Meta:
        model = MessageReaction
        fields = ["id", "emoji", "user_id", "username", "created_at"]
        read_only_fields = ["id", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    """
    Main serializer for messages with support for multiple message types.

    Includes nested reactions and supports polymorphic message handling.
    """

    sender_id = serializers.StringRelatedField(source="sender.id", read_only=True)
    sender_username = serializers.StringRelatedField(
        source="sender.username", read_only=True
    )
    channel_id = serializers.StringRelatedField(source="channel.id", read_only=True)
    channel_name = serializers.StringRelatedField(source="channel.name", read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    message_type_display = serializers.CharField(
        source="get_message_type_display", read_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "message_type",
            "message_type_display",
            "sender_id",
            "sender_username",
            "channel_id",
            "channel_name",
            "metadata",
            "reactions",
            "is_edited",
            "edited_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sender_id",
            "sender_username",
            "channel_id",
            "channel_name",
            "message_type_display",
            "reactions",
            "edited_at",
            "created_at",
            "updated_at",
        ]

    def validate_message_type(self, value):
        """Validate that the message type is supported."""
        valid_types = [choice[0] for choice in MessageType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid message type. Must be one of: {', '.join(valid_types)}"
            )
        return value

    def validate(self, attrs):
        """Cross-field validation for message content and type."""
        message_type = attrs.get("message_type", MessageType.TEXT)
        content = attrs.get("content", "")

        # Text messages must have content
        if message_type == MessageType.TEXT and not content.strip():
            raise serializers.ValidationError(
                {"content": "Text messages must have non-empty content"}
            )

        # Reminder messages should have metadata
        if message_type == MessageType.REMINDER and not attrs.get("metadata"):
            raise serializers.ValidationError(
                {
                    "metadata": "Reminder messages must include reminder details in metadata"
                }
            )

        return attrs


class MessageWebSocketSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for WebSocket messages.
    Optimized for real-time transmission with minimal payload.
    """

    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "message_type",
            "sender",
            "channel_id",
            "metadata",
            "created_at",
        ]

    def get_sender(self, obj):
        return {
            "id": str(obj.sender.id),
            "username": obj.sender.username,
        }


class BulkMessageSerializer(serializers.ModelSerializer):
    """Serializer for bulk message operations (message history, bulk creates)."""

    sender_username = serializers.StringRelatedField(
        source="sender.username", read_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "message_type",
            "sender_username",
            "created_at",
            "metadata",
        ]
        read_only_fields = ["id", "created_at"]
