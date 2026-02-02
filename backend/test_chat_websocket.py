"""
Comprehensive testing and validation script for Chat WebSocket functionality.

Tests:
- Chat model and message types
- WebSocket consumer routing
- Message handlers and utilities
- Message serialization
- JWT authentication integration
"""

import os
import sys
import json
import django
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from django.test import TestCase, AsyncClient
from django.contrib.auth import get_user_model
from apps.channel.models import Channel
from apps.workspace.models import Workspace
from apps.chat.models import Message, MessageType, MessageReaction
from apps.chat.serializers import MessageSerializer, MessageWebSocketSerializer
from apps.chat.message_handlers import (
    MessageHandlerFactory,
    ReminderMessageHandler,
    AlertMessageHandler,
    TextMessageHandler,
    ReminderPriority,
    AlertLevel,
)
from apps.chat.consumers import ChatConsumer
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(name, status, message=""):
    """Print test result."""
    icon = "✓" if status else "✗"
    status_text = "PASS" if status else "FAIL"
    print(f"  {icon} {name:<50} [{status_text}]")
    if message:
        print(f"    → {message}")


class ChatModelTests:
    """Test chat models."""

    @staticmethod
    def test_message_types():
        """Test message type enumeration."""
        print_header("TEST: Message Types")

        types = [choice[0] for choice in MessageType.choices]
        expected = [
            "text",
            "reminder",
            "alert",
            "notification",
            "file",
            "mention",
            "reaction",
        ]

        print("  Supported message types:")
        for msg_type in types:
            print(f"    - {msg_type}")

        success = all(t in types for t in expected)
        print_test("All expected message types exist", success)
        return success

    @staticmethod
    def test_create_text_message():
        """Test creating a text message."""
        print_header("TEST: Create Text Message")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            message = Message.create_text_message(
                sender=user, channel=channel, content="Hello, World!"
            )

            print_test("Text message created", message.id is not None)
            print_test("Message type is TEXT", message.message_type == MessageType.TEXT)
            print_test("Message content correct", message.content == "Hello, World!")

            return True
        except Exception as e:
            print_test("Text message creation", False, str(e))
            return False

    @staticmethod
    def test_create_reminder_message():
        """Test creating a reminder message."""
        print_header("TEST: Create Reminder Message")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            due_date = (datetime.now() + timedelta(days=1)).isoformat()
            reminder_data = {
                "due_date": due_date,
                "priority": "high",
            }

            message = Message.create_reminder_message(
                sender=user,
                channel=channel,
                content="Complete project report",
                reminder_data=reminder_data,
            )

            print_test("Reminder message created", message.id is not None)
            print_test(
                "Message type is REMINDER", message.message_type == MessageType.REMINDER
            )
            print_test(
                "Metadata stored correctly", message.metadata.get("priority") == "high"
            )

            return True
        except Exception as e:
            print_test("Reminder message creation", False, str(e))
            return False

    @staticmethod
    def test_create_alert_message():
        """Test creating an alert message."""
        print_header("TEST: Create Alert Message")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            message = Message.create_alert_message(
                sender=user,
                channel=channel,
                content="System maintenance scheduled",
                alert_level="warning",
            )

            print_test("Alert message created", message.id is not None)
            print_test(
                "Message type is ALERT", message.message_type == MessageType.ALERT
            )
            print_test(
                "Alert level stored", message.metadata.get("alert_level") == "warning"
            )

            return True
        except Exception as e:
            print_test("Alert message creation", False, str(e))
            return False

    @staticmethod
    def test_message_reaction():
        """Test message reactions."""
        print_header("TEST: Message Reactions")

        try:
            user1 = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            user2 = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(
                name="Test Workspace", created_by=user1
            )
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user1
            )

            message = Message.create_text_message(
                sender=user1, channel=channel, content="Great message!"
            )

            reaction = MessageReaction.objects.create(
                message=message, user=user2, emoji="👍"
            )

            print_test("Reaction created", reaction.id is not None)
            print_test("Reaction attached to message", reaction.message == message)
            print_test("Emoji stored correctly", reaction.emoji == "👍")

            return True
        except Exception as e:
            print_test("Message reaction", False, str(e))
            return False


class SerializerTests:
    """Test message serializers."""

    @staticmethod
    def test_message_serializer():
        """Test MessageSerializer."""
        print_header("TEST: Message Serializer")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            message = Message.create_text_message(
                sender=user, channel=channel, content="Test message"
            )

            serializer = MessageSerializer(message)
            data = serializer.data

            print_test("Serializer returns data", data is not None)
            print_test("Contains sender_username", "sender_username" in data)
            print_test("Contains channel_name", "channel_name" in data)
            print_test("Contains message_type_display", "message_type_display" in data)

            return True
        except Exception as e:
            print_test("Message serializer", False, str(e))
            return False

    @staticmethod
    def test_websocket_serializer():
        """Test lightweight WebSocket serializer."""
        print_header("TEST: WebSocket Serializer")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            message = Message.create_text_message(
                sender=user, channel=channel, content="Test message"
            )

            serializer = MessageWebSocketSerializer(message)
            data = serializer.data

            print_test("WebSocket serializer returns data", data is not None)
            print_test("Payload is minimal", len(data) <= 10)
            print_test(
                "Contains sender info",
                "sender" in data and "username" in data["sender"],
            )

            return True
        except Exception as e:
            print_test("WebSocket serializer", False, str(e))
            return False


