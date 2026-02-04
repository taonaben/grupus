from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.group_views import GroupViewSet
from .views.group_members_views import GroupMemberViewSet

router = DefaultRouter()
router.register(r"", GroupViewSet, basename="group")
router.register(r"member", GroupMemberViewSet, basename="group-member")

urlpatterns = [
    path("", include(router.urls)),
]
