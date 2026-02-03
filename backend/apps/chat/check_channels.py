"""
Configuration validation script for Django Channels setup.

Run this to verify that all Channels and WebSocket infrastructure is properly configured.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from django.conf import settings


def check_channels_configuration():
    """Validate that Channels is properly configured."""
    print("\n" + "=" * 60)
    print("DJANGO CHANNELS CONFIGURATION VALIDATION")
    print("=" * 60)

    checks_passed = 0
    checks_failed = 0

    # Check 1: ASGI Application
    print("\n[1] ASGI Application Configuration:")
    asgi_app = getattr(settings, "ASGI_APPLICATION", None)
    if asgi_app == "main.asgi.application":
        print(f"    ✓ ASGI_APPLICATION = '{asgi_app}'")
        checks_passed += 1
    else:
        print(f"    ✗ ASGI_APPLICATION not configured correctly: {asgi_app}")
        checks_failed += 1

    # Check 2: Channels in INSTALLED_APPS
    print("\n[2] Channels App Registration:")
    if "channels" in settings.INSTALLED_APPS:
        print("    ✓ 'channels' found in INSTALLED_APPS")
        checks_passed += 1
    else:
        print("    ✗ 'channels' NOT in INSTALLED_APPS")
        checks_failed += 1

    if "channels_redis" in settings.INSTALLED_APPS:
        print("    ✓ 'channels_redis' found in INSTALLED_APPS")
        checks_passed += 1
    else:
        print("    ✗ 'channels_redis' NOT in INSTALLED_APPS")
        checks_failed += 1

    # Check 3: Channel Layers Configuration
    print("\n[3] Channel Layers Configuration:")
    channel_layers = getattr(settings, "CHANNEL_LAYERS", None)
    if channel_layers:
        print("    ✓ CHANNEL_LAYERS configured")
        print(
            f"      Backend: {channel_layers.get('default', {}).get('BACKEND', 'N/A')}"
        )
        hosts = channel_layers.get("default", {}).get("CONFIG", {}).get("hosts", [])
        print(f"      Redis hosts: {hosts}")
        checks_passed += 1
    else:
        print("    ✗ CHANNEL_LAYERS not configured")
        checks_failed += 1

    # Check 4: Redis Connection
    print("\n[4] Redis Connection:")
    try:
        import redis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        # Try to extract from channel layers config
        if channel_layers:
            redis_url = (
                channel_layers.get("default", {})
                .get("CONFIG", {})
                .get("hosts", [redis_url])[0]
            )

        print(f"    Attempting connection to: {redis_url}")
        r = redis.from_url(redis_url)
        r.ping()
        print("    ✓ Redis connection successful")
        checks_passed += 1
    except Exception as e:
        print(f"    ✗ Redis connection failed: {e}")
        print("    ⚠ Ensure Redis is running at the configured URL")
        checks_failed += 1

    # Check 5: WSGI Application still configured
    print("\n[5] WSGI Application Configuration:")
    wsgi_app = getattr(settings, "WSGI_APPLICATION", None)
    if wsgi_app == "main.wsgi.application":
        print(f"    ✓ WSGI_APPLICATION = '{wsgi_app}' (for compatibility)")
        checks_passed += 1
    else:
        print(f"    ⚠ WSGI_APPLICATION may not be configured: {wsgi_app}")

    # Check 6: Chat Routing Module
    print("\n[6] Chat Routing Module:")
    try:
        from apps.chat import routing

        if hasattr(routing, "websocket_urlpatterns"):
            print(f"    ✓ Chat routing module found")
            print(
                f"    ✓ websocket_urlpatterns defined: {routing.websocket_urlpatterns}"
            )
            checks_passed += 1
        else:
            print("    ✗ websocket_urlpatterns not found in routing module")
            checks_failed += 1
    except Exception as e:
        print(f"    ✗ Error importing chat routing: {e}")
        checks_failed += 1

    # Check 7: ASGI Module
    print("\n[7] ASGI Module:")
    try:
        from main import asgi

        if hasattr(asgi, "application"):
            print(f"    ✓ ASGI application module found")
            print(f"    ✓ application callable exists")
            checks_passed += 1
        else:
            print("    ✗ application callable not found")
            checks_failed += 1
    except Exception as e:
        print(f"    ✗ Error importing ASGI module: {e}")
        checks_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_checks = checks_passed + checks_failed
    print(f"✓ Passed: {checks_passed}/{total_checks}")
    print(f"✗ Failed: {checks_failed}/{total_checks}")

    if checks_failed == 0:
        print("\n✓ All checks passed! Channels is properly configured.")
        return True
    else:
        print("\n✗ Some checks failed. Review the errors above.")
        return False


if __name__ == "__main__":
    success = check_channels_configuration()
    sys.exit(0 if success else 1)
