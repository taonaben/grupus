from django.db import models
from user.models import User
import uuid
import string
import random
import time

# Create your models here.


class Workspace(models.Model):

    def generate_access_code():
        MAX_ATTEMPTS = 10  
        chars = string.ascii_uppercase + string.digits

        for attempt in range(MAX_ATTEMPTS):
            # Generate code with pattern: XXXX-XXXX
            code = (
                "".join(random.choices(chars, k=4))
                + "-"
                + "".join(random.choices(chars, k=4))
            )

            # Check if code already exists
            if not Workspace.objects.filter(access_code=code).exists():
                return code

        # If we couldn't generate a unique code after MAX_ATTEMPTS
        timestamp = hex(int(time.time()))[2:]
        return f"{timestamp[:4]}-{timestamp[4:8]}".upper()

    # core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="workspaces",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # visibility and access
    access_code = models.CharField(
        max_length=100, unique=True, default=generate_access_code
    )
    is_public = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=True)
    max_members = models.PositiveIntegerField(default=100)

    # stats
    member_count = models.PositiveIntegerField(default=0)
    channel_count = models.PositiveIntegerField(default=0)
    group_count = models.PositiveIntegerField(default=0)

    # rules & restrictions
    content_guidelines = models.TextField(blank=True, null=True)
    rules = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.name


class SpaceMember(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="workspace_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_banned = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    contribution_score = models.IntegerField(default=0)
    custom_permissions = models.JSONField(default=dict, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ["workspace", "user"]
        indexes = [
            models.Index(fields=["workspace", "role"]),
            models.Index(fields=["user", "is_banned"]),
        ]

    def __str__(self):
        return f"{self.user} in {self.workspace} ({self.role})"
