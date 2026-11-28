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
from apps.workspace.apps_app.views import app_create as app_create_views
from apps.workspace.apps_app.views import first_run as first_run_views
from apps.workspace.my_projects_app.views.dispatch import root_dispatch
from apps.workspace.my_projects_app.views.index import current_project_view
from config import security_views
from config.pwa import serve_root_static
from config.urls_helpers import RESERVED_PATHS, dev_module_view  # noqa: F401
from config.urls_mounts import (  # noqa: E402
    _figrecipe_old_direct_patterns,
    _live_paper_patterns,
    _scholar_old_direct_patterns,
    _sdk_creator_patterns,
    _writer_old_direct_patterns,
)

urlpatterns = [
    # Language selection. Django's set_language view writes the chosen language
    # to the session/cookie and redirects back to `next`. LocaleMiddleware then
    # prefers that over the Accept-Language header on every later request, which
    # is the whole point: automatic detection is the DEFAULT, and this is how a
    # visitor overrides it when the guess is wrong.
    #
    # Mounted at a non-i18n prefix deliberately: the endpoint must be reachable
    # identically in every language, so it must not itself be language-prefixed.
    path("i18n/", include("django.conf.urls.i18n")),
    # Security posture endpoints (config/security_views.py).
    path(".well-known/security.txt", security_views.security_txt, name="security_txt"),
    path("sitemap.xml", security_views.sitemap_xml, name="sitemap_xml"),
    path("api/csp-report/", security_views.csp_report, name="csp_report"),
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
    # /apps/ is the APPS HOME (launcher grid) for logged-in users — the same
    # surface that lives at the root, NOT the App Store (/apps/store/). The old
    # 301 here -> /apps/store/ made the landing page's "Apps" button land on the
    # store (operator: "apps should be the home of the apps"). root_dispatch
    # handles the split: anonymous -> landing, logged-in -> launcher (apps
    # home). Placed before the tools include so /apps/tools/ still resolves.
    path("apps/", root_dispatch, name="apps_home"),
    path(
        "apps/getting-started/dismiss/",
        first_run_views.dismiss,
        name="first_run_dismiss",
    ),
    path(
        "apps/getting-started/reshow/",
        first_run_views.reshow,
        name="first_run_reshow",
    ),
    path(
        "apps/getting-started/<str:step_key>/",
        first_run_views.follow_step,
        name="first_run_step",
    ),
    path("apps/create/", app_create_views.create_page, name="app_create"),
    path(
        "apps/create/<str:slug>/",
        app_create_views.workspace_page,
        name="app_workspace",
    ),
    path(
        "apps/create/<str:slug>/api/chat/",
        app_create_views.api_chat,
        name="app_workspace_chat",
    ),
    path(
        "apps/create/<str:slug>/api/apply/",
        app_create_views.api_apply,
        name="app_workspace_apply",
    ),
    path(
        "apps/create/<str:slug>/api/run/",
        app_create_views.api_run,
        name="app_workspace_run",
    ),
    path("apps/", include(("apps.workspace.tools_app.urls", "tools_app"))),
    # --- App Creator wizard (scitex-sdk) ---
    # The SDK owns the wizard (STARTERS SSOT + `scitex_sdk.creator.urls`);
    # the hub only mounts it. Canonical home is /apps/sdk/ (moved from
    # /apps/new/; the old path is a permanent redirect in
    # urls_legacy_redirects.py, following the PR #1023 pattern).
    # The hub's own /apps/create/* project flow above is the
    # fallback workspace backend.
    path(
        "apps/sdk/",
        include((_sdk_creator_patterns(), "scitex_sdk_creator")),
    ),
    # --- Admin ---
    # Path is configurable (ADMIN_URL_PATH); access is staff-only, enforced
    # by config.security_headers.AdminAccessMiddleware (404 for anyone else).
    path(settings.ADMIN_URL_PATH, admin.site.urls),
    # --- AI Setup (AI agent configuration hub) ---
    path("ai-setup/", include("apps.infra.accounts_app.urls_ai_setup")),
    # --- Auth ---
    path(
        "accounts/settings/spend/",
        include(("apps.infra.spend_app.urls", "spend_app")),
    ),
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
    # --- My Projects ---
    path(
        "apps/my-projects/api/",
        include("apps.workspace.my_projects_app.urls.api"),
    ),
    path("apps/my-projects/", include("apps.workspace.my_projects_app.urls.index")),
    # --- Public Projects ---
    path(
        "apps/public-projects/",
        include(("apps.workspace.public_projects_app.urls", "public_projects_app")),
    ),
    # --- App modules (/apps/) ---
    # Scholar cutover (CCT 2760) + RED START (CCT 2806, binding):
    # /apps/scholar/ serves the LEAF ONLY (login-gated wrapper in
    # scholar_app/urls/scholar_django.py) — the plain hub-side routes went
    # dark first (404) and the plain route is relit ONLY by the working leaf
    # plugin. The pre-cutover hub-native routes are NOT on the user path
    # anymore. CCT 2795: NO /v2/ alias remains.
    # Plain include (no app_name tuple) ON PURPOSE: the leaf carries its own
    # namespaces and Django only propagates them to reverse() through a
    # namespace-transparent outer mount (see scholar_app/urls/__init__.py).
    path("apps/scholar/", include("apps.workspace.scholar_app.urls")),
    # Live Paper viewer (scitex-live-paper leaf 0.2.0): same gated wrapper
    # shape as scholar — per-request BundleContext via mount(resolver=...).
    # Single namespace registration (`live_paper`, from the leaf's mount
    # tuple); the patterns go through the shared login wrapper so the
    # whole tree is gated.
    path("apps/live-paper/", include(_live_paper_patterns())),
    # Journal (agentic-journal leaf, first release 0.1.0a0): same gated
    # wrapper shape as scholar — leaf views carry no auth of their own.
    # Canonical home is /apps/agentic-journal/ (leaf slug contract); the
    # old /apps/journal/ is a permanent redirect in
    # urls_legacy_redirects.py.
    path("apps/agentic-journal/", include("apps.workspace.journal_app.urls")),
    # OPERATOR ROUTE RULE (CCT 2763/2764) + RED START (CCT 2806), ALL apps,
    # same pattern: hub-side app routes move to apps/<app>/old-direct as the
    # parity reference, and old-direct NEVER ships in production — dev-gated,
    # no launcher tiles/links, no user path, deleted outright once parity
    # closes. Scholar was the first instance; figrecipe and writer follow the identical
    # pattern as of their cutovers below (console follows as it migrates;
    # same mount shape, same gate, same no-tiles rule — no
    # registry/manifest entry exists for
    # old-direct by construction, so no tile can render it; no /v2/ alias).
    *_scholar_old_direct_patterns(),
    path("apps/console/", include(("apps.workspace.console_app.urls", "console_app"))),
    # FigRecipe cutover (CCT-2784, Scholar #1074 template) + RED START
    # (CCT 2806, binding): /apps/figrecipe/ serves the LEAF ONLY
    # (login-gated wrapper in figrecipe_app/urls/figrecipe_django.py) — the
    # plain hub-side routes went dark first (404) and the plain route is
    # relit ONLY by the working leaf plugin. The pre-cutover hub-native
    # routes (adapter page + SITE-2 guarded API) are NOT on the user path
    # anymore: they live ONLY at /apps/figrecipe/old-direct/ in dev.
    # Old-direct is spliced FIRST on purpose (see _figrecipe_old_direct_patterns:
    # the leaf's <path:endpoint> catch-all would otherwise swallow it).
    # Plain include (no app_name tuple) ON PURPOSE: the leaf carries its own
    # namespace and Django only propagates it to reverse() through a
    # namespace-transparent outer mount (see figrecipe_app/urls/__init__.py).
    # No alias mount is added (CCT 2795 lesson): the leaf's hosted-compat
    # names travel inside the single mount. The generic plugin mount keeps
    # skipping this route via _route_taken (the bespoke default still takes
    # it), so the leaf urlconf is never double-mounted.
    *_figrecipe_old_direct_patterns(),
    path("apps/figrecipe/", include("apps.workspace.figrecipe_app.urls")),
    # Writer: /apps/writer/ is served by the GENERIC plugin mount
    # (plugin_urlpatterns at the bottom of this file) — whatever routes the
    # writer leaf's own urlconf declares, login-gated by its manifest
    # mount_policy, below the hub's scitex-writer floor never mounted. The
    # hub names no writer route: the leaf authorizes every request itself
    # through scitex_sdk.host (project identity, storage root, write grant,
    # CSRF), so the old hub-side SITE-3 wrapper and its route-name allowlist
    # are gone. Only the dev-only old-direct reference stays hub-native; the
    # generic mount hoists it ahead of the leaf (whose <path:endpoint>
    # catch-all would otherwise swallow it).
    *_writer_old_direct_patterns(),
    # NOTE: the old raw ``path("writer/", include("scitex_writer._django.urls"))``
    # mount (card sec-working-dir-passthrough-family, SITE 3) served a leaf
    # that honoured a caller-supplied ?working_dir= with no login. /writer/
    # now falls through to the legacy 301 redirect to /apps/writer/
    # (config/urls_legacy_redirects.py).
    # Upstream plugin apps live under /apps/<name>/, exactly like every other
    # app on the launcher (operator, 2026-07-13: "他のアプリと同じようにして
    # ください"). They used to be mounted at the bare root (/todo/, /storage/)
    # because that is where an upstream package's _django app "naturally" lands,
    # but that leaked an internal distinction — hub-native vs plugin — into the
    # URL a user reads. To a user these are simply apps. It also kept them out
    # of hub's own namespace, where a future top-level route could collide.
    #
    # Agents, Cards and Storage mount EXCLUSIVELY through the generic plugin
    # mount (plugin_urlpatterns at the bottom of this file: the plugin's own
    # urlconf + manifest tile, login-wrapped and mount-policy-guarded without
    # app-specific code). There are no bespoke hub mounts here on purpose —
    # the thin-hub rule forbids the hub knowing what a plugin provides.
    # Legacy mount: the board lived at /apps/todo/ before the Cards
    # rebrand (operator live review 2026-07-17). Permanent-redirect
    # the whole subtree so old links and pinned tiles keep working.
    re_path(
        r"^apps/todo/(?P<rest>.*)$",
        RedirectView.as_view(
            url="/apps/cards/%(rest)s", permanent=True, query_string=True
        ),
    ),
    # Same pattern for the Agents rebrand (operator 2026-10-22): the
    # dashboard lived at /apps/agents/ before the rename to
    # /apps/agent-container/. Permanent-redirect the whole subtree.
    re_path(
        r"^apps/agents/(?P<rest>.*)$",
        RedirectView.as_view(
            url="/apps/agent-container/%(rest)s", permanent=True, query_string=True
        ),
    ),
    path(
        "apps/workspace/", include(("apps.infra.workspace_app.urls", "workspace_app"))
    ),
    path("apps/llm/", include(("apps.infra.llm_app.urls", "llm_app"))),
    path("apps/store/", include(("apps.workspace.apps_app.urls", "apps_app"))),
    path("apps/comms/", include(("apps.workspace.comms_app.urls", "comms_app"))),
    path("apps/files/", include(("apps.workspace.files_app.urls", "files_app"))),
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
        # Non-permanent so a later icon change is not pinned by a cached 301.
        RedirectView.as_view(
            url="/static/shared/images/favicons/favicon.png?v=7", permanent=False
        ),
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
    path("current-project/", current_project_view, name="hub_current_project"),
    # --- GitHub-style catch-all (MUST BE LAST) ---
    path("<str:username>/", include(("apps.infra.project_app.urls", "user_projects"))),
]

# --- Plugin apps (pip-installed, scitex.apps entry point) ---
# First so a hub catch-all cannot swallow them; routes the hub serves are skipped.
from apps.workspace.apps_app.services.plugin_apps import plugin_urlpatterns  # noqa: E402

urlpatterns[:0] = plugin_urlpatterns(urlpatterns)

# --- Leaf REST APIs (scitex.apis entry point) at /api/v1/<package>/ ---
# Generic: scitex-sdk admits every trusted plugin and serves its declared
# operations (scopes, problem+json, pagination, idempotency) through the host
# hooks in settings. First, so no hub route shadows a leaf operation; the
# problem+json 404 for other api/v1 paths goes just before the username
# catch-all, after the hub's own legacy api/v1 routes in config.urls_api.
from scitex_sdk.app.api_serve import api_not_found_pattern, api_urlpatterns  # noqa: E402

urlpatterns[:0] = api_urlpatterns(catch_all=False)
urlpatterns.insert(len(urlpatterns) - 1, api_not_found_pattern())

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
