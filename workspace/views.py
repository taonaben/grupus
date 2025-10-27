from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import Workspace, SpaceMember
from .serializers import WorkspaceSerializer
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
        workspace = serializer.save(created_by=request.user)

        response = super().create(request, *args, **kwargs)
        SpaceMember.objects.create(user=request.user, workspace=workspace, role="admin")

        return response


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

    # def post(self, request, *args, **kwargs):
    #     serializer = WorkspaceSerializer(data=request.data)
    #     permission_classes = [IsAuthenticated]
    #     if serializer.is_valid():
    #         workspace = serializer.save()
    #         SpaceMember.objects.create(
    #             user=request.user, workspace=workspace, role="admin"
    #         )
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
