from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from apps.group.models import Group
from apps.workspace.models import Workspace
from apps.channel.models import Channel
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Group)
def create_channel_defaults_for_group(sender, instance, created, **kwargs):
    """
    Groups will only have one default channel named "general".
    No other channels will be created!
    """
    if not created:
        return
    try:
        with transaction.atomic():
            Channel.objects.create(
                name="general",
                group=instance,
                created_by=instance.created_by,
            )
    except Exception as e:
        # Log the exception or handle it as needed
        logger.error(f"Error creating default channel for group {instance.id}: {e}")


@receiver(post_save, sender=Workspace)
def create_channel_defaults_for_workspace(sender, instance, created, **kwargs):
    """
    Workspaces will have a default channel named "batch 1".

    Additional channels can be created by workspace admins later.

    These channels will serve as batches of users (students, teammates, etc.) in the workspace (courses, projects, etc.).

    Multiple channels in workspace will serve to separate different batches of users and preserve the workspace structure.
    """
    if not created:
        return

    try:
        with transaction.atomic():
            Channel.objects.create(
                name="batch 1",
                workspace=instance,
                created_by=instance.created_by,
            )
    except Exception as e:
        # Log the exception or handle it as needed
        logger.error(f"Error creating default channel for workspace {instance.id}: {e}")
