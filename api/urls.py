from django.urls import path
from .views.auth_view import MyTokenObtainPairView, register
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .views.hunt_view import (
    HuntListCreateView,
    HuntDetailView,
)

urlpatterns = [
    # auth
    path("token/", MyTokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("register/", register, name="register"),
    
    #hunt
    path("hunts/", HuntListCreateView.as_view()),
    path("hunt/<slug:slug>/", HuntDetailView.as_view()),
    
]
