from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import Workspace, SpaceMember
from .serializers import WorkspaceSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# Create your views here.

def home(request):
    return render(request, 'home.html')


class WorkspaceList(generics.ListCreateAPIView):
    queryset = Workspace.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

    def get(self, request, *args, **kwargs):
        workspaces = Workspace.objects.filter(members__user=request.user)
        serializer = WorkspaceSerializer(workspaces, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = WorkspaceSerializer(data=request.data)
        if serializer.is_valid():
            workspace = serializer.save()
            SpaceMember.objects.create(user=request.user, workspace=workspace, role='admin')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)