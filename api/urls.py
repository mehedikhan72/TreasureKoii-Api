from django.urls import path
from .views.auth_view import MyTokenObtainPairView, register
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .views.hunt_view import (
    HuntListCreateView,
    HuntDetailView,
    create_puzzle,
    create_team,
    join_team,
    get_current_puzzle_view,
    get_next_or_skip_puzzle,
    submit_answer,
    get_leaderboard,
    get_announcements,
    add_announcements,
    add_hint,
    get_hints,
    get_hunt_images,
    post_hunt_images
)

urlpatterns = [
    # auth
    path("token/", MyTokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("register/", register, name="register"),

    # hunt
    path("hunts/", HuntListCreateView.as_view()),
    path("hunt/<slug:slug>/", HuntDetailView.as_view()),

    # before hunt functions
    path("<slug:hunt_slug>/create_puzzle/", create_puzzle),
    path("<slug:hunt_slug>/create_team/", create_team),
    path("<slug:hunt_slug>/join_team/", join_team),

    # During the hunt functions
    path("<slug:hunt_slug>/get_current_puzzle_view/", get_current_puzzle_view),
    path("<slug:hunt_slug>/next/", get_next_or_skip_puzzle),
    path("<slug:hunt_slug>/skip/", get_next_or_skip_puzzle),
    path("<int:puzzle_id>submit_answer/", submit_answer),
    path("<slug:hunt_slug>/leaderboard/", get_leaderboard),
    path("<slug:hunt_slug>/announcements/", get_announcements),
    path("<slug:hunt_slug>/add_announcements/", add_announcements),
    path("<slug:hunt_slug>/<int:team_id>/<int:puzzle_id>/add_hint/", add_hint),
    path("<int:team_id>/<int:puzzle_id>/get_hints/", get_hints),
    path("<slug:hunt_slug>/get_hunt_images/", get_hunt_images),
    path("<slug:hunt_slug>/post_hunt_images/", post_hunt_images)

]
