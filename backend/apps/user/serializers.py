from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.user import models

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration with profile details"""

    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    preferred_language = serializers.CharField(required=False, default="en")
    notification_settings = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "bio",
            "profile_picture",
            "preferred_language",
            "notification_settings",
        ]

    def validate(self, data):
        if data.get("password") != data.get("password2"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        # Extract profile and related data
        validated_data.pop("password2")
        password = validated_data.pop("password")

        # Extract profile-related fields
        profile_data = {
            "first_name": validated_data.pop("first_name"),
            "last_name": validated_data.pop("last_name"),
            "bio": validated_data.pop("bio", None),
            "profile_picture": validated_data.pop("profile_picture", None),
            "preferred_language": validated_data.pop("preferred_language", "en"),
            "notification_settings": validated_data.pop("notification_settings", {}),
        }

        # Create user
        user = User.objects.create_user(password=password, **validated_data)

        # Create related objects
        models.UserProfile.objects.create(user=user, **profile_data)
        models.UserStats.objects.create(user=user)
        models.UserSubscription.objects.create(user=user)

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user's profile details"""

    class Meta:
        model = models.UserProfile
        fields = [
            "user",
            "first_name",
            "last_name",
            "bio",
            "profile_picture",
            "preferred_language",
            "notification_settings",
        ]
        read_only_fields = [
            "user",
        ]


class UserStatsSerializer(serializers.ModelSerializer):
    """Serializer for user's statistics"""

    class Meta:
        model = models.UserStats
        fields = [
            "user",
            "score",
            "reputation_level",
            "completed_tasks",
        ]
        read_only_fields = [
            "user",
        ]


class UserBadgesSerializer(serializers.ModelSerializer):
    """Serializer for user's badges"""

    class Meta:
        model = models.UserBadges
        fields = [
            "user",
            "badge",
            "earned_at",
        ]
        read_only_fields = ["user"]


class UserPresenceSerializer(serializers.ModelSerializer):
    """Serializer for the user's presence in the app"""

    class Meta:
        model = models.UserPresence
        fields = [
            "user",
            "last_active",
            "is_online",
        ]
        read_only_fields = ["user"]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user's subscription details"""

    class Meta:
        model = models.UserSubscription
        fields = [
            "user",
            "subscription_type",
            "is_premium_member",
            "subscription_start",
            "subscription_end",
        ]
        read_only_fields = [
            "user",
        ]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for complete user details with nested relationships"""

    profile = UserProfileSerializer(read_only=True)
    stats = UserStatsSerializer(source="userStats", read_only=True)
    subscription = UserSubscriptionSerializer(source="usersubscription", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "profile",
            "stats",
            "subscription",
        ]
        read_only_fields = ["id"]
