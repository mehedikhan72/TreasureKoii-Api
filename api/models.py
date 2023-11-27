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
    organizers = models.ManyToManyField(User, related_name='hunts')

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Hunt, self).save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Team(models.Model):
    hunt = models.ForeignKey(Hunt, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100)
    leader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teams_lead_by')
    members = models.ManyToManyField(User, related_name='teams')
    remaining_skips = models.IntegerField(default=3) # for a team, in a specific hunt. 
    joining_password = models.CharField(max_length=100, blank=True, null=True)
    
class Puzzle(models.Model):
    hunt = models.ForeignKey(Hunt, on_delete=models.CASCADE, related_name='puzzles')
    name = models.CharField(max_length=100)
    description = models.TextField()
    answer = models.CharField(max_length=100) # need to be case insensitive
    type = models.CharField(max_length=100, blank=True, null=True) 
    # easy, medium, hard
    # max points for easy, medium, hard are respectively 50, 75, 100... the points will be 
    # calculated based on the time taken to solve the puzzle.
    
    # images - one to many relationship with PuzzleImage class.
    
class PuzzleImage(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='images/', blank=True)
    
class PuzzleTimeMaintenance(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name='time_maintenance')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='time_maintenance')
    puzzle_start_time = models.DateTimeField()
    puzzle_end_time = models.DateTimeField()
    
    
    
    
    
    
