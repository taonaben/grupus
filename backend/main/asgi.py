"""
ASGI config for main project with Django Channels support.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
https://channels.readthedocs.io/en/latest/deploying/index.html
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")

# Initialize Django ASGI application early to ensure Django is set up
django_asgi_app = get_asgi_application()

# Import routing and settings after Django setup
from apps.chat import routing as chat_routing  # noqa: E402
from django.conf import settings  # noqa: E402

_ws_app = AuthMiddlewareStack(
    URLRouter(
        chat_routing.websocket_urlpatterns,
    )
)

# AllowedHostsOriginValidator blocks clients that don't send an Origin header
# (e.g. Postman, mobile apps, native clients). Only enable it in production
# where browser-based CSRF protection is needed; JWT auth in the consumer
# handles real authentication in all environments.
if not settings.DEBUG:
    _ws_app = AllowedHostsOriginValidator(_ws_app)

application = ProtocolTypeRouter(
    {
        # Django's ASGI application to handle traditional HTTP requests
        "http": django_asgi_app,
        # WebSocket chat handler with JWT authentication
        "websocket": _ws_app,
    }
)
