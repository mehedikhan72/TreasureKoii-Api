from ..models import Hunt, User, Puzzle, PuzzleImage, Team
from ..serializers import HuntSerializer, UserDataSerializer
import random
import string
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

# Let's have the implementation in this order - Before Hunt, During Hunt, After Hunt

# Before Hunt


class HuntListCreateView(generics.ListCreateAPIView):
    queryset = Hunt.objects.all()
    serializer_class = HuntSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(organizers=User.objects.filter(
            id=self.request.user.id))


class HuntDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hunt.objects.all()
    serializer_class = HuntSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


@api_view(['POST'])
def create_puzzle(request, hunt_id):
    hunt = Hunt.objects.get(id=hunt_id)
    name = request.data.get('name')
    description = request.data.get('description')
    type = request.data.get('type')
    answer = request.data.get('answer')

    if not hunt or not name or not description or not type or not answer:
        return Response(
            {"error": "Please provide all fields"},
            status=status.HTTP_400_BAD_REQUEST,)

    # save images
    images = request.FILES.getlist('images')
    puzzle = Puzzle.objects.create(
        hunt=hunt, name=name, description=description, type=type, answer=answer)
    for image in images:
        PuzzleImage.objects.create(puzzle=puzzle, image=image)

    return Response(status=status.HTTP_201_CREATED)


@api_view(['POST'])
def create_team(request, hunt_id):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to join a team"},
            status=status.HTTP_400_BAD_REQUEST,)

    hunt = Hunt.objects.get(id=hunt_id)
    name = request.data.get('name')
    leader = User.objects.get(id=request.user.id)
    members = [leader]
    remaining_skips = hunt.number_of_skips_for_each_team
    # randomly generate a joining password of 8 characters
    joining_password = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=8))

    if not hunt or not name or not leader:
        return Response(
            {"error": "Please provide all fields"},
            status=status.HTTP_400_BAD_REQUEST,)

    Team.objects.create(hunt=hunt, name=name, leader=leader, members=members,
                        remaining_skips=remaining_skips, joining_password=joining_password)
    return Response(status=status.HTTP_201_CREATED)


@api_view(['POST'])
def join_team(request, hunt_id):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to join a team"},
            status=status.HTTP_400_BAD_REQUEST,)

    team_password = request.data.get('team_password')
    team = Team.objects.get(hunt_id=hunt_id, joining_password=team_password)
    if not team:
        return Response(
            {"error": "Team not found"},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    team.members.add(user)
    return Response(status=status.HTTP_201_CREATED)
