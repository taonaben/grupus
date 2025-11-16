from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration with profile details"""

    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True, min_length=8)

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
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, data):
        if data.get("password") != data.get("password2"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "profile_picture",
            "score",
            "reputation_level",
            "contribution_badges",
            "completed_tasks",
            "is_active",
            "last_active",
            "status_message",
            "date_joined",
            "is_premium_member",
            "preferred_language",
            "notification_settings",
        ]
        read_only_fields = [
            "id",
            "score",
            "reputation_level",
            "contribution_badges",
            "completed_tasks",
            "last_active",
            "date_joined",
        ]
