from .models import TaskBoard, TaskList, Task, TaskAssignment
from rest_framework import serializers
from apps.workspace.models import SpaceMember
from apps.group.models import GroupMember
from apps.user.models import User
from apps.group.models import Group
from django.contrib.contenttypes.models import ContentType


class TaskBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskBoard
        fields = [
            "id",
            "workspace",
            "group",
            "name",
            "description",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at"]


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskList
        fields = [
            "id",
            "task_board",
            "name",
            "position",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at", "task_board", "position"]


class TaskAssignmentSerializer(serializers.ModelSerializer):
    assigned_to_type = serializers.CharField(write_only=True, required=False)
    assigned_to_id = serializers.UUIDField(write_only=True, required=False)
    assigned_to_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TaskAssignment
        fields = [
            "id",
            "task",
            "assigned_to_type",
            "assigned_to_id",
            "assigned_to_detail",
            "assigned_by",
            "assigned_at",
            "status",
            "notes",
        ]
        read_only_fields = ["id", "assigned_at", "assigned_by", "assigned_to_detail"]

    def get_assigned_to_detail(self, obj):
        """Return details about the assigned entity (User or Group)"""
        if obj.assigned_to:
            if isinstance(obj.assigned_to, User):
                return {
                    "type": "user",
                    "id": str(obj.assigned_to.id),
                    "username": obj.assigned_to.username,
                    "email": obj.assigned_to.email,
                }
            elif isinstance(obj.assigned_to, Group):
                return {
                    "type": "group",
                    "id": str(obj.assigned_to.id),
                    "name": obj.assigned_to.name,
                    "member_count": obj.assigned_to.member_count,
                }
        return None

    def create(self, validated_data):
        assigned_to_type = validated_data.pop("assigned_to_type", None)
        assigned_to_id = validated_data.pop("assigned_to_id", None)

        if assigned_to_type and assigned_to_id:
            if assigned_to_type == "user":
                content_type = ContentType.objects.get_for_model(User)
                assigned_to = User.objects.get(id=assigned_to_id)
            elif assigned_to_type == "group":
                content_type = ContentType.objects.get_for_model(Group)
                assigned_to = Group.objects.get(id=assigned_to_id)
            else:
                raise serializers.ValidationError(
                    "assigned_to_type must be 'user' or 'group'"
                )

            validated_data["content_type"] = content_type
            validated_data["object_id"] = assigned_to_id

        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    assignments = TaskAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "task_list",
            "title",
            "description",
            "assigned_to",
            "assignments",
            "position",
            "due_date",
            "is_completed",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at", "position", "assignments"]

    def validate_assigned_to(self, value):
        """Ensure assigned users/groups are valid"""
        if not value:
            return value

        task_list_id = self.initial_data.get("task_list")

        if not task_list_id:
            return value

        try:
            from .models import TaskList

            task_list = TaskList.objects.get(id=task_list_id)
            task_board = task_list.task_board
        except TaskList.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid task_list. Could not validate assignments."
            )

        # Get valid members based on workspace or group
        valid_user_ids = set()
        valid_group_ids = set()

        if task_board.workspace:
            workspace_members = SpaceMember.objects.filter(
                workspace=task_board.workspace, is_banned=False
            ).values_list("user_id", flat=True)
            valid_user_ids.update(workspace_members)

            # All groups in the workspace are valid
            from apps.group.models import Group

            workspace_groups = Group.objects.filter(
                workspace=task_board.workspace
            ).values_list("id", flat=True)
            valid_group_ids.update(workspace_groups)

        if task_board.group:
            group_members = GroupMember.objects.filter(
                group=task_board.group, is_banned=False
            ).values_list("user_id", flat=True)
            valid_user_ids.update(group_members)
            # The group itself is valid
            valid_group_ids.add(task_board.group.id)

        # Validate each assignment
        for assignment in value:
            assignment_type = assignment.get("type")
            assignment_id = assignment.get("id")

            if assignment_type == "user":
                try:
                    user = User.objects.get(id=assignment_id)
                    if user.id not in valid_user_ids:
                        raise serializers.ValidationError(
                            f"{user.username} is not a member of this workspace/group"
                        )
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        f"User with id {assignment_id} not found"
                    )

            elif assignment_type == "group":
                try:
                    group = Group.objects.get(id=assignment_id)
                    if group.id not in valid_group_ids:
                        raise serializers.ValidationError(
                            f"Group {group.name} is not valid for this task"
                        )
                except Group.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Group with id {assignment_id} not found"
                    )
            else:
                raise serializers.ValidationError(
                    "Each assignment must have 'type' (user or group) and 'id'"
                )

        return value


class TaskAssignmentSerializer(serializers.ModelSerializer):
    assigned_to_type = serializers.CharField(write_only=True, required=False)
    assigned_to_id = serializers.UUIDField(write_only=True, required=False)
    assigned_to_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TaskAssignment
        fields = [
            "id",
            "task",
            "assigned_to_type",
            "assigned_to_id",
            "assigned_to_detail",
            "assigned_by",
            "assigned_at",
            "status",
            "notes",
        ]
        read_only_fields = ["id", "assigned_at", "assigned_by", "assigned_to_detail"]

    def get_assigned_to_detail(self, obj):
        """Return details about the assigned entity (User or Group)"""
        if obj.assigned_to:
            if isinstance(obj.assigned_to, User):
                return {
                    "type": "user",
                    "id": str(obj.assigned_to.id),
                    "username": obj.assigned_to.username,
                    "email": obj.assigned_to.email,
                }
            elif isinstance(obj.assigned_to, Group):
                return {
                    "type": "group",
                    "id": str(obj.assigned_to.id),
                    "name": obj.assigned_to.name,
                    "member_count": obj.assigned_to.member_count,
                }
        return None

    def create(self, validated_data):
        assigned_to_type = validated_data.pop("assigned_to_type", None)
        assigned_to_id = validated_data.pop("assigned_to_id", None)

        if assigned_to_type and assigned_to_id:
            if assigned_to_type == "user":
                content_type = ContentType.objects.get_for_model(User)
                assigned_to = User.objects.get(id=assigned_to_id)
            elif assigned_to_type == "group":
                content_type = ContentType.objects.get_for_model(Group)
                assigned_to = Group.objects.get(id=assigned_to_id)
            else:
                raise serializers.ValidationError(
                    "assigned_to_type must be 'user' or 'group'"
                )

            validated_data["content_type"] = content_type
            validated_data["object_id"] = assigned_to_id

        return super().create(validated_data)
