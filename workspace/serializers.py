from rest_framework import serializers
from .models import Workspace, SpaceMember


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "access_code",
            "member_count",
            "channel_count",
            "group_count",
        )
