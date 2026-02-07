from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from ..models import Group, GroupMember
from apps.workspace.models import Workspace
from apps.task.models import TaskBoard, TaskList
from ..serializers import GroupSerializer, GroupMemberSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return Group.objects.none()

        queryset = Group.objects.filter(
            members__user=self.request.user,
            members__is_banned=False,  # Exclude if user is banned
        )

        return (
            queryset.select_related(
                "created_by", "workspace"
            )  # Optimize by pre-fetching related user and workspace
            .prefetch_related("members")  # Optimize by pre-fetching members
            .distinct()
            .order_by("-created_at")
        )

    @action(
        detail=False, methods=["get"], url_path="workspace/(?P<workspace_id>[^/.]+)"
    )
    def workspace_groups(self, workspace_id):
        """Return groups within a specific workspace the user belongs to"""
        return (
            Group.objects.filter(
                workspace__id=workspace_id,
                members__user=self.request.user,
                members__is_banned=False,
            )
            .select_related("created_by", "workspace")
            .prefetch_related("members")
            .distinct()
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if this is being created within a workspace
        workspace_id = self.kwargs.get("workspace_id")
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                # Check if user is a member of the workspace
                if not workspace.members.filter(
                    user=request.user, is_banned=False
                ).exists():
                    return Response(
                        {
                            "detail": "You must be a member of the workspace to create a group."
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Workspace.DoesNotExist:
                return Response(
                    {"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            workspace = None

        # Create the group
        group = serializer.save(created_by=request.user, workspace=workspace)

        # Make creator an admin member
        GroupMember.objects.create(
            user=request.user, group=group, role=GroupMember.Role.ADMIN
        )

        # Update member count
        group.member_count = 1
        group.save(update_fields=["member_count"])

        return Response(self.get_serializer(group).data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="workspace/(?P<workspace_id>[^/.]+)/create",
    )
    def create_in_workspace(self, request, workspace_id=None):
        """Create a group within a specific workspace"""
        self.kwargs["workspace_id"] = workspace_id
        return self.create(request)

    def update(self, request, *args, **kwargs):
        group = self.get_object()

        if group.created_by != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to update this group."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        group = self.get_object()

        if group.created_by != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to update this group."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().partial_update(request, *args, **kwargs)
