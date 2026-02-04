from django.shortcuts import render
import logging
import uuid
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.views import APIView
from ..models import TaskBoard
from ..serializers import TaskBoardSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from drf_spectacular.utils import extend_schema


logger = logging.getLogger(__name__)


# * T A S K B O A R D   V I E W S
class CreateTaskBoardView(generics.CreateAPIView):
    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_board = serializer.save(created_by=request.user)

        return Response(
            self.get_serializer(task_board).data, status=status.HTTP_201_CREATED
        )


@extend_schema(summary="List Boards in space or group")
class TaskBoardList(generics.ListAPIView):
    """
    List of all the boards in a workspace or group
    """

    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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
