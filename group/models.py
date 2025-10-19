from django.db import models
from workspace.models import Workspace
from user.models import User
import uuid


# Create your models here.
class Group(models.Model):
    # core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="groups"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="created_groups",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # access and visibility
    is_public = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=True)
    invite_code = models.CharField(max_length=100, unique=True)
    max_members = models.PositiveIntegerField(default=10)

    # stats
    member_count = models.PositiveIntegerField(default=0)
    active_member_count = models.PositiveIntegerField(default=0)
    channel_count = models.PositiveIntegerField(default=0)

    # rules & guidelines
    content_guidelines = models.TextField(blank=True, null=True)
    rules = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_banned = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    contribution_score = models.IntegerField(default=0)

    class Meta:
        unique_together = ["group", "user"]
        indexes = [
            models.Index(fields=["group", "role"]),
            models.Index(fields=["user", "is_banned"]),
        ]

    def __str__(self):
        return f"{self.user} in {self.group} ({self.role})"
