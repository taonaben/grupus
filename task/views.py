from django.shortcuts import render
import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.views import APIView
from .models import TaskBoard, TaskList, Task, TaskAssignment
from .serializers import TaskBoardSerializer, TaskListSerializer, TaskSerializer
from workspace.models import Workspace, SpaceMember
from group.models import Group, GroupMember
from user.models import User
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination

logger = logging.getLogger(__name__)


# * T A S K B O A R D   V I E W S
class CreateTaskBoardView(generics.CreateAPIView):
    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_board = serializer.save(created_by=request.user)

        return Response(
            self.get_serializer(task_board).data, status=status.HTTP_201_CREATED
        )


class TaskBoardList(generics.ListAPIView):
    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workspace_id = self.request.query_params.get("workspace_id")
        group_id = self.request.query_params.get("group_id")

        logger.info(f"workspace_id: {workspace_id}")
        logger.info(f"group_id: {group_id}")

        queryset = TaskBoard.objects.all()

        if workspace_id:
            logger.info("found workspace id in params")
            queryset = queryset.filter(
                workspace_id=workspace_id,
                workspace__members__user=self.request.user,
                workspace__members__is_banned=False,
            )

        if group_id:
            logger.info("found group id in params")

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


#! T A S K L I S T   V I E W S


class CreateTaskListView(generics.CreateAPIView):
    queryset = TaskList.objects.all()
    serializer_class = TaskListSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        board_id = request.data.get("task_board_id") or request.data.get("board_id")

        if not board_id:
            return Response(
                {"error": "task_board_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not TaskBoard.objects.filter(id=board_id).exists():
            return Response(
                {"error": "TaskBoard does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_list = serializer.save(task_board_id=board_id)

        return Response(
            self.get_serializer(task_list).data, status=status.HTTP_201_CREATED
        )


class TaskListList(generics.ListAPIView):
    queryset = TaskList.objects.all()
    serializer_class = TaskListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_board_id = self.request.query_params.get("task_board_id")

        logger.info(f"task_board_id: {task_board_id}")

        queryset = TaskList.objects.all()

        if task_board_id:
            logger.info("found task_board id in params")
            queryset = queryset.filter(
                task_board_id=task_board_id,
            )

        return (
            queryset.select_related("task_board", "task_board__created_by")
            .distinct()
            .order_by("position")
        )


class ChangeTaskListPosition(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, task_board_id):
        """
        Change position of a TaskList and reorder others efficiently.

        Request body:
        {
            "task_list_id": "uuid",
            "new_position": 2
        }
        """
        task_list_id = request.data.get("task_list_id")
        new_position = request.data.get("new_position")

        # Validate inputs
        if not task_list_id or new_position is None:
            return Response(
                {"error": "task_list_id and new_position are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_position = int(new_position)
            if new_position < 1:
                raise ValueError("Position must be >= 1")
        except (ValueError, TypeError):
            return Response(
                {"error": "new_position must be a valid integer >= 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_list = TaskList.objects.get(
                id=task_list_id, task_board_id=task_board_id
            )
        except TaskList.DoesNotExist:
            return Response(
                {"error": "TaskList not found in this board."},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_position = task_list.position

        # If position hasn't changed, return early
        if old_position == new_position:
            return Response(
                TaskListSerializer(task_list).data,
                status=status.HTTP_200_OK,
            )

        # Get all task lists in the board for reordering
        all_lists = list(
            TaskList.objects.filter(task_board_id=task_board_id).order_by("position")
        )

        # Remove the moving list from the array
        all_lists = [tl for tl in all_lists if tl.id != task_list_id]

        # Insert it at the new position (adjust for 0-based indexing)
        all_lists.insert(new_position - 1, task_list)

        # Bulk update positions efficiently
        for idx, tl in enumerate(all_lists, start=1):
            tl.position = idx

        # Use bulk_update for efficiency
        TaskList.objects.bulk_update(all_lists, ["position"], batch_size=100)

        return Response(
            TaskListSerializer(task_list).data,
            status=status.HTTP_200_OK,
        )


# ? T A S K C A R D   V I E W S
class CreateTaskView(generics.CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):

        task_list_id = request.data.get("task_list")

        if task_list_id is None:
            return Response(
                {"error": "TaskList ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not TaskList.objects.filter(id=task_list_id).exists():
            return Response(
                {"error": "TaskList does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_list = TaskList.objects.get(id=task_list_id)
            task_board = task_list.task_board

            # # Check permission: user must be member of workspace OR group
            # has_workspace_access = (
            #     task_board.workspace
            #     and SpaceMember.objects.filter(
            #         workspace=task_board.workspace,
            #         user=request.user,
            #         is_banned=False,
            #     ).exists()
            # )
            # has_group_access = (
            #     task_board.group
            #     and GroupMember.objects.filter(
            #         group=task_board.group,
            #         user=request.user,
            #         is_banned=False,
            #     ).exists()
            # )

            # if not (has_workspace_access or has_group_access):
            #     return Response(
            #         {
            #             "error": "You do not have permission to add tasks to this TaskList."
            #         },
            #         status=status.HTTP_403_FORBIDDEN,
            #     )

        except TaskList.DoesNotExist:
            return Response(
                {"error": "TaskList does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract assigned_to from request before serializer validation
        assigned_to_ids = request.data.get("assigned_to", [])
        if assigned_to_ids is None:
            assigned_to_ids = []

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save()

        # Create TaskAssignment records for each assigned user
        if assigned_to_ids:
            for user_id in assigned_to_ids:
                try:
                    user = User.objects.get(id=user_id)
                    TaskAssignment.objects.create(
                        task=task,
                        assigned_to=user,
                        assigned_by=request.user,
                    )
                except User.DoesNotExist:
                    # If user doesn't exist, continue without assigning
                    logger.warning(f"User {user_id} does not exist for task assignment")
                    continue

        return Response(self.get_serializer(task).data, status=status.HTTP_201_CREATED)


class TaskCardList(generics.ListAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_list_id = self.request.query_params.get("task_list_id")

        logger.info(f"task_list_id: {task_list_id}")

        queryset = Task.objects.all()

        if task_list_id:
            logger.info("found task_list id in params")
            queryset = queryset.filter(
                task_list_id=task_list_id,
            )

        return (
            queryset.select_related("task_list", "created_by")
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
        return Response(serializer.data, status=status.HTTP_200)


class GetTaskBoardMembersView(generics.GenericAPIView):
    """Get all members available for assignment in a task board"""

    permission_classes = [IsAuthenticated]

    def get(self, request, task_board_id, *args, **kwargs):
        try:
            task_board = TaskBoard.objects.get(id=task_board_id)
        except TaskBoard.DoesNotExist:
            return Response(
                {"error": "TaskBoard not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get members from workspace or group
        members = []

        if task_board.workspace:
            workspace_members = SpaceMember.objects.filter(
                workspace=task_board.workspace, is_banned=False
            ).select_related("user")

            for member in workspace_members:
                members.append(
                    {
                        "id": member.user.id,
                        "username": member.user.username,
                        "email": member.user.email,
                        "role": member.role,
                        "joined_at": member.joined_at,
                    }
                )

        if task_board.group:
            group_members = GroupMember.objects.filter(
                group=task_board.group, is_banned=False
            ).select_related("user")

            for member in group_members:
                members.append(
                    {
                        "id": member.user.id,
                        "username": member.user.username,
                        "email": member.user.email,
                        "role": member.role,
                        "joined_at": member.joined_at,
                    }
                )

        return Response(
            {"members": members, "total": len(members)}, status=status.HTTP_200_OK
        )