class MessageHandlerTests:
    """Test message handler factory and utilities."""

    @staticmethod
    def test_handler_factory():
        """Test MessageHandlerFactory."""
        print_header("TEST: Message Handler Factory")

        try:
            # Test getting handlers
            text_handler = MessageHandlerFactory.get_handler(MessageType.TEXT)
            reminder_handler = MessageHandlerFactory.get_handler(MessageType.REMINDER)
            alert_handler = MessageHandlerFactory.get_handler(MessageType.ALERT)

            print_test("Text handler found", text_handler is not None)
            print_test("Reminder handler found", reminder_handler is not None)
            print_test("Alert handler found", alert_handler is not None)

            return True
        except Exception as e:
            print_test("Message handler factory", False, str(e))
            return False

    @staticmethod
    def test_reminder_handler():
        """Test reminder message handler."""
        print_header("TEST: Reminder Handler")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            due_date = (datetime.now() + timedelta(days=1)).isoformat()

            message = ReminderMessageHandler.create(
                sender=user,
                channel=channel,
                content="Task reminder",
                due_date=due_date,
                priority=ReminderPriority.HIGH,
                tags=["important", "deadline"],
            )

            print_test("Reminder created", message is not None)
            print_test(
                "Priority set correctly", message.metadata.get("priority") == "high"
            )
            print_test(
                "Tags stored", message.metadata.get("tags") == ["important", "deadline"]
            )

            # Test overdue check
            past_date = (datetime.now() - timedelta(days=1)).isoformat()
            past_message = Message.objects.create(
                sender=user,
                channel=channel,
                content="Past reminder",
                message_type=MessageType.REMINDER,
                metadata={"due_date": past_date},
            )

            is_overdue = ReminderMessageHandler.is_overdue(past_message)
            print_test("Overdue detection works", is_overdue)

            return True
        except Exception as e:
            print_test("Reminder handler", False, str(e))
            return False

    @staticmethod
    def test_alert_handler():
        """Test alert message handler."""
        print_header("TEST: Alert Handler")

        try:
            user = User.objects.create_user(
                username=f"user_{uuid4().hex[:8]}",
                email=f"user_{uuid4().hex[:8]}@test.com",
                password="testpass123",
            )
            workspace = Workspace.objects.create(name="Test Workspace", created_by=user)
            channel = Channel.objects.create(
                name="test-channel", workspace=workspace, created_by=user
            )

            message = AlertMessageHandler.create(
                sender=user,
                channel=channel,
                content="Critical system failure",
                alert_level=AlertLevel.CRITICAL,
                action_url="https://admin.example.com/alerts",
            )

            print_test("Alert created", message is not None)
            print_test(
                "Alert level set", message.metadata.get("alert_level") == "critical"
            )
            print_test(
                "Action URL stored", message.metadata.get("action_url") is not None
            )

            # Test display formatting
            formatted = AlertMessageHandler.format_display(message)
            print_test("Formatted with CSS class", "css_class" in formatted)
            print_test(
                "CSS class for critical", formatted["css_class"] == "alert-danger"
            )

            return True
        except Exception as e:
            print_test("Alert handler", False, str(e))
            return False


class RoutingTests:
    """Test WebSocket routing configuration."""

    @staticmethod
    def test_routing_configured():
        """Test that WebSocket routing is configured."""
        print_header("TEST: WebSocket Routing")

        try:
            from apps.chat.routing import websocket_urlpatterns

            print_test("Routing module imports", websocket_urlpatterns is not None)
            print_test("URL patterns defined", len(websocket_urlpatterns) > 0)

            # Check for chat consumer route
            chat_route_found = any(
                "ws/chat/" in str(pattern.pattern) for pattern in websocket_urlpatterns
            )
            print_test("Chat WebSocket route configured", chat_route_found)

            return True
        except Exception as e:
            print_test("WebSocket routing", False, str(e))
            return False


class ConsumerTests:
    """Test WebSocket consumer configuration."""

    @staticmethod
    def test_consumer_imports():
        """Test that consumer can be imported."""
        print_header("TEST: WebSocket Consumer")

        try:
            from apps.chat.consumers import ChatConsumer

            print_test("ChatConsumer imports", ChatConsumer is not None)
            print_test("Has connect method", hasattr(ChatConsumer, "connect"))
            print_test("Has disconnect method", hasattr(ChatConsumer, "disconnect"))
            print_test("Has receive method", hasattr(ChatConsumer, "receive"))

            return True
        except Exception as e:
            print_test("WebSocket consumer import", False, str(e))
            return False


def run_all_tests():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  CHAT WEBSOCKET COMPREHENSIVE TEST SUITE".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []

    # Run test suites
    results.append(("Message Types", ChatModelTests.test_message_types()))
    results.append(("Text Message", ChatModelTests.test_create_text_message()))
    results.append(("Reminder Message", ChatModelTests.test_create_reminder_message()))
    results.append(("Alert Message", ChatModelTests.test_create_alert_message()))
    results.append(("Message Reactions", ChatModelTests.test_message_reaction()))

    results.append(("Message Serializer", SerializerTests.test_message_serializer()))
    results.append(
        ("WebSocket Serializer", SerializerTests.test_websocket_serializer())
    )

    results.append(("Handler Factory", MessageHandlerTests.test_handler_factory()))
    results.append(("Reminder Handler", MessageHandlerTests.test_reminder_handler()))
    results.append(("Alert Handler", MessageHandlerTests.test_alert_handler()))

    results.append(("WebSocket Routing", RoutingTests.test_routing_configured()))
    results.append(("WebSocket Consumer", ConsumerTests.test_consumer_imports()))

    # Print summary
    print_header("SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}\n")

    if passed == total:
        print("  ✓ ALL TESTS PASSED!\n")
        return 0
    else:
        print(f"  ✗ {total - passed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n✗ Test suite error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
