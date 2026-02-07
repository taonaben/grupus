from django.apps import AppConfig


class TaskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.task"
    label = "task"

    def ready(self):
        try:
            import apps.task.signals.task_defaults  # noqa: F401
        except Exception as e:
            print(f"Error importing signals: {e}")
