from django.contrib import admin
from .models import User, Hunt, Puzzle, PuzzleImage, Team

# Register your models here.

admin.site.register(User)
admin.site.register(Hunt)
admin.site.register(Puzzle)
admin.site.register(PuzzleImage)
admin.site.register(Team)
