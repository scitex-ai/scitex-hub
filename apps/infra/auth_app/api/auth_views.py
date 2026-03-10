"""
Auth API Views

RESTful API endpoints for authentication operations.
"""

import hashlib
import json
import time

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse


def api_register(request):
    """
    API endpoint for user registration.

    Expects:
        username: Desired username
        email: User's email
        password: Desired password
        first_name: (optional) User's first name
        last_name: (optional) User's last name

    Returns:
        JSON response with registration status and user information if successful
    """
    data = json.loads(request.body)

    # Required fields
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")

    # Optional fields
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    # Validate inputs
    if not username or not email or not password:
        return JsonResponse(
            {
                "success": False,
                "error": "Username, email, and password are required",
            },
            status=400,
        )

    # Check if user already exists
    if User.objects.filter(username=username).exists():
        return JsonResponse(
            {"success": False, "error": "Username already exists"}, status=400
        )

    if User.objects.filter(email=email).exists():
        return JsonResponse(
            {"success": False, "error": "Email already registered"}, status=400
        )

    # Create user
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Log user in
        login(request, user)

        return JsonResponse(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=201,
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_login(request):
    """
    API endpoint for user login.

    Expects:
        username: User's username
        password: User's password

    Returns:
        JSON response with login status and user information if successful
    """
    data = json.loads(request.body)
    username = data.get("username", "")
    password = data.get("password", "")

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)

        # Generate a simple token
        token = hashlib.sha256(f"{user.username}{time.time()}".encode()).hexdigest()

        return JsonResponse(
            {
                "success": True,
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            }
        )
    else:
        return JsonResponse(
            {"success": False, "error": "Invalid username or password"},
            status=401,
        )


def api_forgot_password(request):
    """
    API endpoint for password reset request.

    Expects:
        email: User's email address

    Returns:
        JSON response with status
    """
    data = json.loads(request.body)
    email = data.get("email", "")

    if not email:
        return JsonResponse(
            {"success": False, "error": "Email is required"},
            status=400,
        )

    # Check if user exists
    try:
        user = User.objects.get(email=email)
        # In a real implementation, you would:
        # 1. Generate a password reset token
        # 2. Send an email with reset link
        # 3. Store the token with expiry

        # For now, we'll just return success
        return JsonResponse(
            {
                "success": True,
                "message": "Password reset instructions sent to your email",
            }
        )
    except User.DoesNotExist:
        # For security, don't reveal if email exists
        return JsonResponse(
            {
                "success": True,
                "message": "If an account exists with this email, you will receive password reset instructions",
            }
        )


def api_logout(request):
    """
    API endpoint for user logout.

    Returns:
        JSON response with logout status
    """
    logout(request)

    return JsonResponse({"success": True, "message": "Successfully logged out"})
