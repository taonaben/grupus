from django.urls import path
import workspace.views as views

urlpatterns = [
    # path("admin/", admin.site.urls),
    path("create/", views.CreateWorkspaceView.as_view(), name="create-workspace"),
    path("list/", views.WorkspaceList.as_view(), name="workspace-list"),
    path("<uuid:id>/", views.WorkspaceDetailView.as_view(), name="workspace-detail"),
    # S P A C E  M E M B E R  R O U T E S
    path(
        "members/create/<str:access_code>/",
        views.CreateSpaceMemberView.as_view(),
        name="create-space-member",
    ),
    path(
        "members/<uuid:workspace_id>/",
        views.SpaceMembersList.as_view(),
        name="space-member-list",
    ),
]
