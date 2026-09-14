"""Grouped results for the header command palette (GET /api/search/?q=)."""

from __future__ import annotations

from django.db.models import Q
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy

from apps.infra.project_app.models import Project, ProjectMembership

RESULTS_PER_GROUP = 5
MAX_QUERY_LENGTH = 100

SETTINGS_PAGES = (
    (_("Profile"), "accounts_app:profile_edit", "fas fa-user"),
    (_("Appearance"), "accounts_app:appearance", "fas fa-palette"),
    (_("Git platforms"), "accounts_app:git_integrations", "fab fa-git-alt"),
    (_("AI providers"), "accounts_app:ai_providers", "fas fa-robot"),
    (_("AI usage"), "llm_app:usage_dashboard", "fas fa-chart-bar"),
    (_("MCP tools"), "accounts_app:mcp_tools", "fas fa-puzzle-piece"),
    (_("SSH keys"), "accounts_app:ssh_keys", "fas fa-key"),
    (_("API keys"), "accounts_app:api_keys", "fas fa-code"),
    (_("Privacy & Analytics"), "accounts_app:privacy_settings", "fas fa-shield-alt"),
    (_("Payment method"), "accounts_app:billing", "fas fa-credit-card"),
    (_("Project Health"), "accounts_app:repository_health", "fas fa-heartbeat"),
)


def _matches(query: str, *candidates) -> bool:
    folded_query = query.casefold()
    return any(folded_query in str(text).casefold() for text in candidates if text)


def _english(text) -> str:
    with translation.override("en"):
        return str(text)


def _result(title, url, icon, subtitle="") -> dict:
    return {"title": str(title), "subtitle": str(subtitle), "url": url, "icon": icon}


def search_apps(request, query: str) -> list[dict]:
    from apps.workspace.apps_app.views.launcher import _build_tiles as launcher_tiles

    results = []
    for tile in launcher_tiles(request):
        if not tile["is_launchable"]:
            continue
        shown_label = pgettext("app name", tile["label"])
        if _matches(query, tile["label"], shown_label, tile["name"]):
            results.append(_result(shown_label, tile["launch_url"], tile["icon_fa"]))
        if len(results) == RESULTS_PER_GROUP:
            break
    return results


def _projects_matching(query: str):
    return Project.objects.filter(
        Q(name__icontains=query) | Q(slug__icontains=query)
    ).select_related("owner", "org_owner")


def _project_result(project: Project) -> dict:
    return _result(
        project.name,
        project.get_absolute_url(),
        "fas fa-lock" if project.visibility == "private" else "fas fa-book",
        f"{project.effective_owner_slug}/{project.slug}",
    )


def _member_project_ids(user):
    return ProjectMembership.objects.filter(user=user).values("project_id")


def search_my_projects(user, query: str) -> list[dict]:
    if not user.is_authenticated:
        return []
    projects = _projects_matching(query).filter(
        Q(owner=user) | Q(id__in=_member_project_ids(user))
    )
    return [_project_result(p) for p in projects.order_by("-updated_at")[:RESULTS_PER_GROUP]]


def search_public_projects(user, query: str) -> list[dict]:
    projects = _projects_matching(query).filter(visibility="public")
    if user.is_authenticated:
        # Already listed under "My projects".
        projects = projects.exclude(owner=user).exclude(id__in=_member_project_ids(user))
    return [_project_result(p) for p in projects.order_by("-updated_at")[:RESULTS_PER_GROUP]]


def search_docs(query: str) -> list[dict]:
    from apps.workspace.docs_app.views import DOCS_PAGES

    docs_url = reverse("docs_app:index")
    results = []
    for page in DOCS_PAGES:
        if _matches(query, page["label"], _english(page["label"]), page["slug"]):
            results.append(_result(page["label"], f"{docs_url}#{page['slug']}", page["icon"]))
        if len(results) == RESULTS_PER_GROUP:
            break
    return results


def search_settings(user, query: str) -> list[dict]:
    if not user.is_authenticated:
        return []
    results = []
    for label, url_name, icon in SETTINGS_PAGES:
        if _matches(query, label, _english(label)):
            results.append(_result(label, reverse(url_name), icon))
        if len(results) == RESULTS_PER_GROUP:
            break
    return results


def grouped_search_results(request, query: str) -> list[dict]:
    query = query.strip()[:MAX_QUERY_LENGTH]
    if not query:
        return []
    user = request.user
    groups = (
        ("apps", _("Apps"), search_apps(request, query)),
        ("my_projects", pgettext_lazy("app name", "My Projects"), search_my_projects(user, query)),
        ("public_projects", pgettext_lazy("app name", "Public Projects"), search_public_projects(user, query)),
        ("docs", _("Docs"), search_docs(query)),
        ("settings", _("Settings"), search_settings(user, query)),
    )
    return [
        {"key": key, "label": str(label), "results": results}
        for key, label, results in groups
        if results
    ]
