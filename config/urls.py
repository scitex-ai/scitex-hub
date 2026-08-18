# -*- coding: utf-8 -*-
# scitex-linter: skip-file
# Timestamp: 2026-03-09
# File: /home/ywatanabe/proj/scitex-hub/config/urls.py
"""
URL Configuration for SciTeX Hub project.
Organized into clear sections; helpers, API routes, and legacy redirects
are extracted into separate modules.
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from apps.infra.auth_app.oauth_views import userinfo as oauth_userinfo  # noqa: E402
from apps.infra.project_app.views import (
    accept_invitation,
    decline_invitation,
    project_create,
)
from apps.infra.public_app.views import healthz
from apps.workspace.repo_app.views.dispatch import root_dispatch
from apps.workspace.repo_app.views.index import current_project_view
from config.pwa import serve_root_static
from config.urls_helpers import RESERVED_PATHS, dev_module_view  # noqa: F401


def _scitex_cards_installed() -> bool:
    """True when the upstream cards package is importable.

    Mirrors the guarded THIRD_PARTY_APPS import in settings_shared.py so
    the /apps/cards/ mount and the installed app always agree.

    Checks the CANONICAL name first. ``scitex_todo`` is a deprecated alias
    of ``scitex_cards`` (renamed 2026-07-16) whose own DeprecationWarning
    says it "ships for one transition window only". Gating the mount on the
    alias made the board's existence depend on a package the upstream has
    already announced it will delete — and the failure is SILENT: when the
    alias goes, find_spec returns None, the mount is skipped, and
    /apps/cards/ quietly falls through to the username catch-all. No error,
    no log, the board simply stops existing.

    The alias is still accepted as a fallback so an environment pinned to
    the pre-rename dist keeps working; drop that arm once nothing ships it.
    """
    from importlib.util import find_spec

    return (
        find_spec("scitex_cards") is not None
        or find_spec("scitex_todo") is not None
    )


def _scitex_storage_installed() -> bool:
    """True when scitex-storage's _django app is importable.

    Mirrors the guarded THIRD_PARTY_APPS import in settings_shared.py so
    the /apps/storage/ mount and the installed app always agree. Gates on the
    _django submodule (the include target), so a scitex_storage present
    without its _django app doesn't mount a broken include.
    """
    from importlib.util import find_spec

    # find_spec of a SUBMODULE raises ModuleNotFoundError (rather than
    # returning None) when the PARENT package scitex_storage is absent
    # entirely — the state pytest CI hits (no install_apps, no package).
    # Treat that as not-installed instead of exploding the urlconf import.
    try:
        return find_spec("scitex_storage._django") is not None
    except ModuleNotFoundError:
        return False


urlpatterns = [
    # A2A protocol surface — canonical host: a2a.scitex.ai
    path("", include("apps.infra.a2a_app.urls")),
    # --- PWA (must be served from root for scope) ---
    #
    # Resolved through the staticfiles finders at REQUEST time, NOT pinned to a
    # document_root here. The old form passed
    # `settings.STATIC_ROOT or settings.STATICFILES_DIRS[0]`, but STATIC_ROOT is
    # a Path and therefore always truthy, so the source-tree fallback never ran
    # and both routes 404'd in every environment that had not run collectstatic
    # — silently, because pwa-register.ts swallows the failure. See config/pwa.py.
    path(
        "manifest.json",
        serve_root_static,
        {"path": "shared/manifest.json"},
        name="pwa-manifest",
    ),
    path(
        "sw.js",
        serve_root_static,
        {"path": "shared/sw.js"},
        name="pwa-sw",
    ),
    # --- Health ---
    path("healthz/", healthz, name="healthz"),
    # --- Root + Core Panes ---
    path("", root_dispatch, name="root"),
    path("chat/", root_dispatch, name="pane-chat", kwargs={"pane": "chat"}),
    path(
        "chat/<uuid:session_token>/",
        root_dispatch,
        name="pane-chat-session",
        kwargs={"pane": "chat"},
    ),
    path("console/", root_dispatch, name="pane-console", kwargs={"pane": "console"}),
    path("files/", root_dispatch, name="pane-files", kwargs={"pane": "editor"}),
    path("", include("apps.infra.public_app.urls")),
    path("apps/", include(("apps.workspace.tools_app.urls", "tools_app"))),
    # --- Admin ---
    path("admin/", admin.site.urls),
    # --- AI Setup (AI agent configuration hub) ---
    path("ai-setup/", include("apps.infra.accounts_app.urls_ai_setup")),
    # --- Auth ---
    path("accounts/", include(("apps.infra.accounts_app.urls", "accounts_app"))),
    path("auth/", include(("apps.infra.auth_app.urls", "auth_app"))),
    path("auth/social/", include("allauth.urls")),
    # --- OAuth2 Provider (Sign in with SciTeX) ---
    path(
        "oauth/userinfo/",
        oauth_userinfo,
        name="oauth-userinfo",
    ),
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    # --- Hub ---
    path("apps/home/api/", include("apps.workspace.repo_app.urls.api")),
    path("apps/home/", include("apps.workspace.repo_app.urls.index")),
    # --- Discovery ---
    path(
        "apps/discovery/",
        include(("apps.workspace.discovery_app.urls", "discovery_app")),
    ),
    # --- App modules (/apps/) ---
    path("apps/scholar/", include(("apps.workspace.scholar_app.urls", "scholar_app"))),
    path("apps/console/", include(("apps.workspace.console_app.urls", "console_app"))),
    path(
        "apps/figrecipe/",
        include(("apps.workspace.figrecipe_app.urls", "figrecipe_app")),
    ),
    path("apps/writer/", include(("apps.workspace.writer_app.urls", "writer_app"))),
    # NOTE: the raw ``path("writer/", include("scitex_writer._django.urls"))``
    # mount (card hub-mount-writer-django-app-20260707) was REMOVED as a P0
    # security fix (card sec-working-dir-passthrough-family, SITE 3). It
    # exposed the upstream writer handler set with NO login_required and a
    # @csrf_exempt POST/write dispatcher, reading a caller-supplied
    # ?working_dir= against ANY host directory — unauthenticated
    # cross-tenant read AND write. The SAME app is already served, gated
    # (login_required + server-side working_dir override), via the wrapper
    # at /apps/writer/{editor-v2,viewer-v2,v2/<endpoint>} above. With the
    # raw mount gone, /writer/ now falls through to the legacy 301 redirect
    # to /apps/writer/ (config/urls_legacy_redirects.py).
    # Upstream plugin apps live under /apps/<name>/, exactly like every other
    # app on the launcher (operator, 2026-07-13: "他のアプリと同じようにして
    # ください"). They used to be mounted at the bare root (/todo/, /storage/)
    # because that is where an upstream package's _django app "naturally" lands,
    # but that leaked an internal distinction — hub-native vs plugin — into the
    # URL a user reads. To a user these are simply apps. It also kept them out
    # of hub's own namespace, where a future top-level route could collide.
    #
    # Upstream scitex-todo's own contract-compliant Django board app
    # (phase 1: read-only). Only mounted when the package is importable —
    # mirror of the settings_shared.py guarded import. Per-request
    # workspace tenancy + the read-only gate are enforced by
    # apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware (whose
    # path prefix tracks this mount).
    *(
        [
            path("apps/cards/", include("scitex_cards._django.urls")),
            # Legacy mount: the board lived at /apps/todo/ before the Cards
            # rebrand (operator live review 2026-07-17). Permanent-redirect
            # the whole subtree so old links and pinned tiles keep working.
            re_path(
                r"^apps/todo/(?P<rest>.*)$",
                RedirectView.as_view(
                    url="/apps/cards/%(rest)s", permanent=True, query_string=True
                ),
            ),
        ]
        if _scitex_cards_installed()
        else []
    ),
    # Upstream scitex-storage's own contract-compliant Django app. Only
    # mounted when the package is importable — mirror of the
    # settings_shared.py guarded import. SECURITY: mounted through the
    # hub-side wrapper (apps.workspace.storage_app.urls), NOT the raw
    # upstream urls, so ?path= is login-gated and containment-validated to
    # the requester's own jail (card sec-working-dir-passthrough-family,
    # SITE 4 — the raw view scanned ANY host directory unauthenticated).
    *(
        [path("apps/storage/", include("apps.workspace.storage_app.urls"))]
        if _scitex_storage_installed()
        else []
    ),
    path(
        "apps/workspace/", include(("apps.infra.workspace_app.urls", "workspace_app"))
    ),
    path("apps/llm/", include(("apps.infra.llm_app.urls", "llm_app"))),
    path("apps/clew/", include(("apps.workspace.clew_app.urls", "clew_app"))),
    path("apps/store/", include(("apps.workspace.apps_app.urls", "apps_app"))),
    path("apps/comms/", include(("apps.workspace.comms_app.urls", "comms_app"))),
    # --- Dev-installed app modules (/apps/dev__<owner>__<repo>/) ---
    path("apps/dev__<str:rest>/", dev_module_view, name="dev_module_shell_apps"),
    # --- F0+F1 user-published apps (/apps/u/<module_name>/...) ---
    # operator picked A per lead msg 34a4b271; dispatcher in
    # apps.workspace.apps_app.urls_user_apps consumes the
    # _URL_PATTERNS_CACHE populated by app_loader at activation time.
    path(
        "apps/u/<str:module_name>/",
        include("apps.workspace.apps_app.urls_user_apps"),
    ),
    # --- Legacy redirects (/<app>/ → /apps/<app>/) ---
    path("", include("config.urls_legacy_redirects")),
    # --- Other apps ---
    path("dev/", include(("apps.workspace.dev_app.urls", "dev_app"))),
    path("apps/docs/", include(("apps.workspace.docs_app.urls", "docs_app"))),
    path(
        "integrations/",
        include(("apps.infra.integrations_app.urls", "integrations_app")),
    ),
    path(
        "organizations/",
        include(("apps.infra.organizations_app.urls", "organizations_app")),
    ),
    path("search/", include(("apps.infra.search_app.urls", "search_app"))),
    path("social/", include(("apps.infra.social_app.urls", "social_app"))),
    # --- API (/api/) ---
    path("api/", include("config.urls_api")),
    # --- Platform API ---
    path("platform/api/", include("apps.infra.platform_app.urls.api")),
    # --- Legacy: /project/api/check-name/ → now at /api/project/check-name/ ---
    path(
        "project/api/check-name/",
        RedirectView.as_view(
            url="/api/project/check-name/", permanent=True, query_string=True
        ),
    ),
    # --- Favicon ---
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/shared/images/favicon.png", permanent=True),
    ),
    # --- GitHub-like operations ---
    path("new/", project_create, name="project_create"),
    path(
        "invitations/<str:token>/accept/", accept_invitation, name="accept_invitation"
    ),
    path(
        "invitations/<str:token>/decline/",
        decline_invitation,
        name="decline_invitation",
    ),
    # --- Dev module shell ---
    path("dev__<str:rest>/", dev_module_view, name="dev_module_shell"),
    # --- Hub shortcuts ---
    path(
        "explore/",
        RedirectView.as_view(url="/apps/discovery/", permanent=True, query_string=True),
        name="hub_explore_redirect",
    ),
    path("current-project/", current_project_view, name="hub_current_project"),
    # --- GitHub-style catch-all (MUST BE LAST) ---
    path("<str:username>/", include(("apps.infra.project_app.urls", "user_projects"))),
]

# --- Debug-only ---
if settings.DEBUG:
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns.insert(
            -1,
            path("__reload__/", include("django_browser_reload.urls")),
        )
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# --- Production media fallback ---
if not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

# EOF
