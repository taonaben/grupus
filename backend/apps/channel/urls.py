from django.urls import path, include
import apps.channel.views as views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"", views.ChannelViewSet, basename="channel")

urlpatterns = [
    path("", include(router.urls)),
]
