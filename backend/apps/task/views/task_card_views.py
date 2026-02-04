from django.shortcuts import render
import logging
import uuid
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.views import APIView
from ..models import TaskBoard, TaskList, Task, TaskAssignment
from ..serializers import TaskBoardSerializer, TaskListSerializer, TaskSerializer
from apps.workspace.models import Workspace, SpaceMember
from apps.group.models import Group, GroupMember
from apps.user.models import User
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from drf_spectacular.utils import extend_schema


logger = logging.getLogger(__name__)


# ? T A S K C A R D   V I E W S
class CreateTaskView(generics.CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

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

            # # Check permission: user must be member of workspace OR group
            # has_workspace_access = (
            #     task_board.workspace
            #     and SpaceMember.objects.filter(
            #         workspace=task_board.workspace,
            #         user=request.user,
            #         is_banned=False,
            #     ).exists()
            # )
            # has_group_access = (
            #     task_board.group
            #     and GroupMember.objects.filter(
            #         group=task_board.group,
            #         user=request.user,
            #         is_banned=False,
            #     ).exists()
            # )

            # if not (has_workspace_access or has_group_access):
            #     return Response(
            #         {
            #             "error": "You do not have permission to add tasks to this TaskList."
            #         },
            #         status=status.HTTP_403_FORBIDDEN,
            #     )

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


class TaskCardList(generics.ListAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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
            .distinct()
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200)


@extend_schema(
    summary="Get task board members",
    description="Get all members available for assignment in a task board",
    responses={
        200: {
            "type": "object",
            "properties": {
                "members": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "username": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "role": {"type": "string"},
                            "joined_at": {"type": "string", "format": "date-time"},
                        },
                    },
                },
                "total": {"type": "integer"},
            },
        }
    },
)
class GetTaskBoardMembersView(generics.GenericAPIView):
    """Get all members available for assignment in a task board"""

    permission_classes = [IsAuthenticated]

    def get(self, request, task_board_id, *args, **kwargs):
        try:
            task_board = TaskBoard.objects.get(id=task_board_id)
        except TaskBoard.DoesNotExist:
            return Response(
                {"error": "TaskBoard not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get members from workspace or group
        members = []

        if task_board.workspace:
            workspace_members = SpaceMember.objects.filter(
                workspace=task_board.workspace, is_banned=False
            ).select_related("user")

            for member in workspace_members:
                members.append(
                    {
                        "id": member.user.id,
                        "username": member.user.username,
                        "email": member.user.email,
                        "role": member.role,
                        "joined_at": member.joined_at,
                    }
                )

        if task_board.group:
            group_members = GroupMember.objects.filter(
                group=task_board.group, is_banned=False
            ).select_related("user")

            for member in group_members:
                members.append(
                    {
                        "id": member.user.id,
                        "username": member.user.username,
                        "email": member.user.email,
                        "role": member.role,
                        "joined_at": member.joined_at,
                    }
                )

        return Response(
            {"members": members, "total": len(members)}, status=status.HTTP_200_OK
        )
