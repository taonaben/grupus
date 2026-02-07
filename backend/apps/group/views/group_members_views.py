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


class GroupMemberViewSet(viewsets.ModelViewSet):
    serializer_class = GroupMemberSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return GroupMember.objects.none()

        group_id = self.request.query_params.get("group_id")
        if group_id:
            return (
                GroupMember.objects.filter(group__id=group_id, is_banned=False)
                .select_related("user")
                .order_by("-joined_at")
            )

        # Return members of groups the user belongs to
        return (
            GroupMember.objects.filter(
                group__members__user=self.request.user, is_banned=False
            )
            .select_related("user")
            .order_by("-joined_at")
            .distinct()
        )

    @action(detail=False, methods=["post"], url_path="join/(?P<access_code>[^/.]+)")
    def join(self, request, access_code=None):
        """Join a group using an access code"""
        if not access_code:
            return Response(
                {"detail": "Access code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group = Group.objects.get(access_code=access_code)
        except Group.DoesNotExist:
            return Response(
                {"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if GroupMember.objects.filter(user=request.user, group=group).exists():
            return Response(
                {"detail": "You are already a member of this group."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if group.member_count >= group.max_members:
            return Response(
                {"detail": "This group has reached its member limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_member = serializer.save(
            user=request.user,
            group=group,
            role=GroupMember.Role.MEMBER,
        )

        group.member_count += 1
        group.save(update_fields=["member_count"])

        return Response(
            self.get_serializer(group_member).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False, methods=["delete", "post"], url_path="leave/(?P<group_id>[^/.]+)"
    )
    def leave(self, request, group_id=None):
        """Leave a group"""
        if not group_id:
            return Response(
                {"detail": "Group ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group_member = GroupMember.objects.get(
                group__id=group_id,
                user=request.user,
            )
        except GroupMember.DoesNotExist:
            return Response(
                {"detail": "You are not a member of this group."},
                status=status.HTTP_404_NOT_FOUND,
            )

        group = group_member.group
        group_member.delete()

        # Decrement member count
        group.member_count = max(0, group.member_count - 1)
        group.save(update_fields=["member_count"])

        return Response(
            {"detail": "You have left the group."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="list/(?P<group_id>[^/.]+)")
    def list_by_group(self, request, group_id=None):
        """List all members of a specific group"""
        if not group_id:
            return Response(
                {"detail": "Group ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            GroupMember.objects.filter(group__id=group_id, is_banned=False)
            .select_related("user")
            .order_by("-joined_at")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
