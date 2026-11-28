#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth JSON endpoints used by the signup and sign-in pages.

The e-mail code endpoints live in :mod:`.otp_api_views` and are re-exported
here so the URLconf keeps one import.
"""

import json
import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .otp_api_views import resend_otp_api, verify_email_api  # noqa: F401

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def check_username_availability(request):
    """API endpoint to check if a username is available for registration"""
    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()

        if not username:
            return JsonResponse(
                {"available": False, "error": "Username is required."}, status=400
            )

        # Check if username is too short
        if len(username) < 1:
            return JsonResponse(
                {"available": False, "error": "Username must be at least 1 character."}
            )

        # Check if username is too long
        if len(username) > 39:
            return JsonResponse(
                {"available": False, "error": "Username cannot exceed 39 characters."}
            )

        # Reserved usernames (must match forms.py)
        reserved_usernames = [
            "admin",
            "administrator",
            "api",
            "auth",
            "billing",
            "blog",
            "cloud",
            "code",
            "core",
            "dashboard",
            "dev",
            "docs",
            "help",
            "login",
            "logout",
            "project",
            "projects",
            "scholar",
            "signup",
            "static",
            "support",
            "terms",
            "privacy",
            "about",
            "contact",
            "settings",
            "user",
            "users",
            "viz",
            "writer",
            "root",
            "system",
            "scitex",
        ]

        if username.lower() in reserved_usernames:
            return JsonResponse(
                {"available": False, "error": "This username is reserved."}
            )

        # Check if username already exists (case-insensitive)
        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse(
                {"available": False, "error": "This username is already taken."}
            )

        # If we get here, username is available
        return JsonResponse({"available": True, "message": "Username is available!"})

    except json.JSONDecodeError:
        return JsonResponse(
            {"available": False, "error": "Invalid JSON data."}, status=400
        )
    except Exception as e:
        logger.error(f"Error checking username availability: {str(e)}")
        return JsonResponse(
            {"available": False, "error": "An error occurred. Please try again."},
            status=500,
        )


@csrf_exempt
@require_http_methods(["POST"])
def verify_credentials_api(request):
    """API endpoint for remote credential verification (orochi SSO fallback).

    Verifies username/password without creating a session.
    Returns user info on success for the remote app to create a local account.
    """
    from django.contrib.auth import authenticate as django_authenticate

    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return JsonResponse(
                {"success": False, "error": "Credentials required."}, status=400
            )

        # Allow login with email
        if "@" in username:
            try:
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Invalid credentials."}, status=401
                )

        user = django_authenticate(username=username, password=password)
        if user is None or not user.is_active:
            return JsonResponse(
                {"success": False, "error": "Invalid credentials."}, status=401
            )

        return JsonResponse(
            {
                "success": True,
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "name": user.get_full_name() or user.username,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)


@require_http_methods(["POST"])
def check_email_academic(request):
    """API endpoint: is this email from a recognized academic domain?

    Read-only hint for the signup form (academic pricing eligibility).
    Decides nothing about the account; the list is the JP academic list in
    :mod:`apps.infra.auth_app.models` (same checker the registration grant
    path re-exports).
    """
    try:
        data = json.loads(request.body)
        email = (data.get("email") or "").strip()
        if not email or "@" not in email:
            return JsonResponse({"academic": False}, status=200)
        from .models import is_japanese_academic_email

        return JsonResponse({"academic": bool(is_japanese_academic_email(email))})
    except json.JSONDecodeError:
        return JsonResponse({"academic": False}, status=200)
