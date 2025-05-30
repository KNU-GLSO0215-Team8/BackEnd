from django.shortcuts import render
import requests
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
import hashlib

from .models import user

solved_ac = "https://solved.ac/api/v3"

def get_baekjoon_user_info(baekjoon_id: str) -> dict | bool:
    url = f"{solved_ac}/user/show?handle={baekjoon_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return False

def is_user_exists(username):
    '''
    같은 유저 이름이 존재하는지 확인하는 함수
    '''

    if user.objects.filter(name=username).exists():
        return True
    return False
    
def register_user(username: str, password: str, baekjoon_id: str) -> tuple[bool, str]:
    if len(username) < 2 or len(username) > 32:
        return (False, "Username len short or long")
    if len(password) < 2 or len(password) > 32:
        return (False, "Password len short or long")
    if len(baekjoon_id) < 2 or len(baekjoon_id) > 32:
        return (False, "Baekjoon ID len short or long")

    if is_user_exists(username):
        return (False, "User already exists")

    user_info = get_baekjoon_user_info(baekjoon_id)
    if not user_info:
        return (False, "Failed to retrieve baekjoon info")

    new_user = user(
        name=username,
        password=password,
        baekjoon_id=baekjoon_id
    )
    new_user.save()

    return (True, "User registered successfully")

def login_user(username: str, password: str) -> tuple[bool, str]:
    if len(username) < 2 or len(username) > 32:
        return (False, "Username len short or long")
    if len(password) < 2 or len(password) > 32:
        return (False, "Password len short or long")

    try:
        user_obj = user.objects.get(name=username)
    except:
        return (False, "User does not exist")

    if hashlib.sha256(password.encode()).hexdigest() != user_obj.password:
        return (False, "Incorrect password")

    return (True, "Login successful")

def delete_user(username: str, password: str) -> tuple[bool, str]:
    if len(username) < 2 or len(username) > 32:
        return (False, "Username len short or long")
    if len(password) < 2 or len(password) > 32:
        return (False, "Password len short or long")

    try:
        user_obj = user.objects.get(name=username)
    except:
        return (False, "User does not exist")

    if hashlib.sha256(password.encode()).hexdigest() != user_obj.password:
        return (False, "Incorrect password")

    user_obj.delete()
    return (True, "User deleted successfully")

def change_baekjoon_id(username: str, password: str, new_baekjoon_id: str) -> tuple[bool, str]:
    if len(username) < 2 or len(username) > 32:
        return (False, "Username len short or long")
    if len(password) < 2 or len(password) > 32:
        return (False, "Password len short or long")
    if len(new_baekjoon_id) < 2 or len(new_baekjoon_id) > 32:
        return (False, "New Baekjoon ID len short or long")

    try:
        user_obj = user.objects.get(name=username)
    except:
        return (False, "User does not exist")

    if hashlib.sha256(password.encode()).hexdigest() != user_obj.password:
        return (False, "Incorrect password")

    user_info = get_baekjoon_user_info(new_baekjoon_id)
    if not user_info:
        return (False, "Failed to retrieve baekjoon info")

    user_obj.baekjoon_id = new_baekjoon_id
    user_obj.save()

    return (True, "Baekjoon ID changed successfully")


@api_view(['POST'])
def register(request: Request) -> Response:
    data = request.data
    username = data.get('username')
    password = data.get('password')
    baekjoon_id = data.get('baekjoon_id')

    if not username or not password or not baekjoon_id:
        return Response({"error": "Missing required fields"}, status=400)

    success, message = register_user(username, password, baekjoon_id)
    
    if success:
        return Response({"message": message}, status=201)
    else:
        return Response({"error": message}, status=400)
    
@api_view(['POST'])
def login(request: Request) -> Response:
    data = request.data
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return Response({"error": "Missing required fields"}, status=400)

    success, message = login_user(username, password)
    
    if success:
        return Response({"message": message}, status=200)
    else:
        return Response({"error": message}, status=400)
    
@api_view(['POST'])
def delete(request: Request) -> Response:
    data = request.data
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return Response({"error": "Missing required fields"}, status=400)

    success, message = delete_user(username, password)
    
    if success:
        return Response({"message": message}, status=200)
    else:
        return Response({"error": message}, status=400)
    
@api_view(['POST'])
def update(request: Request) -> Response:
    data = request.data
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return Response({"error": "Missing required fields"}, status=400)
    
    success = True
    message = ""
    error_message = ""

    new_baekjoon_id = data.get('new_baekjoon_id')
    if new_baekjoon_id:
        tmp_success, tmp_message = change_baekjoon_id(username, password, new_baekjoon_id)
        success = success and tmp_success

        if tmp_success: message += tmp_message + " "
        else: error_message += tmp_message + " "

    if len(error_message) < 1 and len(message) < 1:
        success = False
        error_message = "No changes made"

    return Response(
        {"message": message, "error": error_message} if not success else {"message": message},
        status=200 if success else 400
    )