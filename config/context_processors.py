#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context processors for adding global template variables.
"""

import os
from pathlib import Path

from django.conf import settings

from config import branding

# Cache the build_id to avoid repeated file system calls
_cached_build_id = None
_last_check_time = 0


def cache_buster(request):
    """
    Add a cache-busting parameter for static files in development.
    In production, use proper static file versioning.

    In development, this checks the modification time of JS directories
    and updates when they change.
    """
    global _cached_build_id, _last_check_time

    if settings.DEBUG:
        import time

        current_time = time.time()

        # Check files every 2 seconds to avoid excessive file system calls
        if current_time - _last_check_time > 2:
            try:
                # Check modification time of key JS and CSS directories
                static_dirs = [
                    Path(settings.BASE_DIR)
                    / "apps/workspace/console_app/static/console_app/js",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/figrecipe_app/static/figrecipe_app/ts",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/writer_app/static/writer_app/js",
                    Path(settings.BASE_DIR) / "static/shared/js",
                    Path(settings.BASE_DIR) / "static/shared/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/writer_app/static/writer_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/scholar_app/static/scholar_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/console_app/static/console_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/infra/public_app/static/public_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/docs_app/static/docs_app/css",
                ]
                max_mtime = 0
                for static_dir in static_dirs:
                    if static_dir.exists():
                        for static_file in static_dir.rglob("*"):
                            if static_file.suffix in (".js", ".css"):
                                mtime = static_file.stat().st_mtime
                                if mtime > max_mtime:
                                    max_mtime = mtime
                _cached_build_id = (
                    str(int(max_mtime)) if max_mtime else str(int(current_time))
                )
            except Exception:
                _cached_build_id = str(int(current_time))

            _last_check_time = current_time

        build_id = _cached_build_id or str(int(current_time))
    else:
        # In production, derive build_id from .build-timestamp file, then
        # SCITEX_HUB_BUILD_ID env var, falling back to timestamp.
        build_id = ""
        try:
            ts_file = Path(settings.STATIC_ROOT) / "vite" / ".build-timestamp"
            if ts_file.exists():
                build_id = ts_file.read_text().strip()[:10]
        except Exception:
            pass
        if not build_id:
            build_id = os.environ.get("SCITEX_HUB_BUILD_ID", "")
        if not build_id:
            import time

            build_id = str(int(time.time()))

    return {"build_id": build_id}


def debug_mode(request):
    """
    Always expose DEBUG setting to templates.
    Unlike django.template.context_processors.debug, this doesn't check INTERNAL_IPS.
    """
    return {"DEBUG": settings.DEBUG}


def scitex_version(request):
    """
    Expose SciTeX Hub version to all templates.
    Single source of truth: settings.SCITEX_HUB_VERSION
    """
    return {"SCITEX_HUB_VERSION": get_scitex_hub_version()}


def get_scitex_hub_version():
    """
    Get version from Django settings (single source of truth).
    settings.SCITEX_HUB_VERSION is the scitex-hub web app version,
    separate from pyproject.toml which is for the pypi package.
    """
    return getattr(settings, "SCITEX_HUB_VERSION", "0.0.0")


def umami_analytics(request):
    """
    Expose Umami Analytics configuration to templates.
    Umami is privacy-focused and does not use cookies.
    Respects user's analytics_opt_out preference.
    """
    # Check if user has opted out of analytics
    opted_out = False
    if hasattr(request, "user") and request.user.is_authenticated:
        try:
            opted_out = request.user.profile.analytics_opt_out
        except Exception:
            pass

    return {
        "UMAMI_WEBSITE_ID": (
            "" if opted_out else getattr(settings, "UMAMI_WEBSITE_ID", "")
        ),
        "UMAMI_SCRIPT_URL": getattr(
            settings, "UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js"
        ),
        "UMAMI_DOMAINS": os.environ.get("SCITEX_HUB_UMAMI_DOMAINS", ""),
    }


def site_branding(request):
    """
    Expose site branding constants to all templates.
    Single source of truth: config/branding.py
    """
    from config import branding

    return {
        "SITE_NAME": branding.SITE_NAME,
        "SITE_TAGLINE": branding.SITE_TAGLINE,
        "SITE_TAGLINE_SECONDARY": branding.SITE_TAGLINE_SECONDARY,
        "SITE_DESCRIPTION": branding.SITE_DESCRIPTION,
        "META_DESCRIPTION_DEFAULT": branding.META_DESCRIPTION_DEFAULT,
        "OG_TITLE": branding.OG_TITLE,
        "OG_DESCRIPTION": branding.OG_DESCRIPTION,
        # Public contact addresses. Templates must use these rather than
        # hardcoding an address, so changing one is a single edit and cannot go
        # half-applied across pages. NOTE templates/500.html cannot use them —
        # Django's default handler500 renders without context processors, so a
        # {{ }} there would emit an empty mailto:. See config/branding.py.
        "CONTACT_EMAIL": branding.CONTACT_EMAIL,
        "LEGAL_EMAIL": branding.LEGAL_EMAIL,
        "PRIVACY_EMAIL": branding.PRIVACY_EMAIL,
        "RECRUIT_EMAIL": branding.RECRUIT_EMAIL,
        # branding.NOREPLY_EMAIL is deliberately NOT exported: it is a mail
        # SENDER, never something a page invites a reader to write to. Its one
        # use site (apps/infra/public_app/tasks/health.py) is Python and imports
        # the constant directly.
        #
        # The registered company address and name, READ-ONLY here. These are the
        # only two values in this function that come from Django settings rather
        # than config/branding.py, and that asymmetry is deliberate:
        # settings_commerce.py OWNS them because they are 特定商取引法
        # legal-disclosure facts, env-driven and changeable only when the
        # operator says so. This export WIDENS READ ACCESS so any template can
        # show the real address; it does not relocate ownership. Do NOT move the
        # definitions into config/branding.py, and do NOT point them at
        # branding.CONTACT_EMAIL's neighbours -- config/branding.py carries the
        # matching warning about exactly that class of refactor.
        #
        # WHY THIS EXISTS: /cookies/ published a FABRICATED US address
        # ("123 Science Park, San Francisco, CA 94107") while the app already
        # held the real one and rendered it correctly on /services/tokushoho/.
        # The page contradicted a value the app owned. The tokushoho VIEW passes
        # its own lowercase ``company_address`` for that page only, so a template
        # outside that view had no way to read it -- writing
        # ``{{ company_address }}`` into any other template renders EMPTY.
        # Exported in SCREAMING_SNAKE to match this function's other keys and to
        # stay textually distinct from the tokushoho view's lowercase context, so
        # the two never silently shadow one another.
        #
        # The getattr default is NOT an unconsidered silent fallback. settings
        # ALWAYS defines these (settings_commerce.py is star-imported by
        # settings_shared, which every environment inherits), so the default is
        # unreachable in practice. It is kept because this processor runs on EVERY
        # template: raising here would 500 the entire site over one line of one
        # legal page. The loudness lives in the test instead --
        # tests/apps/public_app/views/test_legal_addresses.py asserts the setting
        # is non-trivial AND that the real string reaches the rendered /cookies/
        # body, so an empty value fails CI and can never ship quietly. Same
        # "SSoT by ASSERTION where raising is the wrong tool" pattern as
        # tests/config/test_contact_email_ssot.py.
        "COMPANY_ADDRESS": getattr(settings, "COMPANY_ADDRESS", ""),
        # COMPANY_NAME is "株式会社 SciTeX" -- the entity that does not legally
        # exist until incorporation completes (2026-08-08). It is exported so the
        # switch on that date is a one-token template edit rather than a
        # context-processor change, but the general legal pages deliberately
        # render SITE_NAME ("SciTeX") until then: the operator ruled that naming a
        # company which does not yet exist replaces one false statement with
        # another. /services/tokushoho/ is the ONE page that names the statutory
        # entity, and it reads settings directly through its own view.
        "COMPANY_NAME": getattr(settings, "COMPANY_NAME", ""),
    }


def writer_api_base(request):
    """Resolve ``api_base`` for scitex_writer._django's editor/viewer templates.

    ``scitex_writer._django.views.editor_page`` / ``viewer_page`` render
    ``writer/{editor,viewer}.html`` via
    ``render_to_string(template, context, request=request)`` and never put
    ``api_base`` in their own context dict, so the template's
    ``{{ api_base|default:'/' }}`` always fell back to ``"/"``. That default
    is only correct for scitex-writer's OWN standalone deployment (mounted
    at the domain root by ``_standalone_urls.py``). Hub mounts the same
    views under ``/apps/writer/{editor,viewer}-v2/`` and
    ``/<username>/<slug>/live/`` (scitex-hub#146), so with no context
    processor supplying ``api_base``, every one of
    ``writer_app/frontend/src/api.ts``'s ``fetch(API_BASE + endpoint)``
    calls silently targeted the wrong absolute path (e.g. ``/api/claims``
    instead of ``/apps/writer/v2/api/claims``) and 404'd — the editor/viewer
    shell renders, but no claim, DAG, or manuscript data ever loads.

    Derived purely from ``request.path`` (no DB lookup): the writer v2
    routes are the only ones with a matching shape, so every other template
    keeps getting an empty context key here (falls through to the
    template's own ``default:'/'``, unused since no other page reads
    ``api_base``).
    """
    path = request.path
    if path.endswith("/editor-v2/") or path.endswith("/viewer-v2/"):
        return {"api_base": path.rsplit("/", 2)[0] + "/v2/"}
    if path.endswith("/live/"):
        # "v2/" (not "api/"): HANDLERS keys already carry their own "api/"
        # prefix (e.g. "api/claims") — see
        # apps/infra/project_app/urls.py's "<slug:slug>/live/v2/<endpoint>".
        return {"api_base": path + "v2/"}
    return {}


try:
    from scitex_ui.branding import launcher_context as _ui_launcher_context
except ImportError:
    # scitex-ui is floor-pinned (>=0.16.0) in pyproject.toml, so a plain
    # `pip install`/`uv pip install` picks up whatever the LATEST release on
    # PyPI is -- not necessarily the exact version this file was written
    # against. launcher_context() shipped in scitex-ui PR #162 (commit
    # ee689b33e122, merged to scitex-ui's develop 2026-08-20), but the newest
    # PyPI release at the time of THIS commit is 0.16.0 (published 2026-08-18,
    # two days earlier) and does not have it yet. A hard `from ... import`
    # would raise at Django startup and 500 every single page on any
    # deployment still resolving to 0.16.0 -- unacceptable for one back-link.
    # Falling back to building the same dict shape by hand keeps this inert
    # (no launcher key changes) until scitex-ui publishes a release the floor
    # pin picks up, at which point this starts calling the real validator
    # with no hub-side change required.
    _ui_launcher_context = None


def mounted_app_launcher(request):
    """Give standalone-mounted apps a way back to the Store (scitex-ui #162).

    scitex-ui's ``standalone_shell.html`` (used by every app hub mounts as an
    upstream leaf package rather than folding into the full workspace shell --
    Storage and Cards today, Writer's editor-v2/viewer-v2 as well) renders a
    launcher back-link ONLY when the context carries a ``launcher`` key. Below
    768px every workspace pane is ``display:none``, and neither app's own
    content supplies a way out, so scitex-hub measured /apps/storage/ at
    390x844 with ZERO anchor elements on the page -- nothing a visitor could
    tap to leave. This processor is the fix: it supplies ``launcher`` for
    exactly the request paths that render through that shell.

    A context processor, not each view's own context dict, because Storage's
    and Cards' views are upstream (``scitex_storage._django`` /
    ``scitex_cards._django``) -- hub cannot edit their context without
    forking them, and forking a leaf package to add one shared link is the
    kind of duplication that drifts. This processor reaches every render
    without touching upstream code at all (mirrors ``writer_api_base``
    above, which solves the same "upstream view, hub-only context" problem
    for a different key).

    Scoped by prefix/suffix on ``request.path``, deliberately narrow: any page
    NOT in this list keeps getting no ``launcher`` key, unchanged from before
    this processor existed. In particular this never touches hub's own
    full-workspace pages (they already carry the sidebar's own navigation, so
    a second back-link would be redundant) or Writer's public
    ``/<user>/<slug>/live/`` viewer (an anonymous reader of a published paper
    has no reason to be routed to the SciTeX app store).
    """
    path = request.path
    is_mounted_standalone_page = path.startswith(
        ("/apps/cards/", "/apps/storage/")
    ) or path.endswith(("/editor-v2/", "/viewer-v2/"))
    if not is_mounted_standalone_page:
        return {}

    launcher = {"url": "/apps/store/", "label": "Back to Store"}
    if _ui_launcher_context is not None:
        return _ui_launcher_context(launcher)
    return {"launcher": launcher}


def scitex_env(request):
    """
    Expose the deployment environment to templates.

    The environment is read from ``settings.SCITEX_ENV``, which each concrete
    settings module (settings_dev / settings_staging / settings_prod) declares
    literally. It is deliberately NOT re-derived from the SCITEX_HUB_ENV
    environment variable here: the settings module Django is actually running
    under IS the environment, and reading it twice from two sources is how the
    favicon and the deployment drift apart.

    ``SCITEX_FAVICON`` is the static-relative path of the environment's tab
    icon -- the same SciTeX brand mark in a per-environment colour, so prod /
    staging / dev are distinguishable from the tab icon alone.
    """
    env = branding.normalize_env(settings.SCITEX_ENV)
    return {
        "SCITEX_ENV": env,
        "IS_STAGING": env == branding.ENV_STAGING,
        "IS_PRODUCTION": env == branding.ENV_PRODUCTION,
        "SCITEX_FAVICON": branding.favicon_for_env(env),
        # "dev" / "staging" / "standalone", or None in hub production. Same
        # marker the tab title uses, so chrome and tab never disagree.
        "SCITEX_ENV_MARKER": branding.title_marker(env, settings.SCITEX_APP_MODE),
    }
