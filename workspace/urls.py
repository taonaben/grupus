from django.urls import path
from .views import WorkspaceList

urlpatterns = [
    # path("admin/", admin.site.urls),
    path("workspaces/", WorkspaceList.as_view(), name="workspace-list"),
]
