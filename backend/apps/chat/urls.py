from django.urls import path, include
import apps.chat.views as views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"messages", views.MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
]
