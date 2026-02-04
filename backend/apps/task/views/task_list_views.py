from django.shortcuts import render
import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.views import APIView
from ..models import TaskBoard, TaskList, Task, TaskAssignment
from ..serializers import TaskListSerializer, TaskSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from drf_spectacular.utils import extend_schema


logger = logging.getLogger(__name__)


#! T A S K L I S T   V I E W S


@extend_schema(
    summary="Create a task list",
    description="""Creates a new task list inside a group workspace. 
    The authenticated user becomes the creator.
    This list will contain tasks that are either pending, done or binned, depending""",
    request=TaskListSerializer,
    responses={201: TaskListSerializer},
)
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


@extend_schema(
    summary="Change task list position",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "task_list_id": {"type": "string", "format": "uuid"},
                "new_position": {"type": "integer", "minimum": 1},
            },
            "required": ["task_list_id", "new_position"],
        }
    },
    responses={200: TaskListSerializer},
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
