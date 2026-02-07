import os
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from ..models import WorkspaceType
from ..serializers import WorkspaceTypeSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.environ.get("DEBUG", "0") == "1"


class WorkspaceTypeViewSet(viewsets.ModelViewSet):
    queryset = WorkspaceType.objects.all()
    serializer_class = WorkspaceTypeSerializer
    if DEBUG:
        permission_classes = [IsAuthenticated]
    else:
        permission_classes = [IsAdminUser]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return WorkspaceType.objects.none()

        return WorkspaceType.objects.all().order_by("name")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
