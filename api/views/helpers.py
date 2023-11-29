from django.utils import timezone
import random
from ..models import Team

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

def count_points(puzzle, puzzle_maintenance):
    start_time = puzzle_maintenance.puzzle_start_time
    end_time = puzzle_maintenance.puzzle_end_time

    max_points = puzzle.points
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

def get_random_puzzle(hunt, team):
    viewed_puzzles = team.viewed_puzzles.all()
    solved_puzzles = team.solved_puzzles.all()
    available_puzzles = hunt.puzzles.exclude(
        id__in=viewed_puzzles).exclude(id__in=solved_puzzles)

    if not available_puzzles.exists():
        return None

    random_puzzle = random.choice(available_puzzles)
    return random_puzzle

def user_already_in_a_team(user, hunt):
    teams = Team.objects.filter(hunt=hunt)
    for team in teams:
        if user in team.members.all():
            return True
    return False