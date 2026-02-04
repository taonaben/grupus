from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.badges.models import Badge
import uuid


class User(AbstractUser):
    """User's core fields, that will be used everywhere"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """Presentation. The user's personal information"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, null=True
    )
    preferred_language = models.CharField(max_length=10, default="en")
    notification_settings = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class UserStats(models.Model):
    """Gamification & Reputation. This will have all the user's collective performance statistics in their groups/workspaces"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="userstats"
    )
    score = models.IntegerField(default=0)
    reputation_level = models.CharField(max_length=20, null=True, blank=True)
    completed_tasks = models.IntegerField(default=0)


class UserBadges(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="userbadges"
    )
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")


class UserPresence(models.Model):
    """
    Ephemeral.
    Not persistent identity.
        - Redis
        - Cache
        - Websocket memory
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="userpresence"
    )
    last_active = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=True)


UserPresence._meta.managed = False  # This model won't create any DB table


class UserSubscription(models.Model):
    """System & Preferences. User's subscription and membership details"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="usersubscription"
    )
    subscription_type = models.CharField(max_length=20)
    is_premium_member = models.BooleanField(default=False)
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s subscription"
