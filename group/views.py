from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import Group, GroupMember
from .serializers import GroupSerializer, GroupMemberSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser


class CreateGroupView(generics.CreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

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


class GroupList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    # pagination_class = CustomCursorPagination

    def get_queryset(self):
        workspace_id = self.request.query_params.get("workspace_id")
        queryset = Group.objects.filter(
            members__user=self.request.user,
            members__is_banned=False,  # Exclude if user is banned
        )

        # Filter by workspace if specified
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        return (
            queryset.select_related(
                "created_by", "workspace"
            )  # Optimize by pre-fetching related user and workspace
            .prefetch_related("members")  # Optimize by pre-fetching members
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
        return Response(serializer.data, status=status.HTTP_200_OK)


# ------- G R O U P   M E M B E R S   V I E W S ----------

# class CreateGroupMemberView(generics.CreateAPIView):
#     queryset = GroupMember.objects.all()
#     serializer_class = GroupMemberSerializer
#     permission_classes = [IsAuthenticated]

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         # Create the group member with the current user as creator
#         group_member = serializer.save()

#         return Response(
#             self.get_serializer(group_member).data, status=status.HTTP_201_CREATED
#         )
