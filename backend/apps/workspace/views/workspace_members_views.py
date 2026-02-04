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


class SpaceMemberViewSet(viewsets.ModelViewSet):
    serializer_class = SpaceMemberSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return SpaceMember.objects.none()

        workspace_id = self.request.query_params.get("workspace_id")
        if workspace_id:
            return (
                SpaceMember.objects.filter(
                    workspace__id=workspace_id,
                    is_banned=False,
                )
                .select_related("user")
                .order_by("-joined_at")
            )

        # Return members of workspaces the user belongs to
        return (
            SpaceMember.objects.filter(
                workspace__members__user=self.request.user,
                is_banned=False,
            )
            .select_related("user")
            .order_by("-joined_at")
            .distinct()
        )

    @action(detail=False, methods=["post"], url_path="join/(?P<access_code>[^/.]+)")
    def join(self, request, access_code=None):
        """Join a workspace using an access code"""
        if not access_code:
            return Response(
                {"detail": "Access code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            workspace = Workspace.objects.get(access_code=access_code)
        except Workspace.DoesNotExist:
            return Response(
                {"detail": "Invalid access code"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is already a member
        if SpaceMember.objects.filter(workspace=workspace, user=request.user).exists():
            return Response(
                {"detail": "You are already a member of this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if workspace.member_count >= workspace.max_members:
            return Response(
                {"detail": "This workspace has reached its maximum member limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create the space member
        space_member = serializer.save(
            user=request.user, workspace=workspace, role=SpaceMember.Role.MEMBER
        )

        # Update the member count
        workspace.member_count += 1
        workspace.save(update_fields=["member_count"])

        return Response(
            self.get_serializer(space_member).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["delete", "post"],
        url_path="leave/(?P<workspace_id>[^/.]+)",
    )
    def leave(self, request, workspace_id=None):
        """Leave a workspace"""
        if not workspace_id:
            return Response(
                {"detail": "Workspace ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            space_member = SpaceMember.objects.get(
                workspace__id=workspace_id, user=request.user
            )
        except SpaceMember.DoesNotExist:
            return Response(
                {"detail": "You are not a member of this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        workspace = space_member.workspace
        space_member.delete()

        if workspace.member_count > 0:
            workspace.member_count -= 1
            workspace.save(update_fields=["member_count"])

        return Response(
            {"detail": "You have left the workspace."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="list/(?P<workspace_id>[^/.]+)")
    def list_by_workspace(self, request, workspace_id=None):
        """List all members of a specific workspace"""
        if not workspace_id:
            return Response(
                {"detail": "Workspace ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            SpaceMember.objects.filter(
                workspace__id=workspace_id,
                is_banned=False,
            )
            .select_related("user")
            .order_by("-joined_at")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
