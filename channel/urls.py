from django.urls import path, include
import channel.views as views

urlpatterns = [
    path("create/", views.CreateChannelView.as_view(), name="create_channel"),
    path(
        "list/<uuid:group>/",
        views.ChannelList.as_view(),
        name="list_group_channels",
    ),
    path(
        "list/<uuid:workspace>/",
        views.ChannelList.as_view(),
        name="list_workspace_channels",
    ),
]
