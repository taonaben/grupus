from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import Workspace, SpaceMember
from .serializers import WorkspaceSerializer, SpaceMemberSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination


class CustomCursorPagination(CursorPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CreateWorkspaceView(generics.CreateAPIView):
    queryset = Workspace.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create the workspace with the current user as creator
        workspace = serializer.save(created_by=request.user)

        # Create the space membership for the creator as admin
        SpaceMember.objects.create(
            user=request.user,
            workspace=workspace,
            role=SpaceMember.Role.ADMIN,  # Using the enum from model
        )

        # Update the member count
        workspace.member_count = 1
        workspace.save(update_fields=["member_count"])

        return Response(
            self.get_serializer(workspace).data, status=status.HTTP_201_CREATED
        )


class WorkspaceList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer
    # pagination_class = CustomCursorPagination

    def get_queryset(self):
        # Get all workspaces where the user is a member through SpaceMember
        return (
            Workspace.objects.filter(
                members__user=self.request.user,
                members__is_banned=False,  # Exclude if user is banned
            )
            .select_related("created_by")  # Optimize by pre-fetching related user
            .prefetch_related("members")  # Optimize by pre-fetching members
            .distinct()  # Avoid duplicates
            .order_by("-created_at")  # Most recent first
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkspaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Workspace.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer
    lookup_field = "id"

    def delete(self, request, *args, **kwargs):
        workspace = self.get_object()
        # TODO make sure admins of the "groups" can delete
        if workspace.created_by != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to delete this workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        workspace = self.get_object()
        # TODO make sure admins and moderators of the "groups" can update
        if workspace.created_by != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to update this workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


# ---------- W O R K S P A C E   M E M B E R S   V I E W S ----------


class CreateSpaceMemberView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceMemberSerializer
    lookup_field = "access_code"

    def create(self, request, *args, **kwargs):
        access_code = self.kwargs.get("access_code")
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


class SpaceMembersList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceMemberSerializer
    lookup_field = "workspace_id"

    def get_queryset(self):
        workspace_id = self.kwargs.get("workspace_id")
        return (
            SpaceMember.objects.filter(
                workspace__id=workspace_id,
                is_banned=False,
            )
            .select_related("user")
            .order_by("-joined_at")
        )

    def list(self, request, *args, **kwargs):

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
