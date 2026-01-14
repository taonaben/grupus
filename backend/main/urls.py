"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from apps.workspace.urls import urlpatterns as workspace_urls
from apps.group.urls import urlpatterns as group_urls
from apps.channel.urls import urlpatterns as channel_urls
from apps.task.urls import urlpatterns as task_urls
from apps.user.urls import urlpatterns as user_urls
from apps.authentication.urls import urlpatterns as auth_urls


app_urlpatterns = [
    path("auth/", include(auth_urls)),
    path("workspace/", include(workspace_urls)),
    path("group/", include(group_urls)),
    path("channel/", include(channel_urls)),
    path("task/", include(task_urls)),
    path("users/", include(user_urls)),
]

third_party_urlpatterns = [
    ## JWT Auth
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ## Schema and Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # optional ui:
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(), name="redoc"),
]


urlpatterns = [
    path("admin/", admin.site.urls),
    # Include app-specific URLs
    path("", include(app_urlpatterns)),
    # Include third-party URLs
    path("", include(third_party_urlpatterns)),
]
