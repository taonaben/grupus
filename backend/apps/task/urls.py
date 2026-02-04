from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.task_board_views import TaskBoardViewSet
from .views.task_list_views import TaskListViewSet
from .views.task_card_views import TaskViewSet

router = DefaultRouter()
router.register(r"board", TaskBoardViewSet, basename="task-board")
router.register(r"list", TaskListViewSet, basename="task-list")
router.register(r"task", TaskViewSet, basename="task")

urlpatterns = [
    path("", include(router.urls)),
]
