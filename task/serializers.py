from .models import TaskBoard, TaskList, Task, TaskAssignment
from rest_framework import serializers
from workspace.models import SpaceMember
from group.models import GroupMember
from user.models import User


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

        read_only_fields = ["id", "created_at", "updated_at"]


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "task_list",
            "title",
            "description",
            "assigned_to",
            "position",
            "due_date",
            "is_completed",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at", "position"]

    def validate_assigned_to(self, value):
        """Ensure assigned users are members of the workspace/group"""
        if not value:
            return value

        request = self.context.get("request")
        task_list_id = self.initial_data.get("task_list")

        if not task_list_id:
            return value

        try:
            from .models import TaskList

            task_list = TaskList.objects.get(id=task_list_id)
            task_board = task_list.task_board
        except TaskList.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid task_list. Could not validate assigned users."
            )

        # Get valid members based on workspace or group
        valid_user_ids = set()

        if task_board.workspace:
            workspace_members = SpaceMember.objects.filter(
                workspace=task_board.workspace, is_banned=False
            ).values_list("user_id", flat=True)
            valid_user_ids.update(workspace_members)

        if task_board.group:
            group_members = GroupMember.objects.filter(
                group=task_board.group, is_banned=False
            ).values_list("user_id", flat=True)
            valid_user_ids.update(group_members)

        # Validate each assigned user is a member
        for user in value:
            if user.id not in valid_user_ids:
                raise serializers.ValidationError(
                    f"{user.username} is not a member of this workspace/group"
                )

        return value


class TaskAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = [
            "id",
            "task",
            "assigned_to",
            "assigned_by",
            "assigned_at",
            "status",
            "notes",
        ]

        read_only_fields = ["id", "assigned_at", "assigned_by"]
