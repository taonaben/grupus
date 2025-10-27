from django.urls import path
import workspace.views as views

urlpatterns = [
    # path("admin/", admin.site.urls),
    path("create/", views.CreateWorkspaceView.as_view(), name="create-workspace"),
    path("list/", views.WorkspaceList.as_view(), name="workspace-list"),
]
