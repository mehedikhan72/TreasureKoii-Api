from ..models import Hunt, User, Puzzle, PuzzleImage, Team, PuzzleTimeMaintenance, Announcement, Hint, HuntImage
from ..serializers import HuntSerializer, UserDataSerializer, PuzzleSerializer, PuzzleImageSerializer, HuntImageSerializer
import random
import string
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .helpers import is_hunt_active, is_before_hunt_start, is_after_hunt_end, is_team_leader, get_random_puzzle, count_points, user_already_in_a_team

# Let's have the implementation in this order - Before Hunt, During Hunt, After Hunt

# Before Hunt


class HuntListCreateView(generics.ListCreateAPIView):
    queryset = Hunt.objects.all()
    serializer_class = HuntSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            organizers=User.objects.filter(id=self.request.user.id),
        )


class HuntDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hunt.objects.all()
    serializer_class = HuntSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


@api_view(['POST'])
def create_puzzle(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    name = request.data.get('name')
    description = request.data.get('description')
    type = request.data.get('type')
    answer = request.data.get('answer')
    points = request.data.get('points')

    if not hunt or not name or not description or not type or not answer:
        return Response(
            {"error": "Please provide all fields"},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    if not user in hunt.organizers.all():
        return Response(
            {"error": "You are not an organizer of this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    # save images
    images = request.FILES.getlist('images')
    puzzle = Puzzle.objects.create(
        hunt=hunt, name=name, description=description, type=type, answer=answer, points=points)
    for image in images:
        PuzzleImage.objects.create(puzzle=puzzle, image=image)

    return Response({
        "success": "Puzzle created successfully",
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def create_team(request, hunt_slug):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to create a team"},
            status=status.HTTP_400_BAD_REQUEST,)
    user = User.objects.get(id=request.user.id)
    if user_already_in_a_team(user, Hunt.objects.get(slug=hunt_slug)):
        return Response(
            {"error": "You are already in a team for this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    # TODO: make sure its before hunt stage

    hunt = Hunt.objects.get(slug=hunt_slug)
    name = request.data.get('name')
    leader = user
    remaining_skips = hunt.number_of_skips_for_each_team

    joining_password = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=8))

    if not hunt or not name or not leader:
        return Response(
            {"error": "Please provide all fields"},
            status=status.HTTP_400_BAD_REQUEST,)

    team = Team.objects.create(hunt=hunt, name=name, leader=leader,
                               remaining_skips=remaining_skips, joining_password=joining_password)
    team.members.add(leader)
    team.save()
    hunt.participants.add(user)

    return Response({
        "success": "Team created successfully. Here is your joining password: " + joining_password + ". Please share this password with your team members.",
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def join_team(request, hunt_slug):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to join a team"},
            status=status.HTTP_400_BAD_REQUEST,)
    hunt = Hunt.objects.get(slug=hunt_slug)
    if is_hunt_active(hunt) or is_after_hunt_end(hunt):
        return Response(
            {"error": "You cannot join a team now."},
            status=status.HTTP_400_BAD_REQUEST,)
    user = User.objects.get(id=request.user.id)
    if user_already_in_a_team(user, Hunt.objects.get(slug=hunt_slug)):
        return Response(
            {"error": "You are already in a team for this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    team_password = request.data.get('team_password')

    try:
        team = Team.objects.get(
            hunt=hunt, joining_password=team_password)
    except Team.DoesNotExist:
        return Response(
            {"error": "Invalid team password. Please try again."},
            status=status.HTTP_400_BAD_REQUEST,)

    team.members.add(user)
    team.save()
    hunt.participants.add(user)
    hunt.save()

    return Response({
        "success": "You have joined the team successfully.",
    }, status=status.HTTP_201_CREATED)

# During the Hunt

# puzzle view for each team


@api_view(['GET'])
def get_current_puzzle_view(request, hunt_slug):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to view the puzzle"},
            status=status.HTTP_400_BAD_REQUEST,)

    hunt = Hunt.objects.get(slug=hunt_slug)
    if not is_hunt_active(hunt):
        return Response(
            {"error": "Hunt is not active now."},
            status=status.HTTP_400_BAD_REQUEST,)

    if not user_already_in_a_team(request.user, hunt):
        return Response(
            {"error": "You are not in a team for this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    team = Team.objects.get(hunt=hunt, members=user)

    # no puzzle has been assigned to this team yet(probably their first visit)
    if not team.current_puzzle:
        print("current puzzle not found")
        puzzle = get_random_puzzle(hunt, team)
        if puzzle is None:
            return Response(
                {"error": "No more puzzles left to solve."},
                status=status.HTTP_400_BAD_REQUEST,)
        team.current_puzzle = puzzle
        team.viewed_puzzles.add(puzzle)
        team.save()
        puzzle_mainenance = PuzzleTimeMaintenance.objects.create(
            puzzle=puzzle, team=team)
        puzzle_mainenance.puzzle_start_time = timezone.now()
        puzzle_mainenance.save()

    puzzle = team.current_puzzle
    puzzle_serializer = PuzzleSerializer(puzzle)
    return Response(puzzle_serializer.data)


@api_view(['GET'])
def get_next_or_skip_puzzle(request, hunt_slug, type_param):
    # type_param = 'next' or 'skip'.. based on this, implementation will vary a bit.

    # let a leader skip a puzzle, if skips are available
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to skip the puzzle"},
            status=status.HTTP_400_BAD_REQUEST,)
    print("slug " + hunt_slug)
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not is_hunt_active(hunt):
        return Response(
            {"error": "Hunt is not active now."},
            status=status.HTTP_400_BAD_REQUEST,)

    if not user_already_in_a_team(request.user, hunt):
        return Response(
            {"error": "You are not in a team for this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    try:
        team = Team.objects.get(hunt=hunt, leader=user)
    except Team.DoesNotExist:
        return Response(
            {"error": "You need to be the leader of your team to skip a puzzle."},
            status=status.HTTP_400_BAD_REQUEST,)

    # handle skip
    if type_param == 'skip':
        if team.remaining_skips <= 0:
            return Response(
                {"error": "You don't have any skips left."},
                status=status.HTTP_400_BAD_REQUEST,)

        team.remaining_skips -= 1
    puzzle = get_random_puzzle(hunt, team)
    if puzzle is None:
        return Response(
            {"error": "No more puzzles left to skip."},
            status=status.HTTP_400_BAD_REQUEST,)
    team.current_puzzle = puzzle
    team.viewed_puzzles.add(puzzle)
    team.save()

    puzzle_mainenance = PuzzleTimeMaintenance.objects.create(
        puzzle=puzzle, team=team)
    puzzle_mainenance.puzzle_start_time = timezone.now()
    puzzle_mainenance.save()

    # return the new puzzle
    puzzle_serializer = PuzzleSerializer(puzzle)
    return Response(puzzle_serializer.data)


@api_view(['POST'])
def submit_answer(request, puzzle_id):
    # TODO: bug - answer gets solved even if req sent by a non-leader - always gets added to viewed.
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to check the answer"},
            status=status.HTTP_400_BAD_REQUEST,)

    puzzle = Puzzle.objects.get(id=puzzle_id)
    hunt = puzzle.hunt

    try:
        team = Team.objects.get(leader=request.user, hunt=hunt)
    except Team.DoesNotExist:
        return Response(
            {"error": "Only the leader of the team can submit the answer."},
            status=status.HTTP_400_BAD_REQUEST,)

    if not puzzle:
        return Response(
            {"error": "Invalid puzzle id."},
            status=status.HTTP_400_BAD_REQUEST,)

    answer = request.data.get('answer')
    if not answer:
        return Response(
            {"error": "Please provide the answer."},
            status=status.HTTP_400_BAD_REQUEST,)

    if puzzle not in team.viewed_puzzles.all():
        return Response(
            {"error": "This puzzle is not available for your team... yet."},
            status=status.HTTP_400_BAD_REQUEST,)

    if answer.lower() == puzzle.answer.lower():
        # handle correct answers and points.
        team.solved_puzzles.add(puzzle)
        puzzle_maintenance = PuzzleTimeMaintenance.objects.get(
            puzzle=puzzle, team=team)
        puzzle_maintenance.puzzle_end_time = timezone.now()
        puzzle_maintenance.save()

        points = count_points(puzzle, puzzle_maintenance)
        team.points += points
        team.save()

        return Response({
            "success": "Correct answer. You have earned " + str(points) + " points.",
        }, status=status.HTTP_200_OK)

    else:
        return Response({
            "error": "Wrong answer. Please try again.",
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_leaderboard(request, hunt_slug):
    # TODO: after first production - let orgs choose whether they want the leaderboard to show at a particular time.
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)

    teams = Team.objects.filter(hunt=hunt)
    leaderboard = []
    for team in teams:
        leaderboard.append({
            "team_name": team.name,
            "team_leader": team.leader.first_name + " " + team.leader.last_name,
            "points": team.points,
        })

    leaderboard = sorted(leaderboard, key=lambda k: k['points'], reverse=True)
    return Response(leaderboard)


@api_view(['GET'])
def get_announcements(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)

    announcements = hunt.announcements.all().sort_by('-created_at')
    return Response(announcements)


@api_view(['POST'])
def add_announcements(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)

    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to add an announcement"},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    if not user in hunt.organizers.all():
        return Response(
            {"error": "You are not an organizer of this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    text = request.data.get('text')
    if not text:
        return Response(
            {"error": "Please provide the text."},
            status=status.HTTP_400_BAD_REQUEST,)

    Announcement.objects.create(hunt=hunt, text=text, creator=user)
    return Response({
        "success": "Announcement added successfully.",
    }, status=status.HTTP_200_OK)

# hints will be given during the hunt, since puzzles will come in different order for each team,
# the hints will be separately given for each team, organizers will appoint a person to give hints
# and guide the team.

# TODO: implement this later, not a core functionality.


@api_view(['POST'])
def add_hint(request, hunt_slug, team_id, puzzle_id):
    user = User.objects.get(id=request.user.id)
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not user in hunt.organizers.all():
        return Response(
            {"error": "You are not an organizer of this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    team = Team.objects.get(id=team_id)
    puzzle = Puzzle.objects.get(id=puzzle_id)

    text = request.data.get('text')

    if not text:
        return Response(
            {"error": "Please provide the text."},
            status=status.HTTP_400_BAD_REQUEST,)

    Hint.objects.create(team=team, puzzle=puzzle, text=text)
    return Response({
        "success": "Hint added successfully.",
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_hints(request, team_id, puzzle_id):
    team = Team.objects.get(id=team_id)
    puzzle = Puzzle.objects.get(id=puzzle_id)

    hints = Hint.objects.filter(team=team, puzzle=puzzle)
    return Response(hints)


@api_view(['GET'])
def get_puzzle_images(request, puzzle_id):
    print(type(puzzle_id))
    puzzle = Puzzle.objects.get(id=puzzle_id)
    if not puzzle:
        return Response(
            {"error": "Invalid puzzle id."},
            status=status.HTTP_400_BAD_REQUEST,)
    images = puzzle.images.all()
    serializer = PuzzleImageSerializer(images, many=True)
    return Response(serializer.data)

# After Hunt

@api_view(['GET'])
def get_hunt_images(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)
    images = hunt.images.all()
    return Response(images)


@api_view(['POST'])
def post_hunt_images(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)
    user = User.objects.get(id=request.user.id)
    if not user in hunt.organizers.all():
        return Response(
            {"error": "You are not an organizer of this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    images = request.FILES.getlist('images')
    for image in images:
        HuntImage.objects.create(hunt=hunt, image=image)
    return Response({
        "success": "Images added successfully.",
    }, status=status.HTTP_200_OK)
