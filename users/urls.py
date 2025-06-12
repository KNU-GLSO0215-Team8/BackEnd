from django.urls import path
from .views import register, login, delete, change_baekjoon_id


urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('delete/', delete, name='delete_user'),
]