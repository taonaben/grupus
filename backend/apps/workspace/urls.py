from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.workspace_views import WorkspaceViewSet
from .views.workspace_members_views import SpaceMemberViewSet
from .views.workspace_types import WorkspaceTypeViewSet

router = DefaultRouter()
router.register(r"types", WorkspaceTypeViewSet, basename="workspace-type")
router.register(r"members", SpaceMemberViewSet, basename="workspace-member")
router.register(r"", WorkspaceViewSet, basename="workspace")

urlpatterns = [
    path("", include(router.urls)),
]
