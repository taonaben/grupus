from django.urls import path
import apps.authentication.views as views


urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login_user"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
]
