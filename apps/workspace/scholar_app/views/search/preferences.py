#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/views/search/preferences.py
"""
Scholar App - User Preferences Module

Views for managing user search preferences and settings.
Extracted from monolithic views.py for better modularity.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from scitex import logging
from ...models import UserPreference

# Set up logger
logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def get_user_preferences(request):
    """Get user's search preferences"""
    try:
        preferences = UserPreference.get_or_create_for_user(request.user)
        return JsonResponse(
            {
                "status": "success",
                "preferences": {
                    "preferred_sources": preferences.preferred_sources,
                    "default_sort_by": preferences.default_sort_by,
                    "default_filters": preferences.default_filters,
                    "results_per_page": preferences.results_per_page,
                    "show_abstracts": preferences.show_abstracts,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_user_preferences(request):
    """Save user's search preferences"""
    try:
        data = json.loads(request.body)
        preferences = UserPreference.get_or_create_for_user(request.user)

        # Update specific preference fields
        if "preferred_sources" in data:
            preferences.preferred_sources = data["preferred_sources"]

        if "default_sort_by" in data:
            preferences.default_sort_by = data["default_sort_by"]

        if "default_filters" in data:
            preferences.default_filters = data["default_filters"]

        if "results_per_page" in data:
            preferences.results_per_page = data["results_per_page"]

        if "show_abstracts" in data:
            preferences.show_abstracts = data["show_abstracts"]

        preferences.save()

        return JsonResponse(
            {"status": "success", "message": "Preferences saved successfully"}
        )

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error saving user preferences: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_source_preferences(request):
    """Save source selection preferences (for both logged in and visitor users)"""
    try:
        data = json.loads(request.body)
        sources = data.get("sources", {})

        if request.user.is_authenticated:
            # Save to database for logged in users
            preferences = UserPreference.get_or_create_for_user(request.user)
            preferences.preferred_sources = sources
            preferences.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Source preferences saved to profile",
                    "saved_to": "database",
                }
            )
        else:
            # For visitor users, return success (they can use localStorage)
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Source preferences noted (login to save permanently)",
                    "saved_to": "session",
                }
            )

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error saving source preferences: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
