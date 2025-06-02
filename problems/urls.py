from django.urls import path
from .views import solved_problems, solved_problems_update


urlpatterns = [
    path('solved_problems/<str:username>/', solved_problems, name='solved_problems'),
    path('solved_problems_update/<str:username>/', solved_problems_update, name='solved_problems_update'),
]