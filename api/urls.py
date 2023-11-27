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
    join_team
)

urlpatterns = [
    # auth
    path("token/", MyTokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("register/", register, name="register"),
    
    #hunt
    path("hunts/", HuntListCreateView.as_view()),
    path("hunt/<slug:slug>/", HuntDetailView.as_view()),

    #before hunt functions
    path("hunt/<int:hunt_id>/create_puzzle/", create_puzzle),
    path("hunt/<int:hunt_id>/create_team/", create_team),
    path("hunt/<int:hunt_id>/join_team/", join_team),
    
]
