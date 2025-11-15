from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import TaskBoard, TaskList, Task
from .serializers import TaskBoardSerializer, TaskListSerializer, TaskSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination


# Create your views here.
