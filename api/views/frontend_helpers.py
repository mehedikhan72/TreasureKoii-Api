# this files contain all the helper functions for the frontend

from django.http import JsonResponse
from rest_framework.decorators import api_view
from ..models import Hunt

@api_view(['GET'])
def hunt_exists(request, hunt_slug):
    hunt = Hunt.objects.filter(slug=hunt_slug)
    if hunt.exists():
        return JsonResponse({"hunt_exists": True})
    else:
        return JsonResponse({"hunt_exists": False})
    
@api_view(['GET'])
def is_user_an_organizer(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    organizers = hunt.organizers.all()
    user = request.user
    if user in organizers:
        return JsonResponse({"is_organizer": True})
    else:
        return JsonResponse({"is_organizer": False})
    

    