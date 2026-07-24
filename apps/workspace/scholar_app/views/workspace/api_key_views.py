#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# API key management views for Scholar app

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import logging

from ...models import UserPreference

logger = logging.getLogger(__name__)


@login_required
def api_key_management(request):
    """API key management dashboard for users"""
    user_prefs = UserPreference.get_or_create_for_user(request.user)

    if request.method == "POST":
        # Handle API key updates
        source = request.POST.get("source")
        api_key = request.POST.get("api_key", "").strip()

        if source == "unpaywall":
            # Special case for unpaywall (uses email)
            user_prefs.unpaywall_email = api_key
            user_prefs.save()
            messages.success(request, f"Unpaywall email updated successfully!")
        elif source in ["pubmed", "google_scholar", "semantic_scholar", "crossref"]:
            if api_key:
                user_prefs.set_api_key(source, api_key)
                messages.success(
                    request,
                    f"{source.replace('_', ' ').title()} API key updated successfully!",
                )
            else:
                # Clear the API key
                user_prefs.set_api_key(source, "")
                messages.info(
                    request, f"{source.replace('_', ' ').title()} API key cleared."
                )
        else:
            messages.error(request, "Invalid API source specified.")

        return redirect("scholar_app:api_keys")

    # Get current API key status
    api_status = {
        "pubmed": user_prefs.has_api_key("pubmed"),
        "google_scholar": user_prefs.has_api_key("google_scholar"),
        "semantic_scholar": user_prefs.has_api_key("semantic_scholar"),
        "crossref": user_prefs.has_api_key("crossref"),
        "unpaywall": bool(user_prefs.unpaywall_email),
    }

    # API usage statistics
    usage_stats = user_prefs.api_usage_count or {}

    context = {
        "api_status": api_status,
        "usage_stats": usage_stats,
        "unpaywall_email": user_prefs.unpaywall_email,
        "missing_keys": user_prefs.get_missing_api_keys(),
    }

    return render(request, "scholar_app/api_key_management.html", context)


@login_required
@require_http_methods(["POST"])
def test_api_key(request):
    """Test if an API key is valid"""
    try:
        data = json.loads(request.body)
        source = data.get("source")
        api_key = data.get("api_key")

        if not source or not api_key:
            return JsonResponse(
                {"success": False, "error": "Missing source or API key"}
            )

        # Test the API key with a simple request
        test_result = _test_api_key_validity(source, api_key)

        return JsonResponse(
            {
                "success": test_result["valid"],
                "message": test_result["message"],
                "rate_limit": test_result.get("rate_limit"),
            }
        )

    except Exception as e:
        logger.error(f"Error testing API key: {e}")
        return JsonResponse({"success": False, "error": "Failed to test API key"})


def _test_api_key_validity(source, api_key):
    """Test if an API key is valid for a specific source"""
    import requests

    try:
        if source == "pubmed":
            # Test NCBI API key with a simple search
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": "test",
                "retmax": 1,
                "retmode": "json",
                "api_key": api_key,
            }
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if "esearchresult" in data:
                    return {
                        "valid": True,
                        "message": "PubMed API key is valid",
                        "rate_limit": "10 requests/second with API key",
                    }

            return {"valid": False, "message": "Invalid PubMed API key"}

        elif source == "semantic_scholar":
            # Test Semantic Scholar API key
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            headers = {"x-api-key": api_key}
            params = {"query": "test", "limit": 1}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                return {
                    "valid": True,
                    "message": "Semantic Scholar API key is valid",
                    "rate_limit": "100 requests/5 minutes with API key",
                }

            return {"valid": False, "message": "Invalid Semantic Scholar API key"}

        elif source == "crossref":
            # Test Crossref API (usually doesn't require key but can provide better rate limits)
            url = "https://api.crossref.org/works"
            headers = {"User-Agent": f"SciTeX-Scholar (mailto:{api_key})"}
            params = {"query": "test", "rows": 1}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                return {
                    "valid": True,
                    "message": "Crossref contact email is valid",
                    "rate_limit": "Polite rate limiting applied",
                }

            return {"valid": False, "message": "Invalid Crossref contact email"}

        else:
            return {"valid": False, "message": f"Testing not implemented for {source}"}

    except requests.RequestException as e:
        return {"valid": False, "message": f"Network error: {str(e)}"}
    except Exception as e:
        return {"valid": False, "message": f"Error: {str(e)}"}


@login_required
def api_usage_stats(request):
    """Get API usage statistics for the user"""
    user_prefs = UserPreference.get_or_create_for_user(request.user)

    usage_data = {
        "total_requests": (
            sum(user_prefs.api_usage_count.values())
            if user_prefs.api_usage_count
            else 0
        ),
        "by_source": user_prefs.api_usage_count or {},
        "rate_limits": user_prefs.api_rate_limit_reset or {},
    }

    return JsonResponse(usage_data)
