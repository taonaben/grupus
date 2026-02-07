from rest_framework import serializers
from .models import Workspace, SpaceMember, WorkspaceType


class WorkspaceSerializer(serializers.ModelSerializer):

    workspace_type_name = serializers.CharField(
        source="workspace_type.name", read_only=True
    )

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
            "workspace_type_name",
        )

    def validate(self, data):
        """Validate metadata against WorkspaceType schema if workspace_type is set."""
        # Get workspace_type from data or instance
        workspace_type = data.get("workspace_type")
        if not workspace_type and self.instance:
            workspace_type = self.instance.workspace_type

        # Get metadata from data or instance
        metadata = data.get("metadata")
        if metadata is None and self.instance:
            metadata = self.instance.metadata

        # Validate metadata against workspace type schema
        if workspace_type and metadata:
            is_valid, errors = workspace_type.validate_data(metadata)
            if not is_valid:
                raise serializers.ValidationError({"metadata": errors})

        return data


class WorkspaceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceType
        fields = "__all__"
        read_only_fields = ("id",)

    def validate_schema(self, value):
        """Validate the schema structure and field definitions."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Schema must be a valid JSON object.")

        # Schema can be empty
        if not value:
            return value

        # If schema has fields, validate the structure
        if "fields" in value:
            fields = value["fields"]
            if not isinstance(fields, dict):
                raise serializers.ValidationError("Schema 'fields' must be an object.")

            # Validate each field definition
            valid_types = [
                "string",
                "number",
                "boolean",
                "user",
                "array",
                "object",
                "date",
            ]
            for field_name, field_def in fields.items():
                if not isinstance(field_def, dict):
                    raise serializers.ValidationError(
                        f"Field definition for '{field_name}' must be an object."
                    )

                # Validate field type
                if "type" not in field_def:
                    raise serializers.ValidationError(
                        f"Field '{field_name}' must have a 'type' property."
                    )

                if field_def["type"] not in valid_types:
                    raise serializers.ValidationError(
                        f"Field '{field_name}' has invalid type '{field_def['type']}'. "
                        f"Valid types are: {', '.join(valid_types)}"
                    )

                # Validate required field
                if "required" in field_def and not isinstance(
                    field_def["required"], bool
                ):
                    raise serializers.ValidationError(
                        f"Field '{field_name}' 'required' property must be a boolean."
                    )

        return value


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
