from rest_framework import serializers
from .models import Group, GroupMember


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = (
            "id",
            "workspace",
            "name",
            "description",
            "created_by",
            "created_at",
            "updated_at",
            "is_public",
            "requires_approval",
            "access_code",
            "max_members",
            "member_count",
            "active_member_count",
            "channel_count",
            "content_guidelines",
            "rules",
        )

        read_only_fields = (
            "id",
            "workspace",
            "created_by",
            "created_at",
            "updated_at",
            "access_code",
            "member_count",
            "active_member_count",
            "channel_count",
        )


# Serializer for GroupMember model

class GroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMember
        fields = (
            "id",
            "group",
            "user",
            "role",
            "is_banned",
            "joined_at",
            "last_seen",
            "contribution_score",
        )

        read_only_fields = (
            "id",
            "group",
            "user",
            "joined_at",
            "last_seen",
        )