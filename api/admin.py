from django.contrib import admin
from .models import User, Hunt, Puzzle, PuzzleImage, Team, Hint, Announcement, PuzzleTimeMaintenance, HuntImage, Rule

# Register your models here.

admin.site.register(User)
admin.site.register(Hunt)
admin.site.register(Puzzle)
admin.site.register(PuzzleImage)
admin.site.register(Team)
admin.site.register(Hint)
admin.site.register(Announcement)
admin.site.register(PuzzleTimeMaintenance)
admin.site.register(HuntImage)
admin.site.register(Rule)

