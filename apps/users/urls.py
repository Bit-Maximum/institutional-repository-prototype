from django.urls import path

from .views import (
    OAuthConnectionsView,
    OAuthDisconnectView,
    UserLoginView,
    UserLogoutView,
    UserProfileEditView,
    UserProfileView,
    UserRegisterView,
)

urlpatterns = [
    path("register/", UserRegisterView.as_view(), name="register"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/edit/", UserProfileEditView.as_view(), name="profile-edit"),
    path("oauth/", OAuthConnectionsView.as_view(), name="oauth-settings"),
    path("oauth/disconnect/<int:pk>/", OAuthDisconnectView.as_view(), name="oauth-disconnect"),
]
