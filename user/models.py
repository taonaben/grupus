from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.


class User(AbstractUser):
    # core identity fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    # profile and personalization fields
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, null=True
    )

    # score & contribution tracking
    score = models.IntegerField(default=0)
    reputation_level = models.CharField(max_length=20, default="Newbie")
    contribution_badges = models.JSONField(default=list, blank=True)
    completed_tasks = models.IntegerField(default=0)

    # activity and engagement metrics
    is_active = models.BooleanField(default=True)
    last_active = models.DateTimeField(auto_now=True)
    status_message = models.CharField(max_length=100, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # system and preference settings
    is_premium_member = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=10, default="en")
    notification_settings = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
