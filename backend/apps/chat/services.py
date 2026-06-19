import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import status

from apps.channel.models import Channel
from apps.group.models import GroupMember
from apps.workspace.models import SpaceMember
from .models import Message, MessageType

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ChatAccessDenied(ChatServiceError):
    status_code = status.HTTP_403_FORBIDDEN


class ChatNotFound(ChatServiceError):
    status_code = status.HTTP_404_NOT_FOUND


class ChatConflict(ChatServiceError):
    status_code = status.HTTP_409_CONFLICT


class ChatGone(ChatServiceError):
    status_code = status.HTTP_410_GONE


class ChatValidationError(ChatServiceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


def _active_workspace_member_exists(user, workspace_id) -> bool:
    return SpaceMember.objects.filter(
        workspace_id=workspace_id,
        user=user,
        is_banned=False,
    ).exists()


def _active_group_member_exists(user, group_id) -> bool:
    return GroupMember.objects.filter(
        group_id=group_id,
        user=user,
        is_banned=False,
    ).exists()


def user_can_access_channel(user, channel: Channel) -> bool:
    if not user or not user.is_authenticated:
        return False

    if user.is_staff or channel.created_by_id == user.id:
        return True

    if channel.workspace_id:
        return _active_workspace_member_exists(user, channel.workspace_id)

    if channel.group_id:
        return _active_group_member_exists(user, channel.group_id)

    return not channel.is_private


def get_channel_for_user(user, channel_id: str, lock: bool = False) -> Channel:
    queryset = Channel.objects.select_related("workspace", "group")
    if lock:
        queryset = queryset.select_for_update(of=("self",))

    try:
        channel = queryset.get(id=channel_id)
    except Channel.DoesNotExist as exc:
        raise ChatNotFound("Channel not found") from exc

    if not user_can_access_channel(user, channel):
        raise ChatAccessDenied("You do not have access to this channel")

    return channel


def get_accessible_messages(
    user,
    channel_id: str | None = None,
    since_sequence: int | None = None,
    before_sequence: int | None = None,
    limit: int | None = None,
):
    queryset = Message.objects.select_related("sender", "channel").prefetch_related(
        "reactions"
    )

    if channel_id:
        get_channel_for_user(user, channel_id)
        queryset = queryset.filter(channel_id=channel_id)
    else:
        queryset = queryset.filter(
            Q(channel__created_by=user)
            | Q(channel__workspace__members__user=user, channel__workspace__members__is_banned=False)
            | Q(channel__group__members__user=user, channel__group__members__is_banned=False)
            | Q(channel__workspace__isnull=True, channel__group__isnull=True, channel__is_private=False)
        ).distinct()

    if since_sequence is not None:
        queryset = queryset.filter(server_sequence__gt=since_sequence)

    if before_sequence is not None:
        queryset = queryset.filter(server_sequence__lt=before_sequence).order_by(
            "-server_sequence", "-created_at"
        )
    else:
        queryset = queryset.order_by("server_sequence", "created_at")

    if limit:
        queryset = queryset[:limit]

    return queryset


def create_message(
    *,
    user,
    channel_id: str,
    content: str,
    message_type: str = MessageType.TEXT,
    metadata: dict[str, Any] | None = None,
    client_message_id: str | None = None,
    client_mutation_id: str | None = None,
) -> Message:
    metadata = metadata or {}
    client_message_id = client_message_id or metadata.get("client_message_id")

    if message_type not in dict(MessageType.choices):
        raise ChatValidationError(f"Invalid message type: {message_type}")

    if message_type == MessageType.TEXT and not (content or "").strip():
        raise ChatValidationError("Text messages must have non-empty content")

    if message_type == MessageType.REMINDER and not metadata:
        raise ChatValidationError("Reminder messages must include metadata")

    with transaction.atomic():
        channel = get_channel_for_user(user, channel_id, lock=True)

        if client_message_id:
            existing = (
                Message.objects.select_related("sender", "channel")
                .prefetch_related("reactions")
                .filter(client_message_id=client_message_id)
                .first()
            )
            if existing:
                if existing.channel_id != channel.id:
                    raise ChatConflict("client_message_id belongs to another channel")
                if not user_can_access_channel(user, existing.channel):
                    raise ChatAccessDenied("You do not have access to this message")
                return existing

        next_sequence = (
            Message.objects.filter(channel=channel).aggregate(
                max_sequence=Max("server_sequence")
            )["max_sequence"]
            or 0
        ) + 1

        return Message.objects.create(
            sender=user,
            channel=channel,
            content=content.strip() if message_type == MessageType.TEXT else content,
            message_type=message_type,
            metadata=metadata,
            client_message_id=client_message_id,
            client_mutation_id=client_mutation_id,
            server_sequence=next_sequence,
            version=1,
        )


def update_message(
    *,
    user,
    message_id: str,
    content: str,
    version: int,
    client_mutation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Message:
    with transaction.atomic():
        try:
            message = (
                Message.objects.select_for_update()
                .select_related("sender", "channel")
                .prefetch_related("reactions")
                .get(id=message_id)
            )
        except Message.DoesNotExist as exc:
            raise ChatNotFound("Message not found") from exc

        if not user_can_access_channel(user, message.channel):
            raise ChatAccessDenied("You do not have access to this message")

        if message.deleted_at:
            raise ChatGone("Message is deleted")

        if message.sender_id != user.id and not user.is_staff:
            raise ChatAccessDenied("Only the sender can edit this message")

        if message.version != version:
            raise ChatConflict("Message version is stale")

        if not (content or "").strip() and message.message_type == MessageType.TEXT:
            raise ChatValidationError("Text messages must have non-empty content")

        message.content = content.strip() if message.message_type == MessageType.TEXT else content
        if metadata is not None:
            message.metadata = metadata
        message.client_mutation_id = client_mutation_id or message.client_mutation_id
        message.version += 1
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save()
        return message


def delete_message(
    *,
    user,
    message_id: str,
    version: int,
    client_mutation_id: str | None = None,
) -> Message:
    with transaction.atomic():
        try:
            message = (
                Message.objects.select_for_update()
                .select_related("sender", "channel")
                .prefetch_related("reactions")
                .get(id=message_id)
            )
        except Message.DoesNotExist as exc:
            raise ChatNotFound("Message not found") from exc

        if not user_can_access_channel(user, message.channel):
            raise ChatAccessDenied("You do not have access to this message")

        if message.deleted_at:
            raise ChatGone("Message is already deleted")

        if message.sender_id != user.id and not user.is_staff:
            raise ChatAccessDenied("Only the sender can delete this message")

        if message.version != version:
            raise ChatConflict("Message version is stale")

        message.deleted_at = timezone.now()
        message.client_mutation_id = client_mutation_id or message.client_mutation_id
        message.version += 1
        message.save(update_fields=["deleted_at", "client_mutation_id", "version", "updated_at"])
        return message


def build_message_event_payload(message: Message, event_type: str) -> dict[str, Any]:
    return {
        "type": event_type,
        "data": {
            "id": str(message.id),
            "channel_id": str(message.channel_id),
            "client_message_id": message.client_message_id,
            "content": message.content,
            "message_type": message.message_type,
            "metadata": message.metadata or {},
            "sender_id": str(message.sender_id),
            "sender_username": message.sender.username,
            "server_sequence": message.server_sequence,
            "version": message.version,
            "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "updated_at": message.updated_at.isoformat() if message.updated_at else None,
        },
    }


def broadcast_message_event(message: Message, event_type: str) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"chat_{message.channel_id}",
            {
                "type": "chat_message_event",
                "payload": build_message_event_payload(message, event_type),
            },
        )
    except Exception:
        logger.exception("Failed to broadcast chat message event")
