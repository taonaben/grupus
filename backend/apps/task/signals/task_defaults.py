from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from apps.task.models import TaskBoard, TaskList
from apps.group.models import Group
from apps.workspace.models import Workspace
import logging

logger = logging.getLogger(__name__)

DEFAULT_LISTS = ["To Do", "In Progress", "Done"]


@receiver(post_save, sender=Group)
def create_task_board_for_group(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        with transaction.atomic():
            TaskBoard.objects.create(
                group=instance,
                created_by=instance.created_by,
            )

            for list_name in DEFAULT_LISTS:
                TaskList.objects.create(
                    task_board=TaskBoard.objects.get(group=instance),
                    name=list_name,
                )
    except Exception as e:
        logger.error(f"Error creating default task board for group {instance.id}: {e}")


@receiver(post_save, sender=Workspace)
def create_task_board_for_workspace(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        with transaction.atomic():
            TaskBoard.objects.create(
                workspace=instance,
                created_by=instance.created_by,
            )

            for list_name in DEFAULT_LISTS:
                TaskList.objects.create(
                    task_board=TaskBoard.objects.get(workspace=instance),
                    name=list_name,
                )
    except Exception as e:
        logger.error(
            f"Error creating default task board for workspace {instance.id}: {e}"
        )
