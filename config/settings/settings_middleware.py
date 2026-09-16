# -*- coding: utf-8 -*-
# File: config/settings/settings_middleware.py
"""The MIDDLEWARE stack, shared across all environments.

Split out of settings_shared.py (which imports it back under the same name, so
settings_dev.py's ``MIDDLEWARE += [...]`` is unchanged). Order matters: see the
comments on each entry.
"""

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # i18n rails (F: tokushoho/commerce pages). Locale resolution must sit
    # after SessionMiddleware and before CommonMiddleware per Django docs.
    # English by default: pin anonymous visitors to English until they
    # explicitly choose a language (footer switcher sets the cookie). Runs
    # BEFORE LocaleMiddleware so it can strip the Accept-Language preference.
    "apps.infra.public_app.middlewares.EnglishDefaultLanguageMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Resolve Authorization: Bearer <jwt> → request.user for plain Django
    # views. Browser cookie-sessions short-circuit before this runs
    # (request.user already authenticated), so the middleware is a pure
    # addition that opens the JWT door to existing endpoints without
    # touching any view. See apps/infra/accounts_app/middleware.py.
    "apps.infra.accounts_app.middleware.JWTBearerToSessionMiddleware",
    "apps.infra.project_app.middleware.OnSiteAuthMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # VisitorAutoLoginMiddleware / VisitorExpirationMiddleware /
    # VisitorAppRedirectMiddleware were RETIRED 2026-09-10 (operator ruling:
    # "drop visitor entirely" — compass-impl-visitor-pool-retirement-20260910).
    # Anonymous browsers are no longer auto-provisioned into visitor-001..N;
    # they get a plain anonymous session and are funneled to signup (email
    # verify + card → 30-day free trial). The pool classes in
    # apps/infra/project_app/services/visitor_pool/ remain importable for
    # role-detection (VisitorPool / is_visitor_session / is_readonly_visitor)
    # that ~30 non-middleware call sites still use — they just stop being
    # fed by the middleware.
    # Default-deny site-wide write guard for the shared readonly-visitor
    # role (card hub-visitor-slot-isolation-audit — closes the exact gap
    # that produced the field-found "Plaque" leak: per-view opt-in guards
    # had missed project creation entirely). Kept as a safety net for any
    # readonly-visitor row that predates the retirement; no longer fed by
    # the middleware it used to run after. Per-view guards (file_save.py,
    # todo_app middleware below) still apply first for their richer error
    # copy; this is the backstop.
    "apps.infra.project_app.middleware_readonly_write_guard.ReadonlyVisitorWriteGuardMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.infra.project_app.middleware.GuestSessionMiddleware",
    # Desktop 90% content frame for leaf apps that render scitex-ui's own shell.
    "apps.infra.workspace_app.middleware_site_content_frame.SiteContentFrameMiddleware",
    # Scope the mounted scitex-todo board (/todo/) to the requesting
    # user's workspace store + enforce the phase-1 read-only gate. Must
    # run AFTER Authentication + VisitorAutoLogin so request.user is
    # final; no-ops in one prefix check for every other path (and when
    # the scitex_cards package is not installed).
    "apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware",
    # Site-wide dock on leaf-app pages that do not extend global_base.html
    # (hub pages render it themselves; the data-site-dock marker prevents a
    # second copy). Operator 2026-09-14: the dock on EVERY page.
    "apps.infra.workspace_app.middleware_site_dock.SiteDockMiddleware",
    # Injects the Alt+I element inspector into HTML responses when
    # SCITEX_UI_ELEMENT_INSPECTOR is on (see settings_shared.py).
    # Async-capable as of scitex-ui 0.6.1 — do not downgrade below that pin.
    "scitex_ui.middleware.ElementInspectorMiddleware",
]
