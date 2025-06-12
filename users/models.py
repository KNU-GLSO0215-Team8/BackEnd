from django.db import models

# Create your models here.
from django.db import models
import hashlib

# Create your models here.

class user(models.Model):
    _id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=32, unique=True)
    password = models.CharField(max_length=64)  # SHA-256 해시는 64자
    baekjoon_id = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 이미 해시된 비밀번호가 아니라면 해시 처리
        if len(self.password) != 64:
            self.password = hashlib.sha256(self.password.encode()).hexdigest()
        super().save(*args, **kwargs)


