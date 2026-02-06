import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.workspace.models import Workspace, SpaceMember
from .models import Channel
from .serializers import ChannelSerializer

logger = logging.getLogger(__name__)


class ChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workspace_id = self.request.query_params.get("workspace_id")

        logger.info(f"workspace_id: {workspace_id}")

        queryset = Channel.objects.all()

        # Filter by workspace if specified
        if workspace_id:
            logger.info("found workspace id in params")
            queryset = queryset.filter(
                workspace_id=workspace_id,
                workspace__members__user=self.request.user,
                workspace__members__is_banned=False,
            )

        return (
            queryset.select_related("workspace", "created_by")
            .distinct()
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        workspace_id = request.data.get("workspace_id")
        is_user_admin =  SpaceMember.objects.filter(
            workspace_id=workspace_id, user=request.user, role=SpaceMember.Role.ADMIN).exists()

        if not workspace_id:
            return Response(
                {"detail": "Workspace must be specified"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        

        # Check permissions and parent existence
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                # Verify user is a member of the workspace
                if not SpaceMember.objects.filter(
                    workspace=workspace, user=request.user, is_banned=False, 
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

        if not is_user_admin:
            return Response(
                {"detail": "Only workspace admins can create channels"},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel = serializer.save(created_by=request.user)

        # Update channel count
        if workspace_id:
            workspace.channel_count += 1
            workspace.save(update_fields=["channel_count"])

        return Response(
            self.get_serializer(channel).data, status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
