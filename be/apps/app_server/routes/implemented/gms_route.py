from django.urls import path

from apps.app_server.controllers.implemented.gms_controller import MyXPView, LeaderboardView

urlpatterns = [
    path('gms/xp/', MyXPView.as_view(), name='my-xp'),
    path('gms/leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
