"""
WebSocket URL routing for chat application.

Maps WebSocket connections to their respective consumers.
"""

from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    # WebSocket endpoint: 'ws://localhost:8000/ws/chat/$roomId/?token=$jwtToken';
    # The room_id should be a valid Channel UUID
    path("ws/chat/<str:room_id>/", ChatConsumer.as_asgi()),
]
