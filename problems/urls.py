from django.urls import path
from .views import solved_problems_view, solved_problems_update_view, latest_solved_problems_view, recommend_problems_view


urlpatterns = [
    path('solved_problems/<str:username>/', solved_problems_view, name='solved_problems'),
    path('solved_problems_update/<str:username>/', solved_problems_update_view, name='solved_problems_update'),
    path('latest_solved_problems/<str:username>/', latest_solved_problems_view, name='latest_solved_problems'),
    path('recommend_problems/<str:username>/', recommend_problems_view, name='recommend_problems'),
]