from django.shortcuts import render
import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from ..models import TaskBoard, TaskList, Task, TaskAssignment
from ..serializers import TaskListSerializer, TaskSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination, CursorPagination
from drf_spectacular.utils import extend_schema, extend_schema_view


logger = logging.getLogger(__name__)


#! T A S K L I S T   V I E W S

@extend_schema_view(
    list=extend_schema(summary="List task lists"),
    create=extend_schema(
        summary="Create a task list",
        description="""Creates a new task list inside a group workspace. 
        The authenticated user becomes the creator.
        This list will contain tasks that are either pending, done or binned, depending""",
    ),
    retrieve=extend_schema(summary="Get task list details"),
    update=extend_schema(summary="Update task list"),
    partial_update=extend_schema(summary="Partially update task list"),
    destroy=extend_schema(summary="Delete task list"),
)
class TaskListViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task lists within task boards
    """

    queryset = TaskList.objects.all()
    serializer_class = TaskListSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Return empty queryset for schema generation
        if getattr(self, "swagger_fake_view", False):
            return TaskList.objects.none()

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

    @extend_schema(
        summary="Change task list position",
        description="Reorder task lists within a board by changing position",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "new_position": {"type": "integer", "minimum": 1},
                },
                "required": ["new_position"],
            }
        },
        responses={200: TaskListSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="reorder")
    def reorder(self, request, id=None):
        """
        Change position of a TaskList and reorder others efficiently.

        Request body:
        {
            "new_position": 2
        }
        """
        new_position = request.data.get("new_position")

        # Validate inputs
        if new_position is None:
            return Response(
                {"error": "new_position is required."},
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
            task_list = self.get_object()
        except TaskList.DoesNotExist:
            return Response(
                {"error": "TaskList not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_position = task_list.position
        task_board_id = task_list.task_board_id

        # If position hasn't changed, return early
        if old_position == new_position:
            return Response(
                self.get_serializer(task_list).data,
                status=status.HTTP_200_OK,
            )

        # Get all task lists in the board for reordering
        all_lists = list(
            TaskList.objects.filter(task_board_id=task_board_id).order_by("position")
        )

        # Remove the moving list from the array
        all_lists = [tl for tl in all_lists if tl.id != task_list.id]

        # Insert it at the new position (adjust for 0-based indexing)
        all_lists.insert(new_position - 1, task_list)

        # Bulk update positions efficiently
        for idx, tl in enumerate(all_lists, start=1):
            tl.position = idx

        # Use bulk_update for efficiency
        TaskList.objects.bulk_update(all_lists, ["position"], batch_size=100)

        return Response(
            self.get_serializer(task_list).data,
            status=status.HTTP_200_OK,
        )
