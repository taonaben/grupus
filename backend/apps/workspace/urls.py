from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.workspace_views import WorkspaceViewSet
from .views.workspace_members_views import SpaceMemberViewSet

router = DefaultRouter()
router.register(r"", WorkspaceViewSet, basename="workspace")
router.register(r"members", SpaceMemberViewSet, basename="workspace-member")

urlpatterns = [
    path("", include(router.urls)),
]
