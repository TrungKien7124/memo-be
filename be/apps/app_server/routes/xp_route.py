from django.urls import path

from apps.app_server.controllers.xp_controller import MyXPView, LeaderboardView

urlpatterns = [
    path('xp/', MyXPView.as_view(), name='my-xp'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
