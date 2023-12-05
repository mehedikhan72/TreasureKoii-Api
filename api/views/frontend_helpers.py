# this files contain all the helper functions for the frontend

from django.http import JsonResponse
from django.utils import timezone
import random
from rest_framework.decorators import api_view
from ..models import Hunt

@api_view(['GET'])
def hunt_exists(request, hunt_slug):
    hunt = Hunt.objects.filter(slug=hunt_slug)
    if hunt.exists():
        return JsonResponse({"hunt_exists": True})
    else:
        return JsonResponse({"hunt_exists": False})