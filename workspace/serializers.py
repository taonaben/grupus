from rest_framework import serializers
from .models import Workspace, SpaceMember


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_by",
            "created_at",
            "access_code",
            "member_count",
            "channel_count",
            "group_count",
        )


class SpaceMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceMember

        fields = [
            "id",
            "workspace",
            "user",
            "role",
            "is_banned",
            "joined_at",
            "last_seen",
            "contribution_score",
            "custom_permissions",
            "notes",
        ]

        read_only_fields = (
            "workspace",
            "user",
            "id",
            "joined_at",
            "last_seen",
        )
