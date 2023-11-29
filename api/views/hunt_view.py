from ..models import Hunt, User, Puzzle, PuzzleImage, Team, PuzzleTimeMaintenance
from ..serializers import HuntSerializer, UserDataSerializer, PuzzleSerializer
import random
import string
from django.utils import timezone
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
    easy_points = request.data.get('easy_points')
    medium_points = request.data.get('medium_points')
    hard_points = request.data.get('hard_points')

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
        hunt=hunt, name=name, description=description, type=type, answer=answer, easy_points=easy_points, medium_points=medium_points, hard_points=hard_points)
    for image in images:
        PuzzleImage.objects.create(puzzle=puzzle, image=image)

    return Response({
        "success": "Puzzle created successfully",
    }, status=status.HTTP_201_CREATED)


def user_already_in_a_team(user, hunt):
    teams = Team.objects.filter(hunt=hunt)
    for team in teams:
        if user in team.members.all():
            return True
    return False


@api_view(['POST'])
def create_team(request, hunt_id):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to create a team"},
            status=status.HTTP_400_BAD_REQUEST,)
    user = User.objects.get(id=request.user.id)
    if user_already_in_a_team(user, Hunt.objects.get(id=hunt_id)):
        return Response(
            {"error": "You are already in a team for this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    hunt = Hunt.objects.get(id=hunt_id)
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
def join_team(request, hunt_id):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to join a team"},
            status=status.HTTP_400_BAD_REQUEST,)
    hunt = Hunt.objects.get(id=hunt_id)
    if is_hunt_active(hunt) or is_after_hunt_end(hunt):
        return Response(
            {"error": "You cannot join a team now."},
            status=status.HTTP_400_BAD_REQUEST,)
    user = User.objects.get(id=request.user.id)
    if user_already_in_a_team(user, Hunt.objects.get(id=hunt_id)):
        return Response(
            {"error": "You are already in a team for this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    team_password = request.data.get('team_password')

    try:
        team = Team.objects.get(
            hunt_id=hunt_id, joining_password=team_password)
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


def is_hunt_active(hunt):
    return hunt.start_date <= timezone.now() <= hunt.end_date


def is_before_hunt_start(hunt):
    return timezone.now() < hunt.start_date


def is_after_hunt_end(hunt):
    return timezone.now() > hunt.end_date


def is_team_leader(user, team):
    if team.leader == user:
        return True

    return False


def get_random_puzzle(hunt, team):
    viewed_puzzles = team.viewed_puzzles.all()
    solved_puzzles = team.solved_puzzles.all()
    available_puzzles = hunt.puzzles.exclude(
        id__in=viewed_puzzles).exclude(id__in=solved_puzzles)

    if not available_puzzles.exists():
        return None

    random_puzzle = random.choice(available_puzzles)
    return random_puzzle

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
        puzzle = get_random_puzzle(hunt, team)
        if puzzle is None:
            return Response(
                {"error": "No more puzzles left to solve."},
                status=status.HTTP_400_BAD_REQUEST,)
        team.current_puzzle = puzzle

        puzzle_mainenance = PuzzleTimeMaintenance.objects.create(
            puzzle=puzzle, team=team)
        puzzle_mainenance.puzzle_start_time = timezone.now()

    puzzle = team.current_puzzle
    puzzle_serializer = PuzzleSerializer(puzzle)
    return Response(puzzle_serializer.data)


@api_view(['POST'])
def get_next_or_skip_puzzle(request, hunt_slug, type_param):
    # type_param = 'next' or 'skip'.. based on this, implementation will vary a bit.
    
    # let a leader skip a puzzle, if skips are available
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to skip the puzzle"},
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
    team.save()

    puzzle_mainenance = PuzzleTimeMaintenance.objects.create(
        puzzle=puzzle, team=team)
    puzzle_mainenance.puzzle_start_time = timezone.now()

    # return the new puzzle
    puzzle_serializer = PuzzleSerializer(puzzle)
    return Response(puzzle_serializer.data)


def count_points(puzzle, puzzle_maintenance):
    start_time = puzzle_maintenance.puzzle_start_time
    end_time = puzzle_maintenance.puzzle_end_time

    max_points = None
    if puzzle.type == 'easy':
        max_points = puzzle.easy_points
    elif puzzle.type == 'medium':
        max_points = puzzle.medium_points
    elif puzzle.type == 'hard':
        max_points = puzzle.hard_points

    time_taken = end_time - start_time

    hunt = puzzle.hunt
    # one problem may take the entire day(worst case)
    max_allowed_time = hunt.end_date - hunt.start_date

    points = None
    # no points deduction in the first 30 mins
    if time_taken < 30 * 60:
        points = max_points
    else:
        points = max(max_points * (1 - (time_taken - 30 * 60) /
                     max_allowed_time), 0.5 * max_points)
        points = round(points)
    return points


@api_view(['POST'])
def submit_answer(request, puzzle_id):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to check the answer"},
            status=status.HTTP_400_BAD_REQUEST,)

    puzzle = Puzzle.objects.get(id=puzzle_id)
    team = Team.objects.get(leader=request.user)

    if not team:
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

    