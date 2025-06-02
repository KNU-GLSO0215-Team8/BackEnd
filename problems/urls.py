from django.urls import path
from .views import solved_problems


urlpatterns = [
    path('solved_problems/<str:username>/', solved_problems, name='solved_problems'),
]