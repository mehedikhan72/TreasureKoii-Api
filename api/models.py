from django.db import models
from django.utils.text import slugify

from django.contrib.auth.models import AbstractUser
from .managers import UserManager

# Create your models here.


class User(AbstractUser):
    username = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=100, unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()
    phone = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Hunt(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    poster_img = models.ImageField(upload_to='images/', blank=True)
    number_of_skips_for_each_team = models.IntegerField(default=3)

    # Once user will create a hunt but after that, he/she can add other users as organizers
    organizers = models.ManyToManyField(User, related_name='organizing_hunts')
    participants = models.ManyToManyField(
        User, related_name='participating_hunts', null=True, blank=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Hunt, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Puzzle(models.Model):
    hunt = models.ForeignKey(
        Hunt, on_delete=models.CASCADE, related_name='puzzles')
    name = models.CharField(max_length=100)
    description = models.TextField()
    answer = models.CharField(max_length=100)  # need to be case insensitive
    type = models.CharField(max_length=100, blank=True, null=True)
    # easy, medium, hard
    points = models.IntegerField(default=0)

    # max points for easy, medium, hard are respectively 50, 75, 100... the points will be
    # calculated based on the time taken to solve the puzzle.

    # images - one to many relationship with PuzzleImage class.


class Team(models.Model):
    hunt = models.ForeignKey(
        Hunt, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100)
    leader = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='teams_lead_by')
    members = models.ManyToManyField(User, related_name='teams')
    # for a team, in a specific hunt.
    remaining_skips = models.IntegerField(default=3)
    joining_password = models.CharField(max_length=100, blank=True, null=True)

    # during hunt settings
    current_puzzle = models.ForeignKey(
        Puzzle, on_delete=models.CASCADE, related_name='current_puzzle', blank=True, null=True)
    viewed_puzzles = models.ManyToManyField(
        Puzzle, related_name='given_to_teams', blank=True)
    solved_puzzles = models.ManyToManyField(
        Puzzle, related_name='solved_by_teams', blank=True)
    points = models.IntegerField(default=0)


class PuzzleImage(models.Model):
    puzzle = models.ForeignKey(
        Puzzle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='images/', blank=True)


class PuzzleTimeMaintenance(models.Model):
    puzzle = models.ForeignKey(
        Puzzle, on_delete=models.CASCADE, related_name='time_maintenance')
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name='time_maintenance')
    puzzle_start_time = models.DateTimeField(null=True, blank=True)
    puzzle_end_time = models.DateTimeField(null=True, blank=True)
    
# for all of the teams
class Announcement(models.Model):
    hunt = models.ForeignKey(
        Hunt, on_delete=models.CASCADE, related_name='announcements')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements', null=True, blank=True)
    
# for each puzzle, for each team
class Hint(models.Model):
    puzzle = models.ForeignKey(
        Puzzle, on_delete=models.CASCADE, related_name='hints')
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name='hints')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
class HuntImage(models.Model):
    hunt = models.ForeignKey(
        Hunt, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='images/', blank=True)

class Rule(models.Model):
    hunt = models.ForeignKey(
        Hunt, on_delete=models.CASCADE, related_name='rules')
    rule = models.TextField()