from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from workspace.models import Workspace, SpaceMember
from group.models import Group, GroupMember
from .models import Channel
from .serializers import ChannelSerializer


class CreateChannelView(generics.CreateAPIView):
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Get workspace_id or group_id from request data
        workspace_id = request.data.get("workspace")
        group_id = request.data.get("group")

        # Validate that exactly one parent is specified
        if not workspace_id and not group_id:
            return Response(
                {"detail": "Either workspace or group must be specified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if workspace_id and group_id:
            return Response(
                {"detail": "Channel cannot belong to both workspace and group"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check permissions and parent existence
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                # Verify user is a member of the workspace
                if not SpaceMember.objects.filter(
                    workspace=workspace, user=request.user, is_banned=False
                ).exists():
                    return Response(
                        {
                            "detail": "You must be a member of the workspace to create a channel"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Workspace.DoesNotExist:
                return Response(
                    {"detail": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
                )

        if group_id:
            try:
                group = Group.objects.get(id=group_id)
                # Verify user is a member of the group
                if not GroupMember.objects.filter(
                    group=group, user=request.user, is_banned=False
                ).exists():
                    return Response(
                        {
                            "detail": "You must be a member of the group to create a channel"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Group.DoesNotExist:
                return Response(
                    {"detail": "Group not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Create the channel
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel = serializer.save(created_by=request.user)

        # Update channel count
        if workspace_id:
            workspace.channel_count += 1
            workspace.save(update_fields=["channel_count"])
        elif group_id:
            group.channel_count += 1
            group.save(update_fields=["channel_count"])

        return Response(
            self.get_serializer(channel).data, status=status.HTTP_201_CREATED
        )


class ChannelList(generics.ListAPIView):
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get optional filters from query params
        workspace_id = self.request.query_params.get("workspace")
        group_id = self.request.query_params.get("group")

        # Start with all channels where user is a member
        queryset = Channel.objects.all()

        # Filter by workspace if specified
        if workspace_id:
            queryset = queryset.filter(
                workspace_id=workspace_id,
                workspace__members__user=self.request.user,
                workspace__members__is_banned=False,
            )

        # Filter by group if specified
        if group_id:
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
