from django.urls import path
from .views import solved_problems, solved_problems_update, latest_solved_problems


urlpatterns = [
    path('solved_problems/<str:username>/', solved_problems, name='solved_problems'),
    path('solved_problems_update/<str:username>/', solved_problems_update, name='solved_problems_update'),
    path('latest_solved_problems/<str:username>/', latest_solved_problems, name='latest_solved_problems'),
]