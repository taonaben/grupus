from django.apps import AppConfig


class ChannelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.channel"
    label = "channel"

    def ready(self):
        try:
            import apps.channel.signals  # noqa: F401
        except Exception as e:
            print(f"Error importing signals: {e}")
