from rest_framework import serializers
from .models import Channel


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = [
            "id",
            "workspace",
            "group",
            "name",
            "is_private",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def validate(self, data):
        workspace = data.get("workspace")
        group = data.get("group")

        # Ensure at least one parent is specified
        if not workspace and not group:
            raise serializers.ValidationError(
                {"error": "Either workspace or group must be specified"}
            )

        # Ensure not both are specified
        if workspace and group:
            raise serializers.ValidationError(
                {"error": "Channel cannot belong to both workspace and group"}
            )

        # Validate channel name uniqueness within the parent context
        name = data.get("name")
        if name:
            if workspace:
                if Channel.objects.filter(workspace=workspace, name=name).exists():
                    raise serializers.ValidationError(
                        {
                            "name": "A channel with this name already exists in this workspace"
                        }
                    )
            if group:
                if Channel.objects.filter(group=group, name=name).exists():
                    raise serializers.ValidationError(
                        {
                            "name": "A channel with this name already exists in this group"
                        }
                    )

        return data
