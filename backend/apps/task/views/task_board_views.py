from django.shortcuts import render
import logging
import uuid
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView

from apps.group.models import GroupMember
from apps.workspace.models import SpaceMember
from ..models import TaskBoard
from ..serializers import TaskBoardSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from drf_spectacular.utils import extend_schema, extend_schema_view


logger = logging.getLogger(__name__)


# * T A S K B O A R D   V I E W S
@extend_schema_view(
    list=extend_schema(summary="List Boards in space or group"),
    create=extend_schema(summary="Create a task board"),
    retrieve=extend_schema(summary="Get task board details"),
    update=extend_schema(summary="Update task board"),
    partial_update=extend_schema(summary="Partially update task board"),
    destroy=extend_schema(summary="Delete task board"),
)
class TaskBoardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task boards in workspaces or groups
    """

    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return TaskBoard.objects.none()

        workspace_id = self.request.query_params.get("workspace_id")
        group_id = self.request.query_params.get("group_id")

        logger.info(f"workspace_id: {workspace_id}")
        logger.info(f"group_id: {group_id}")

        queryset = TaskBoard.objects.all()

        if workspace_id:
            logger.info("found workspace id in params")
            queryset = queryset.filter(
                workspace_id=workspace_id,
                workspace__members__user=self.request.user,
                workspace__members__is_banned=False,
            )

        if group_id:
            logger.info("found group id in params")

            queryset = queryset.filter(
                group_id=group_id,
                group__members__user=self.request.user,
                group__members__is_banned=False,
            )

        return (
            queryset.select_related("workspace", "group", "created_by")
            .distinct()
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_board = serializer.save(created_by=request.user)

        return Response(
            self.get_serializer(task_board).data, status=status.HTTP_201_CREATED
        )

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
    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, id=None):
        """Get all members available for assignment in a task board"""
        try:
            task_board = self.get_object()
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
