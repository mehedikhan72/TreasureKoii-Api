# this files contain all the helper functions for the frontend

from django.http import JsonResponse
from rest_framework.decorators import api_view
from ..models import Hunt
from django.utils import timezone
from rest_framework.response import Response
from ..serializers import HuntSerializer

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


@api_view(['GET'])
def get_users_hunts(request):
    # returns a list of the hunts(most possibly one) that the user is registered to and that is yet to start
    user = request.user
    if not user:
        return Response({"hunts": []})
    hunts = user.participating_hunts.all()
    hunts_list = []
    for hunt in hunts:
        serializer = HuntSerializer(hunt)
        if hunt.start_date > timezone.now():
            hunts_list.append(serializer.data)

    return Response({"hunts": hunts_list})
