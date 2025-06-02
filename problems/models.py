from django.db import models

from users.models import user

# utf-8mb4 is used to support emojis and other special characters in MySQL
class problem(models.Model):
    _id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=128)
    tag = models.JSONField(blank=True)
    acceptedUserCount = models.IntegerField(default=0)
    isSolvable = models.BooleanField(default=True)
    level = models.IntegerField()
    averageTries = models.IntegerField(default=0)

class problem_solved_user(models.Model):
    _id = models.AutoField(primary_key=True)
    problemId = models.IntegerField()
    userId = models.ForeignKey(user, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
