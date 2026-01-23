from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q
from apps.project_app.models import Project
from .models import GlobalSearchQuery


def unified_search(request):
    """
    Unified search across users, repositories, and more.

    Query params:
    - q: search query
    - type: all|users|repositories|code|papers
    """
    query = request.GET.get("q", "").strip()
    search_type = request.GET.get("type", "all")

    if not query:
        return render(
            request,
            "search_app/search_results.html",
            {
                "query": "",
                "search_type": search_type,
                "users": [],
                "repositories": [],
                "total_results": 0,
            },
        )

    # Log search query
    search_log = GlobalSearchQuery.objects.create(
        query=query,
        search_type=search_type,
        user=request.user if request.user.is_authenticated else None,
    )

    results = {}
    total_results = 0

    # Search users
    if search_type in ["all", "users"]:
        users = search_users(query, request.user)
        results["users"] = users
        total_results += len(users)

    # Search repositories
    if search_type in ["all", "repositories"]:
        repositories = search_repositories(query, request.user)
        results["repositories"] = repositories
        total_results += len(repositories)

    # Update results count
    search_log.results_count = total_results
    search_log.save()

    context = {
        "query": query,
        "search_type": search_type,
        "users": results.get("users", []),
        "repositories": results.get("repositories", []),
        "total_results": total_results,
    }

    return render(request, "search_app/search_results.html", context)


def search_users(query, current_user=None, limit=20):
    """
    Search for users by username, name, institution, or research interests.
    Uses PostgreSQL full-text search for better relevance.
    """
    # Basic Q-based search (works with SQLite for development)
    users = (
        User.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(profile__institution__icontains=query)
            | Q(profile__research_interests__icontains=query)
            | Q(profile__bio__icontains=query)
        )
        .select_related("profile")
        .distinct()[:limit]
    )

    # Format results
    results = []
    for user in users:
        profile = getattr(user, "profile", None)
        results.append(
            {
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "avatar_url": profile.avatar.url
                if profile and profile.avatar
                else None,
                "institution": profile.institution if profile else "",
                "bio": profile.bio[:100] if profile and profile.bio else "",
                "url": f"/{user.username}/",
            }
        )

    return results


def search_repositories(query, current_user=None, limit=20):
    """
    Search for repositories by name, description, or hypotheses.
    Respects privacy: only shows public repos or repos user has access to.
    """
    # Base queryset with optimizations
    repos = Project.objects.select_related("owner").prefetch_related(
        "memberships", "stars"
    )

    # Apply visibility filter
    if current_user and current_user.is_authenticated:
        # Show: public repos + user's own repos + repos they collaborate on
        repos = repos.filter(
            Q(visibility="public")
            | Q(owner=current_user)
            | Q(memberships__user=current_user)
        ).distinct()
    else:
        # Visitor: only public repos
        repos = repos.filter(visibility="public")

    # Apply search filter
    repos = repos.filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(hypotheses__icontains=query)
    )[:limit]

    # Format results
    results = []
    for repo in repos:
        # Get star count
        from apps.social_app.models import RepositoryStar

        star_count = RepositoryStar.get_star_count(repo)

        results.append(
            {
                "name": repo.name,
                "slug": repo.slug,
                "owner_username": repo.owner.username,
                "description": repo.description[:150] if repo.description else "",
                "visibility": repo.visibility,
                "star_count": star_count,
                "updated_at": repo.updated_at,
                "url": repo.get_absolute_url(),
            }
        )

    return results


def autocomplete(request):
    """
    Autocomplete API for search suggestions.
    Returns users and repositories matching the query.
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"suggestions": []})

    suggestions = []

    # Search users (top 5)
    users = User.objects.filter(
        Q(username__istartswith=query)
        | Q(first_name__istartswith=query)
        | Q(last_name__istartswith=query)
    ).select_related("profile")[:5]

    for user in users:
        suggestions.append(
            {
                "type": "user",
                "icon": "👤",
                "title": user.get_full_name() or user.username,
                "subtitle": f"@{user.username}",
                "url": f"/{user.username}/",
            }
        )

    # Search repositories (top 5)
    repos = Project.objects.select_related("owner").filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )

    # Filter by visibility
    if request.user.is_authenticated:
        repos = repos.filter(
            Q(visibility="public")
            | Q(owner=request.user)
            | Q(memberships__user=request.user)
        ).distinct()
    else:
        repos = repos.filter(visibility="public")

    repos = repos[:5]

    for repo in repos:
        visibility_icon = "🔒" if repo.visibility == "private" else "📘"
        suggestions.append(
            {
                "type": "repository",
                "icon": visibility_icon,
                "title": repo.name,
                "subtitle": f"{repo.owner.username}/{repo.slug}",
                "url": repo.get_absolute_url(),
            }
        )

    return JsonResponse({"suggestions": suggestions})


def search_stats(request):
    """Get search statistics and trending queries"""
    popular_queries = GlobalSearchQuery.get_popular_queries(limit=10)

    return JsonResponse(
        {
            "popular_queries": list(popular_queries),
            "total_searches": GlobalSearchQuery.objects.count(),
        }
    )
