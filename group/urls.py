from django.urls import path, include
import group.views as views

urlpatterns = [
  
    path(
        "workspace/<uuid:workspace_id>/create/",
        views.CreateGroupView.as_view(),
        name="create-workspace-group",
    ),
   
    path("create/", views.CreateGroupView.as_view(), name="create-group"),
    
    path("list/", views.GroupList.as_view(), name="list-groups"),
    path("<uuid:id>/", views.GroupDetailView.as_view(), name="group-detail"),
 
    path(
        "member/create/<str:access_code>/",
        views.CreateGroupMemberView.as_view(),
        name="create-group-member",
    ),
    path(
        "member/list/<uuid:group_id>/",
        views.GroupMemberList.as_view(),
        name="list-group-members",
    ),
]
