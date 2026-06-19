from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.channel.models import Channel
from apps.chat import services
from apps.chat.models import Message, MessageType
from apps.user.models import User
from apps.workspace.models import SpaceMember, Workspace


IN_MEMORY_CHANNEL_LAYER = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


class ChatTestDataMixin:
    def setUp(self):
        self.user = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="password",
            is_email_verified=True,
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password",
            is_email_verified=True,
        )
        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="password",
            is_email_verified=True,
        )
        self.workspace = Workspace.objects.create(
            name="Workspace",
            created_by=self.user,
        )
        SpaceMember.objects.create(workspace=self.workspace, user=self.user)
        SpaceMember.objects.create(workspace=self.workspace, user=self.other_user)
        self.channel = Channel.objects.create(
            name="general",
            workspace=self.workspace,
            created_by=self.user,
        )


class MessageServiceTests(ChatTestDataMixin, TestCase):
    def test_create_is_idempotent_by_client_message_id(self):
        first = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Hello",
            client_message_id="install-1:msg-1",
            client_mutation_id="mutation-1",
        )
        retry = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Hello again",
            client_message_id="install-1:msg-1",
            client_mutation_id="mutation-2",
        )

        self.assertEqual(first.id, retry.id)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(retry.content, "Hello")

    def test_server_sequence_is_per_channel(self):
        first = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="First",
        )
        second = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Second",
        )

        self.assertEqual(first.server_sequence, 1)
        self.assertEqual(second.server_sequence, 2)

    def test_update_increments_version_and_rejects_stale_version(self):
        message = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Before",
        )

        updated = services.update_message(
            user=self.user,
            message_id=str(message.id),
            content="After",
            version=message.version,
        )

        self.assertEqual(updated.content, "After")
        self.assertEqual(updated.version, 2)
        self.assertTrue(updated.is_edited)

        with self.assertRaises(services.ChatConflict):
            services.update_message(
                user=self.user,
                message_id=str(message.id),
                content="Stale",
                version=1,
            )

    def test_delete_soft_deletes_and_rejects_stale_version(self):
        message = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Delete me",
        )

        deleted = services.delete_message(
            user=self.user,
            message_id=str(message.id),
            version=message.version,
        )

        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(deleted.version, 2)

        with self.assertRaises(services.ChatGone):
            services.delete_message(
                user=self.user,
                message_id=str(message.id),
                version=1,
            )

    def test_event_payload_contains_sync_fields(self):
        message = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Payload",
            client_message_id="install-1:msg-2",
        )

        payload = services.build_message_event_payload(message, "message.created")
        data = payload["data"]

        self.assertEqual(payload["type"], "message.created")
        self.assertEqual(data["client_message_id"], "install-1:msg-2")
        self.assertEqual(data["server_sequence"], 1)
        self.assertEqual(data["version"], 1)
        self.assertIn("deleted_at", data)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYER)
class MessageApiTests(ChatTestDataMixin, APITestCase):
    def test_create_returns_contract_fields_and_idempotent_retry(self):
        self.client.force_authenticate(self.user)
        url = reverse("message-list")
        payload = {
            "client_message_id": "install-1:api-msg-1",
            "client_mutation_id": "api-mutation-1",
            "content": "API hello",
            "message_type": MessageType.TEXT,
            "metadata": {"client_message_id": "install-1:api-msg-1"},
        }

        first = self.client.post(
            f"{url}?channel_id={self.channel.id}",
            payload,
            format="json",
        )
        retry = self.client.post(
            f"{url}?channel_id={self.channel.id}",
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(retry.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["id"], retry.data["id"])
        self.assertEqual(first.data["client_message_id"], payload["client_message_id"])
        self.assertEqual(first.data["server_sequence"], 1)
        self.assertEqual(first.data["version"], 1)
        self.assertIn("deleted_at", first.data)
        self.assertEqual(Message.objects.count(), 1)

    def test_list_supports_since_sequence_and_access_control(self):
        services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="First",
        )
        second = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Second",
        )

        self.client.force_authenticate(self.other_user)
        url = reverse("message-list")
        response = self.client.get(
            f"{url}?channel_id={self.channel.id}&since_sequence=1"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(second.id))

        self.client.force_authenticate(self.outsider)
        forbidden = self.client.get(f"{url}?channel_id={self.channel.id}")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_and_delete_require_current_version(self):
        self.client.force_authenticate(self.user)
        message = services.create_message(
            user=self.user,
            channel_id=str(self.channel.id),
            content="Before",
        )
        detail_url = reverse("message-detail", args=[message.id])

        stale = self.client.patch(
            detail_url,
            {"version": 99, "content": "Stale"},
            format="json",
        )
        updated = self.client.patch(
            detail_url,
            {"version": 1, "content": "After"},
            format="json",
        )
        deleted = self.client.delete(
            detail_url,
            {"version": 2, "client_mutation_id": "delete-mutation"},
            format="json",
        )

        self.assertEqual(stale.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["content"], "After")
        self.assertEqual(updated.data["version"], 2)
        self.assertEqual(deleted.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(deleted.data["deleted_at"])
        self.assertEqual(deleted.data["version"], 3)
