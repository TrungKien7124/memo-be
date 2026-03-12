from django.urls import path

from apps.app_server.controllers.implemented.iam_auth_controller import (
    RegisterView,
    LoginView,
    CustomTokenRefreshView,
)
from apps.app_server.controllers.implemented.iam_user_profile_controller import UserProfileView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='auth-refresh'),
    path('iam/profiles/', UserProfileView.as_view(), name='user-profile'),
]
