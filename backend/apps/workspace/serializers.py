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

        extra_kwargs = {
            "is_public": {"required": False, "allow_null": True},
            "requires_approval": {"required": False, "allow_null": True},
            "max_members": {"required": False, "allow_null": True},
        }

    def validate(self, data):
        """Validate metadata against WorkspaceType schema if workspace_type is set."""
        data = super().validate(data)
        # Get workspace_type from data or instance
        workspace_type = data.get("workspace_type")
        if not workspace_type and self.instance:
            workspace_type = self.instance.workspace_type

        # Get metadata from data or instance
        metadata_from_request = "metadata" in data
        metadata = data.get("metadata")
        if metadata is None and self.instance:
            metadata = self.instance.metadata

        # Some clients send metadata grouped by workspace type id; focus on the
        # payload that matches the selected workspace type and ignore the rest.
        metadata_to_validate = metadata
        if (
            workspace_type
            and isinstance(metadata, dict)
            and str(workspace_type.id) in metadata
        ):
            scoped_metadata = metadata[str(workspace_type.id)]
            if isinstance(scoped_metadata, dict):
                metadata_to_validate = scoped_metadata
                if metadata_from_request:
                    data["metadata"] = metadata_to_validate

        # Validate metadata against workspace type schema
        if workspace_type and metadata_to_validate:
            is_valid, errors = workspace_type.validate_data(metadata_to_validate)
            if not is_valid:
                raise serializers.ValidationError({"metadata": errors})

        default_fallbacks = {
            "is_public": False,
            "requires_approval": True,
            "max_members": 100,
        }
        for field, default in default_fallbacks.items():
            if field in data and data[field] is None:
                data[field] = default

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
