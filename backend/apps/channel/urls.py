from django.urls import path, include
import apps.channel.views as views

urlpatterns = [
    path(
        "",
        views.ChannelViewSet.as_view({"get": "list", "post": "create"}),
        name="channels",
    ),
    # path(
    #     "list/<uuid:workspace_id>/",
    #     views.ChannelList.as_view(),
    #     name="list_workspace_channels",
    # ),
]
