from .models import TaskBoard, TaskList, Task, TaskAssignment
from rest_framework import serializers
from workspace.models import SpaceMember
from group.models import GroupMember


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

        read_only_fields = ["id", "created_at", "updated_at"]

        def validate_assigned_to(self, value):
            """Ensuring assigned users are members of the workspace/group"""
            task_list = self.instance.task_list if self.instance else None
            task_board = task_list.task_board if task_list else None

            if task_board.workspace:
                for user in value:
                    if not SpaceMember.objects.filter(
                        workspace=task_board.workspace, user=user, is_banned=False
                    ).exists():
                        raise serializers.ValidationError(
                            f"{user.username} is not a member of this workspace"
                        )

            elif task_board.group:
                for user in value:
                    if not GroupMember.objects.filter(
                        group=task_board.group, user=user, is_banned=False
                    ).exists():
                        raise serializers.ValidationError(
                            f"{user.username} is not a member of this group"
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