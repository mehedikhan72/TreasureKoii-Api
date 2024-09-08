from django.utils.text import slugify
from django.http import JsonResponse
from ..models import Hunt, User, Puzzle, PuzzleImage, Team, PuzzleTimeMaintenance, Announcement, Hint, HuntImage, Rule
from ..serializers import HuntSerializer, UserDataSerializer, PuzzleSerializer, PuzzleImageSerializer, HuntImageSerializer, RuleSerializer, AnnouncementSerializer
import random
import string
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .helpers import is_hunt_active, is_before_hunt_start, is_after_hunt_end, is_team_leader, get_a_puzzle, count_points, user_already_in_a_team

# Let's have the implementation in this order - Before Hunt, During Hunt, After Hunt

# Before Hunt

import uuid

from rest_framework import serializers

from django.db import IntegrityError

# class HuntListCreateView(generics.ListCreateAPIView):
#     queryset = Hunt.objects.all()
#     serializer_class = HuntSerializer
#     permission_classes = [IsAuthenticated]

#     def perform_create(self, serializer):
#         payment_uuid = uuid.uuid4()

#         serializer.save(
#             organizers=User.objects.filter(id=self.request.user.id),
#             payment_completed=False,
#             payment_uuid=payment_uuid
#         )

#         print("Hunt created successfully")


# new functional view for creating hunts cause the above one cannot handle the case where the slug is not unique

@api_view(['POST'])
def create_hunt(request):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to create a hunt"},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    name = request.data.get('name')
    description = request.data.get('description')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    poster_img = request.FILES.get('poster_img')

    # number_of_skips_for_each_team = request.data.get('number_of_skips_for_each_team')

    if not name or not description or not start_date or not end_date or not poster_img:
        return Response(
            {"error": "Please provide all fields"},
            status=status.HTTP_400_BAD_REQUEST,)

    slug = slugify(name)

    if Hunt.objects.filter(slug=slug).exists():
        return Response(
            {"error": "Hunt with this name already exists. Please try another one."},
            status=status.HTTP_400_BAD_REQUEST,)

    hunt = Hunt.objects.create(
        name=name,
        slug=slug,
        description=description,
        start_date=start_date,
        end_date=end_date,
        payment_completed=False,
        poster_img=poster_img,
        payment_uuid=uuid.uuid4()
    )
    hunt.organizers.add(user)
    hunt.save()

    return Response({
        "success": "Hunt created successfully.",
    }, status=status.HTTP_201_CREATED)


class HuntDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hunt.objects.all()
    serializer_class = HuntSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

# manual payment logic


