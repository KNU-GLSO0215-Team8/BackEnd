from django.shortcuts import render
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from oneDay_oneProblem.celery import app
from celery import group
from datetime import timedelta
from django.utils import timezone

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

def get_solved_problems(baekjoon_id: str) -> list[int]:
    
    userObject = user.objects.filter(baekjoon_id=baekjoon_id).first()
    if not userObject:
        print(f"User with baekjoon_id {baekjoon_id} not found.")
        return None
    
    solved_problems = problem_solved_user.objects.filter(userId=userObject._id).values_list('problemId', flat=True)

    if not solved_problems:
        print(f"No solved problems found for user {baekjoon_id}.")
        return []


    return list(solved_problems)

def get_latest_solved_problems(baekjoon_id: str, num: int) -> list[int]:
    """
    Retrieve the latest solved problems for a specific user.
    """
    userObject = user.objects.filter(baekjoon_id=baekjoon_id).first()
    if not userObject:
        print(f"User with baekjoon_id {baekjoon_id} not found.")
        return None

    solved_problems = problem_solved_user.objects\
    .filter(userId=userObject._id, created_at__gt=timezone.now() - timedelta(days=30))\
    .order_by('-created_at')\
    .values_list('problemId', flat=True)[:num]

    if not solved_problems:
        print(f"No solved problems found for user {baekjoon_id}.")
        return []

    return list(solved_problems)

# 추천
def recommend_problems(baekjoon_id: str, num: int = 10) -> list[int]:
    """
    Recommend problems for a specific user based on their solved problems.
    """
    userObject = user.objects.filter(baekjoon_id=baekjoon_id).first()
    if not userObject:
        print(f"User with baekjoon_id {baekjoon_id} not found.")
        return None

    tags = dict({
        "math": 0,
        "implementation": 0,
        "greedy": 0,
        "data_structures": 0,
        "graphs": 0,
        "dp": 0,
        "geometry": 0,
        "string": 0
    })
    
    for tag in tags.keys():
        url = f"{solved_ac}/search/problem?query=tag:{tag}+s@{userObject.baekjoon_id}&sort=level&direction=desc&page=1"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            i = 0
            for item in data['items']:
                if i >= 50:
                    break
                tags[tag] += item['level']
                i += 1

    tags = list(zip(tags.keys(), tags.values()))
    tags.sort(key=lambda x: x[1])
    toplevel = tags[-1][1]/50+2 if tags[-1][1] > 3 else 5
    bottomlevel = tags[0][1]/50-2 if tags[0][1] < 3 else 1

    #(tag:math+|+tag:implementation)+*s2..s1+-s@daniel040607+s%2310000..&sort=solved&direction=desc&page=1
    tag_query = "("+"+ | +".join([f"tag:{tag[0]}" for tag in tags[:3]])+")"
    level_query = f"*{bottomlevel}..{toplevel}"
    query = f"{tag_query}+{level_query}+ -s@{baekjoon_id}+s%231000.."
    url = f"{solved_ac}/search/problem?query={query}&sort=solved&direction=desc&page=1"
    print(url)



    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch recommended problems for user {baekjoon_id}: {response.status_code}")
        return None
    data = response.json()
    items = data.get('items', [])
    if not items:
        print(f"No recommended problems found for user {baekjoon_id}.")
        return []
    
    problem_ids = [item['problemId'] for item in items[:num]]
    if not problem_ids:
        print(f"No recommended problems found for user {baekjoon_id}.")
        return []
   
    return problem_ids




@api_view(['GET'])
def solved_problems_update_view(request, username: str) -> Response:
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

@api_view(['GET'])
def solved_problems_view(request, username: str) -> Response:
    """
    Retrieve the list of solved problems for a specific user.
    """
    if not username:
        return Response({"error": "Username is required"}, status=400)

    userObject = user.objects.filter(name=username).first()
    if not userObject:
        return Response({"error": "User not found"}, status=404)

    solved_problems = get_solved_problems(userObject.baekjoon_id)
    if not solved_problems:
        return Response({"error": "Failed to retrieve solved problems"}, status=500)

    return Response({
        "baekjoon_id": userObject.baekjoon_id,
        "username": userObject.name,
        "solved_count": len(solved_problems),
        "solved_problems": solved_problems
    }, status=200)

@api_view(['GET'])
def latest_solved_problems_view(request, username: str) -> Response:
    """
    Retrieve the latest solved problems for a specific user.
    """
    if not username:
        return Response({"error": "Username is required"}, status=400)

    userObject = user.objects.filter(name=username).first()
    if not userObject:
        return Response({"error": "User not found"}, status=404)

    solved_problems = get_latest_solved_problems(userObject.baekjoon_id, 10)
    if not solved_problems:
        return Response({"error": "Failed to retrieve latest solved problems"}, status=500)

    return Response({
        "baekjoon_id": userObject.baekjoon_id,
        "username": userObject.name,
        "solved_count": len(solved_problems),
        "solved_problems": solved_problems
    }, status=200)

@api_view(['GET'])
def recommend_problems_view(request, username: str) -> Response:
    """
    Recommend problems for a specific user based on their solved problems.
    """
    if not username:
        return Response({"error": "Username is required"}, status=400)

    userObject = user.objects.filter(name=username).first()
    if not userObject:
        return Response({"error": "User not found"}, status=404)

    recommended_problems = recommend_problems(userObject.baekjoon_id)
    if not recommended_problems:
        return Response({"error": "Failed to retrieve recommended problems"}, status=500)

    return Response({
        "baekjoon_id": userObject.baekjoon_id,
        "username": userObject.name,
        "recommended_problems": recommended_problems
    }, status=200)