from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from ..models import Workspace, SpaceMember
from apps.task.models import TaskBoard, TaskList
from ..serializers import WorkspaceSerializer, SpaceMemberSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination


class CustomCursorPagination(CursorPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class WorkspaceViewSet(viewsets.ModelViewSet):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return Workspace.objects.none()

        return (
            Workspace.objects.filter(
                members__user=self.request.user,
                members__is_banned=False,
            )
            .select_related("created_by")
            .prefetch_related("members")
            .distinct()
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workspace = serializer.save(created_by=request.user)

        SpaceMember.objects.create(
            user=request.user,
            workspace=workspace,
            role=SpaceMember.Role.ADMIN,  # Using the enum from model
        )

        workspace.member_count = 1
        workspace.save(update_fields=["member_count"])

        return Response(
            self.get_serializer(workspace).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        workspace = self.get_object()
        # TODO make sure admins and moderators of the "groups" can update
        if workspace.created_by != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to update this workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        workspace = self.get_object()
        # TODO make sure admins and moderators of the "groups" can update
        if workspace.created_by != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to update this workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)
