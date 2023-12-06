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
    post_hunt_images,
    get_puzzle_images,
    get_rules,
    add_rule
)

from .views.frontend_helpers import (
    hunt_exists
)

urlpatterns = [
    # auth
    path("token/", MyTokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("register/", register, name="register"),

    # hunt
    path("hunts/", HuntListCreateView.as_view()),
    path("hunt/<slug:slug>/", HuntDetailView.as_view()),



    # before the hunt functions
    path("<slug:hunt_slug>/create-puzzle/", create_puzzle),
    path("<slug:hunt_slug>/create-team/", create_team),
    path("<slug:hunt_slug>/join-team/", join_team),

    # During the hunt functions
    path("<slug:hunt_slug>/get-current-puzzle-view/", get_current_puzzle_view),
    path("<slug:hunt_slug>/puzzle/<str:type_param>/", get_next_or_skip_puzzle),
    path("<int:puzzle_id>/submit-answer/", submit_answer),
    path("<slug:hunt_slug>/leaderboard/", get_leaderboard),
    path("<slug:hunt_slug>/announcements/", get_announcements),
    path("<slug:hunt_slug>/add-announcements/", add_announcements),
    path("<slug:hunt_slug>/<int:team_id>/<int:puzzle_id>/add-hint/", add_hint),
    path("<int:team_id>/<int:puzzle_id>/get-hints/", get_hints),

    path("<int:puzzle_id>/get-puzzle-images/", get_puzzle_images),

    # After the hunt functions
    path("<slug:hunt_slug>/get-hunt-images/", get_hunt_images),
    path("<slug:hunt_slug>/post-hunt-images/", post_hunt_images),
    
    # other hunt info
    path("<slug:hunt_slug>/get-rules/", get_rules),
    path("<slug:hunt_slug>/add-rule/", add_rule),

    # frontend helpers
    path("<slug:hunt_slug>/hunt-exists/", hunt_exists),

]