@api_view(['GET'])
def is_hunt_paid_for(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)

    if hunt.payment_completed == True:
        return Response({
            "paid": True
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "paid": False
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_puzzle(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    name = request.data.get('name')
    description = request.data.get('description')
    type = request.data.get('type')
    answer = request.data.get('answer')
    points = request.data.get('points')

    # get rid of front and trailing spaces
    answer = answer.strip()

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


@api_view(['GET'])
def get_all_teams_data(request, hunt_slug):
    # all data, and their puzzle order
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)
    teams = Team.objects.filter(hunt=hunt)
    data = []
    for team in teams:
        team_members = []
        for member in team.members.all():
            team_members.append({
                "name": member.first_name + " " + member.last_name,
                "email": member.email,
            })
        data.append({
            "team_id": team.id,
            "team_name": team.name,
            "team_leader": team.leader.first_name + " " + team.leader.last_name,
            "team_members": team_members,
            "team_points": team.points,
            "team_puzzle_order": team.puzzle_order_list,
        })

    return Response(data)


@api_view(['POST'])
def create_puzzle_order_for_a_team(request, hunt_slug, team_id):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to create a puzzle order"},
            status=status.HTTP_400_BAD_REQUEST,)

    user = User.objects.get(id=request.user.id)
    hunt = Hunt.objects.get(slug=hunt_slug)
    team = Team.objects.get(id=team_id)

    if not user in hunt.organizers.all():
        return Response(
            {"error": "You are not an organizer of this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)

    if not team:
        return Response(
            {"error": "Invalid team id."},
            status=status.HTTP_400_BAD_REQUEST,)
    list = request.data.get('list')
    if not list:
        return Response(
            {"error": "Please provide the list."},
            status=status.HTTP_400_BAD_REQUEST,)
    for puzzle_id in list:
        try:
            puzzle = Puzzle.objects.get(id=puzzle_id)
        except Puzzle.DoesNotExist:
            return Response(
                {"error": "Invalid puzzle id."},
                status=status.HTTP_400_BAD_REQUEST,)
        if puzzle.hunt != hunt:
            return Response(
                {"error": "Invalid puzzle id."},
                status=status.HTTP_400_BAD_REQUEST,)
    team.set_puzzle_order_list(list)
    team.save()

    return Response(
        {"success": "Puzzle order created successfully."}, status=status.HTTP_201_CREATED)


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
        puzzle = get_a_puzzle(hunt, team)
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
    if puzzle in team.solved_puzzles.all():
        # team's current puzzle did not get updated after solving the previous puzzle

        # TODO: Fix code repetition later
        puzzle = get_a_puzzle(hunt, team)
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

    puzzle_serializer = PuzzleSerializer(puzzle)
    return Response(puzzle_serializer.data)


@api_view(['GET'])
def get_next_or_skip_puzzle(request, hunt_slug, type_param):
    # type_param = 'next' or 'skip'.. based on this, implementation will vary a bit.

    # let a leader skip a puzzle, if skips are available
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to get the next puzzle"},
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
            {"error": "You need to be the leader of your team to get the next puzzle."},
            status=status.HTTP_400_BAD_REQUEST,)

    # case when a puzzle is solved and a member of the team hits refresh,
    # they will get a new puzzle(current puzzle), but then when the leader
    # hits next puzzle, they will get a new current puzzle. So, we need to
    # take care of that.
    if type_param == 'next':
        if team.current_puzzle not in team.solved_puzzles.all():
            return Response(
                {"error": "You already have a new puzzle assigned."},
                status=status.HTTP_400_BAD_REQUEST,)
    # handle skip
    if type_param == 'skip':
        if team.remaining_skips <= 0:
            return Response(
                {"error": "You don't have any skips left."},
                status=status.HTTP_400_BAD_REQUEST,)

        team.remaining_skips -= 1
    puzzle = get_a_puzzle(hunt, team)
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
    # get rid of front and trailing spaces
    answer = answer.strip()
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

    announcements = hunt.announcements.all().order_by('-created_at')
    serializer = AnnouncementSerializer(announcements, many=True)
    return Response(serializer.data)


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
    }, status=status.HTTP_201_CREATED)

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
    serializer = HuntImageSerializer(images, many=True)
    return Response(serializer.data)


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

    # make sure the count is not more than 10
    existing_images_count = hunt.images.all().count()
    if existing_images_count + len(images) > 10:
        return Response(
            {"error": "You cannot add more than 10 images."},
            status=status.HTTP_400_BAD_REQUEST,)
    for image in images:
        HuntImage.objects.create(hunt=hunt, image=image)
    return Response({
        "success": "Images added successfully.",
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_rules(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)
    rules = Rule.objects.filter(hunt=hunt)
    serializer = RuleSerializer(rules, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def add_rule(request, hunt_slug):
    hunt = Hunt.objects.get(slug=hunt_slug)
    if not hunt:
        return Response(
            {"error": "Invalid hunt slug."},
            status=status.HTTP_400_BAD_REQUEST,)

    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to add a rule"},
            status=status.HTTP_400_BAD_REQUEST,)
    user = User.objects.get(id=request.user.id)
    if not user in hunt.organizers.all():
        return Response(
            {"error": "You are not an organizer of this hunt."},
            status=status.HTTP_400_BAD_REQUEST,)
    rule = request.data.get('rule')
    Rule.objects.create(hunt=hunt, rule=rule)
    return Response({
        "success": "Rule added successfully.",
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def add_organizer_to_hunt(request, hunt_slug):
    # we get a list of emails from frontend and set them as organizers
    hunt = Hunt.objects.get(slug=hunt_slug)
    user = request.user
    organizers = hunt.organizers.all()
    if user not in organizers:
        return JsonResponse({"error": "You are not an organizer of this hunt"})
    else:
        emails = request.data.get('emails')
        print(emails)
        for email in emails:
            try:
                user = User.objects.get(email=email)
                hunt.organizers.add(user)
            except:
                pass
        hunt.save()
        return Response({
            "success": "Organizers added successfully.",
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_all_puzzles_of_a_hunt(request, hunt_slug):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Please login to get all puzzles"},
            status=status.HTTP_400_BAD_REQUEST,)

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

    puzzles = hunt.puzzles.all()
    serializer = PuzzleSerializer(puzzles, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_recent_hunts(request):
    hunts = Hunt.objects.filter(
        end_date__lte=timezone.now()).order_by('-end_date')[:5]
    hunts = [hunt for hunt in hunts if hunt.payment_completed == True]
    serializer = HuntSerializer(hunts, many=True)
    return Response(serializer.data)
