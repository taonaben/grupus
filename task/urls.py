from django.urls import path
from .views import (
    CreateTaskBoardView,
    TaskBoardList,
    CreateTaskListView,
    TaskListList,
    CreateTaskView,
    TaskCardList,
    GetTaskBoardMembersView,
)

urlpatterns = [
    #! T A S K   B O A R D   U R L S
    path("create-board/", view=CreateTaskBoardView.as_view(), name="create_board"),
    path("list-board/", view=TaskBoardList.as_view(), name="list_task_boards"),
    path(
        "board/<uuid:task_board_id>/members/",
        view=GetTaskBoardMembersView.as_view(),
        name="get_board_members",
    ),
    #! T A S K   L I S T   U R L S
    path(
        "create-task_list/", view=CreateTaskListView.as_view(), name="create_task_list"
    ),
    path("list-task_list/", view=TaskListList.as_view(), name="list_task_lists"),
    #! T A S K   U R L S
    path("create-task/", view=CreateTaskView.as_view(), name="create_task"),
    path("list-task_card/", view=TaskCardList.as_view(), name="list_tasks"),
]
