import uuid
from django.db import models
from workspace.models import Workspace
from group.models import Group
from user.models import User


# Create your models here.
class Channel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="channels",
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="channels",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    is_private = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="created_channels",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} in {self.workspace or self.group}"
