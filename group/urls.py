from django.urls import path, include
import group.views as views

urlpatterns = [
    # Create group within a workspace
    path(
        "workspace/<uuid:workspace_id>/create/",
        views.CreateGroupView.as_view(),
        name="create-workspace-group",
    ),
    # Create independent group
    path("create/", views.CreateGroupView.as_view(), name="create-group"),
    # List groups
    path("list/", views.GroupList.as_view(), name="list-groups"),
]
