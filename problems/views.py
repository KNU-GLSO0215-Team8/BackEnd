from django.shortcuts import render
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from oneDay_oneProblem.celery import app
from celery import group

from .models import problem, problem_solved_user
from users.models import user

solved_ac = "https://solved.ac/api/v3"


@app.task()
def task_download_problems(problem_id: int) -> dict | None:
    url = f"{solved_ac}/problem/show?problemId={problem_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        problem_data = {
            "_id": data['problemId'],
            "title": data['titleKo'],
            "tag": data['tags'],
            "acceptedUserCount": data['acceptedUserCount'],
            "isSolvable": data['isSolvable'],
            "level": data['level'],
            "averageTries": data['averageTries']
        }

        problem.objects.update_or_create(
            _id=problem_data['_id'],
            defaults={
                'title': problem_data['title'],
                'tag': problem_data['tag'],
                'acceptedUserCount': problem_data['acceptedUserCount'],
                'isSolvable': problem_data['isSolvable'],
                'level': problem_data['level'],
                'averageTries': problem_data['averageTries']
            }
        )
        return problem_data
    else:
        print(f"Error fetching problem {problem_id}: {response.status_code}\n{response.text}")
        return None
    
@app.task()
def task_search_problem(baekjoon_id: str, page: int):
    url_solved_problem = f"{solved_ac}/search/problem?query=s@{baekjoon_id}&sort=id&page={page}"
    response = requests.get(url_solved_problem)
    if response.status_code == 200:
        data = response.json()
        print(f"Fetching solved problems for user {baekjoon_id} on page {page}...")
        return data['items']
    else:
        print(f"Failed to fetch solved problems for user {baekjoon_id} on page {page}: {response.status_code}")
        return None
    
@app.task()
def task_update_db(pb: dict, userId: int):
    problem.objects.update_or_create(
        _id=pb['problemId'],
        defaults={
            'title': pb['titleKo'],
            'tag': pb['tags'],
            'acceptedUserCount': pb['acceptedUserCount'],
            'isSolvable': pb['isSolvable'],
            'level': pb['level'],
            'averageTries': pb['averageTries']
        }
    )

    problem_solved_user.objects.update_or_create(
        problemId=pb['problemId'],
        userId= user.objects.get(_id=userId),
    )



def update_solved_problem(baekjoon_id: str) -> list[int] | None:

    userObject = user.objects.get(baekjoon_id=baekjoon_id)

    if not userObject:
        print(f"User with baekjoon_id {baekjoon_id} not found.")
        return None

    url_solved_cnt = f"{solved_ac}/user/show?handle={userObject.baekjoon_id}"
    response = requests.get(url_solved_cnt)
    if response.status_code == 200:
        data = response.json()
        solved_count = data['solvedCount']
    else:
        print(f"Failed to fetch solved count for user {baekjoon_id}: {response.status_code}")
        return None


    page = (solved_count // 50) + 1 if solved_count % 50 != 0 else solved_count // 50
    list_problem_solved_user:list[problem_solved_user] = []
    print(f"Total solved problems for user {baekjoon_id}: {solved_count}, Pages: {page}")



    grouped_tasks = group(
        task_search_problem.s(baekjoon_id, i) for i in range(1, page + 1)
    )
    result = grouped_tasks()
    
    print(f"Fetching solved problems for user {baekjoon_id}...")

    # Wait for all tasks to complete
    results = result.get()

    list_problem = []
    for res in results:
        if res:
            list_problem.extend(res)

    if not list_problem:
        print(f"No solved problems found for user {baekjoon_id}.")
        return None
    
    list_problem_id = []

    for pb in list_problem:
        print(f"Problem {pb['problemId']} ({pb['titleKo']}) updated or created.")
        task_update_db.delay(pb, userObject._id)
        list_problem_id.append(pb['problemId'])

    return list_problem_id

@api_view(['GET'])
def solved_problems(request, username: str) -> Response:
    """
    Retrieve the list of solved problems for a specific user.
    """
    if not username:
        return Response({"error": "Username is required"}, status=400)

    userObject = user.objects.filter(name=username).first()
    if not userObject:
        return Response({"error": "User not found"}, status=404)

    solved_problems = update_solved_problem(userObject.baekjoon_id)
    if not solved_problems:
        return Response({"error": "Failed to update solved problems"}, status=500)

    return Response({
        "baekjoon_id": userObject.baekjoon_id,
        "username": userObject.name,
        "solved_count": len(solved_problems),
        "solved_problems": solved_problems
    }, status=200)