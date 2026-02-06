from django.shortcuts import render
import logging
import uuid
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from ..models import TaskBoard, TaskList, Task, TaskAssignment
from ..serializers import TaskBoardSerializer, TaskListSerializer, TaskSerializer
from apps.workspace.models import Workspace, SpaceMember
from apps.group.models import Group, GroupMember
from apps.user.models import User
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)


# ? T A S K C A R D   V I E W S
@extend_schema_view(
    list=extend_schema(summary="List tasks"),
    create=extend_schema(
        summary="Create a task",
        description="""Create a new task with optional user/group assignments
        
        Example assigned_to format:
       
        [
            {
                "type": "user",
                "id": "user-uuid-here"
            },
            {
                "type": "group",
                "id": "group-uuid-here"
            },
        ]
        \n\n
        """,
    ),
    retrieve=extend_schema(summary="Get task details"),
    update=extend_schema(summary="Update task"),
    partial_update=extend_schema(summary="Partially update task"),
    destroy=extend_schema(summary="Delete task"),
)
class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tasks (cards) within task lists
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return Task.objects.none()

        task_list_id = self.request.query_params.get("task_list_id")

        logger.info(f"task_list_id: {task_list_id}")

        queryset = Task.objects.all()

        if task_list_id:
            logger.info("found task_list id in params")
            queryset = queryset.filter(
                task_list_id=task_list_id,
            )

        return (
            queryset.select_related("task_list", "created_by")
            .prefetch_related("assignments", "assignments__content_type")
            .distinct()
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        task_list_id = request.data.get("task_list")

        if task_list_id is None:
            return Response(
                {"error": "TaskList ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not TaskList.objects.filter(id=task_list_id).exists():
            return Response(
                {"error": "TaskList does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_list = TaskList.objects.get(id=task_list_id)
            task_board = task_list.task_board

        except TaskList.DoesNotExist:
            return Response(
                {"error": "TaskList does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract assigned_to from request before serializer validation
        assigned_to_data = request.data.get("assigned_to", [])
        if assigned_to_data is None:
            assigned_to_data = []

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save()

        # Create TaskAssignment records for each assigned user/group
        if assigned_to_data:
            self._create_assignments(task, assigned_to_data, request.user)

        return Response(self.get_serializer(task).data, status=status.HTTP_201_CREATED)

    def _create_assignments(self, task, assigned_to_data, assigned_by_user):
        """Helper method to create task assignments efficiently"""
        for assignment in assigned_to_data:
            assignment_type = assignment.get("type")
            assignment_id = assignment.get("id")

            try:
                if assignment_type == "user":
                    user = User.objects.get(id=assignment_id)
                    content_type = ContentType.objects.get_for_model(User)
                    TaskAssignment.objects.create(
                        task=task,
                        content_type=content_type,
                        object_id=user.id,
                        assigned_by=assigned_by_user,
                    )
                elif assignment_type == "group":
                    group = Group.objects.get(id=assignment_id)
                    content_type = ContentType.objects.get_for_model(Group)
                    TaskAssignment.objects.create(
                        task=task,
                        content_type=content_type,
                        object_id=group.id,
                        assigned_by=assigned_by_user,
                    )
                else:
                    logger.warning(f"Invalid assignment type: {assignment_type}")
            except (User.DoesNotExist, Group.DoesNotExist) as e:
                logger.warning(f"Assignment target not found: {e}")
                continue

    @extend_schema(
        summary="Assign task to users or groups",
        description="Add new assignments to an existing task",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "assigned_to": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["user", "group"]},
                                "id": {"type": "string", "format": "uuid"},
                            },
                        },
                    },
                },
                "required": ["assigned_to"],
            }
        },
    )
    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, id=None):
        """Assign task to additional users or groups"""
        task = self.get_object()
        assigned_to_data = request.data.get("assigned_to", [])

        if not assigned_to_data:
            return Response(
                {"error": "assigned_to is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        self._create_assignments(task, assigned_to_data, request.user)

        return Response(
            self.get_serializer(task).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get task assignments",
        description="Get all users and groups assigned to a task",
    )
    @action(detail=True, methods=["get"], url_path="assignments")
    def assignments(self, request, id=None):
        """Get all assignments for a task"""
        task = self.get_object()
        assignments = TaskAssignment.objects.filter(task=task).select_related(
            "content_type", "assigned_by"
        )

        assignment_data = []
        for assignment in assignments:
            assignment_data.append(
                {
                    "id": assignment.id,
                    "type": assignment.content_type.model,
                    "object_id": assignment.object_id,
                    "assigned_by": {
                        "id": assignment.assigned_by.id,
                        "username": assignment.assigned_by.username,
                    },
                    "assigned_at": assignment.assigned_at,
                }
            )

        return Response(
            {"assignments": assignment_data, "total": len(assignment_data)},
            status=status.HTTP_200_OK,
        )

        # Extract assigned_to from request before serializer validation
        assigned_to_data = request.data.get("assigned_to", [])
        if assigned_to_data is None:
            assigned_to_data = []

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save()

        # Create TaskAssignment records for each assigned user/group
        from django.contrib.contenttypes.models import ContentType

        if assigned_to_data:
            for assignment in assigned_to_data:
                assignment_type = assignment.get("type")
                assignment_id = assignment.get("id")

                try:
                    if assignment_type == "user":
                        user = User.objects.get(id=assignment_id)
                        content_type = ContentType.objects.get_for_model(User)
                        TaskAssignment.objects.create(
                            task=task,
                            content_type=content_type,
                            object_id=user.id,
                            assigned_by=request.user,
                        )
                    elif assignment_type == "group":
                        group = Group.objects.get(id=assignment_id)
                        content_type = ContentType.objects.get_for_model(Group)
                        TaskAssignment.objects.create(
                            task=task,
                            content_type=content_type,
                            object_id=group.id,
                            assigned_by=request.user,
                        )
                    else:
                        logger.warning(f"Invalid assignment type: {assignment_type}")
                except (User.DoesNotExist, Group.DoesNotExist) as e:
                    logger.warning(f"Assignment target not found: {e}")
                    continue

        return Response(self.get_serializer(task).data, status=status.HTTP_201_CREATED)
