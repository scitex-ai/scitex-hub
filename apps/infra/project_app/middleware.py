"""
Middleware for SciTeX Hub.

All middlewares in this module are hybrid sync+async. Under daphne/ASGI
the chain is kept async end-to-end so that Django does not need to
insert an async_to_sync bridge around the view — which was the bridge
pair that serialized concurrent requests and caused the 504 pattern
in issue #147 (see #152 day-0 analysis).

Pattern: `sync_capable = True`, `async_capable = True`, the sync body
is kept intact as a private method and the async path simply runs that
body via `sync_to_async(..., thread_sensitive=True)` before awaiting
the next layer. This keeps behaviour identical and isolates DB / session
work in the existing sync code.
"""

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from django.contrib.auth import login

logger = logging.getLogger(__name__)


class VisitorAutoLoginMiddleware:
    """
    Middleware that auto-logs in visitor users as visitors.

    Works on any page - landing, /code/, /writer/, /scholar/, /vis/, etc.
    Skips non-browser requests (bots, health checks, automated scripts).

    Uses User-Agent based browser detection (standard pattern):
    - Allocates visitor slot for real browsers (Chrome, Firefox, Safari, etc.)
    - Skips automated requests (curl, wget, empty UA, crawlers)
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self._acall(request)
        self._sync_body(request)
        return self.get_response(request)

    async def _acall(self, request):
        await sync_to_async(self._sync_body, thread_sensitive=True)(request)
        return await self.get_response(request)

    def _sync_body(self, request):
        # Skip if already authenticated
        if request.user.is_authenticated:
            return

        # Skip static files, media, and paths that don't need visitor
        path = request.path
        skip_paths = (
            # System paths
            "/static/",
            "/media/",
            "/favicon.ico",
            "/robots.txt",
            "/sitemap.xml",
            "/healthz/",
            "/admin/",
            "/__debug__/",
            # API endpoints
            "/api/",
            # Visitor management pages
            "/visitor-pool-full/",
            "/visitor-expired/",
            "/visitor-restart/",
            # Public marketing/info pages (no login required)
            "/about/",
            "/pricing/",
            "/contact/",
            "/donate/",
            "/publications/",
            "/contributors/",
            "/releases/",
            "/demos/",
            # Legal pages
            "/privacy/",
            "/terms/",
            "/cookies/",
            # Documentation
            "/docs/web-api/",
            "/api-docs/",
            "/keyboard-shortcuts/",
            # Tools (client-side, no login needed)
            "/apps/tools/",
            # Auth pages
            "/auth/",
        )

        if any(path.startswith(p) for p in skip_paths):
            return

        # Skip non-browser requests (bots, health checks, automated scripts)
        # Use User-Agent based detection (standard pattern)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Check if it's a real browser
        is_browser = any(
            browser in user_agent
            for browser in ["Mozilla", "Chrome", "Safari", "Firefox", "Edge", "Opera"]
        )

        # Skip if not a browser (includes curl, wget, empty UA, bots, crawlers)
        if not is_browser:
            return

        # Note: Cookie consent check removed - SciTeX uses privacy-focused Umami
        # analytics and only essential session cookies (no tracking/advertising)

        # Auto-login as visitor for real browser requests
        try:
            from django.contrib.auth.models import User
            from django.db import connection

            from apps.infra.project_app.services.visitor_pool import VisitorPool

            visitor_project, visitor_user = VisitorPool.allocate_visitor(
                request.session
            )
            if visitor_user:
                login(
                    request,
                    visitor_user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                logger.info(
                    f"[Middleware] Auto-logged in visitor: {visitor_user.username} for {path}"
                )
            else:
                # Pool full — fall back to shared readonly-visitor
                try:
                    readonly_user = User.objects.get(
                        username=VisitorPool.READONLY_VISITOR_USERNAME
                    )
                    login(
                        request,
                        readonly_user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )
                    request.session["is_readonly_visitor"] = True
                    logger.info(
                        f"[Middleware] Pool full, logged in as readonly-visitor for {path}"
                    )
                except User.DoesNotExist:
                    logger.error(
                        "[Middleware] readonly-visitor user not found — run create_visitor_pool"
                    )
        except Exception as e:
            import traceback

            logger.error(
                f"[Middleware] Visitor auto-login failed: {e}\n{traceback.format_exc()}"
            )

        # Always ensure a clean DB connection before the view runs.
        # The visitor allocation uses @transaction.atomic with
        # select_for_update, and PgBouncer (transaction pool mode) may
        # return a dirty connection on startup.  Closing here guarantees
        # the view's ATOMIC_REQUESTS transaction starts on a fresh
        # connection, preventing cascading "current transaction is
        # aborted" errors during template rendering.
        try:
            from django.db import connection

            connection.close()
        except Exception:
            pass


class VisitorExpirationMiddleware:
    """
    Auto-reallocate expired visitors to a new session seamlessly.

    When a visitor's 60-minute session expires, this middleware automatically:
    1. Logs out the expired visitor
    2. Clears session data
    3. Lets VisitorAutoLoginMiddleware allocate a new slot

    This provides a seamless experience - users don't see the expiration page
    unless all slots are full. Falls back to expiration page only if pool exhausted.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self._acall(request)
        short_circuit = self._sync_body(request)
        if short_circuit is not None:
            return short_circuit
        return self.get_response(request)

    async def _acall(self, request):
        short_circuit = await sync_to_async(self._sync_body, thread_sensitive=True)(
            request
        )
        if short_circuit is not None:
            return short_circuit
        return await self.get_response(request)

    def _sync_body(self, request):
        # Only check for authenticated visitor users
        if not request.user.is_authenticated:
            return None

        # Skip if not a visitor user (readonly-visitor also skipped here)
        if not request.user.username.startswith("visitor-"):
            return None

        # Skip certain paths to avoid redirect loops and allow access to essential pages
        path = request.path
        skip_paths = (
            "/visitor-expired/",  # The expiration page itself
            "/visitor-restart/",  # Restart session flow
            "/visitor-pool-full/",  # Pool exhausted page
            "/static/",
            "/media/",
            "/favicon.ico",
            "/logout/",
            "/signup/",
            "/login/",
            "/auth/",  # All auth pages
            "/api/",
            "/__debug__/",
        )

        if any(path.startswith(p) for p in skip_paths):
            return None

        # Check if visitor's allocation is expired
        try:
            from django.contrib.auth import logout
            from django.shortcuts import redirect
            from django.utils import timezone

            from apps.infra.project_app.models import VisitorAllocation
            from apps.infra.project_app.services.visitor_pool import VisitorPool

            allocation_token = request.session.get(
                VisitorPool.SESSION_KEY_ALLOCATION_TOKEN
            )
            is_expired = False

            if allocation_token:
                try:
                    allocation = VisitorAllocation.objects.get(
                        allocation_token=allocation_token, is_active=True
                    )
                    # Check if allocation is expired
                    is_expired = allocation.expires_at <= timezone.now()
                except VisitorAllocation.DoesNotExist:
                    # No active allocation found - visitor is expired
                    is_expired = True

            if is_expired:
                logger.info(
                    f"[Middleware] Visitor {request.user.username} expired, auto-reallocating..."
                )

                # Clear visitor allocation from session
                request.session.pop(VisitorPool.SESSION_KEY_PROJECT_ID, None)
                request.session.pop(VisitorPool.SESSION_KEY_VISITOR_ID, None)
                request.session.pop(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN, None)

                # Log out the current visitor user
                logout(request)

                # Try to allocate a new visitor slot immediately
                visitor_project, visitor_user = VisitorPool.allocate_visitor(
                    request.session
                )

                if visitor_user:
                    # Successfully allocated new slot - log in and continue
                    login(
                        request,
                        visitor_user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )
                    logger.info(
                        f"[Middleware] Auto-reallocated to {visitor_user.username} for {path}"
                    )
                    # Continue with the request - user doesn't see any interruption
                    return None
                else:
                    # Pool exhausted - redirect to expiration page as fallback
                    logger.warning(
                        "[Middleware] Pool exhausted during auto-reallocation, showing expiration page"
                    )
                    request.session["visitor_next_url"] = request.get_full_path()
                    return redirect("public_app:visitor_expired")

        except Exception as e:
            logger.error(f"[Middleware] Error in auto-reallocation: {e}")

        # Ensure clean DB connection before the view (same rationale as
        # VisitorAutoLoginMiddleware — PgBouncer transaction pool mode +
        # ATOMIC_REQUESTS can cascade dirty connections to the view).
        try:
            from django.db import connection

            connection.close()
        except Exception:
            pass

        return None


class VisitorAppRedirectMiddleware:
    """
    Placeholder — visitors (pool and readonly) CAN access /apps/ for browsing.

    Read-only enforcement is handled at the UI/API level (disabled editing,
    Read-Only badge), not by blocking URL access. Both pool visitors and
    readonly-visitor should be able to browse the workspace.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        # Pass-through: in async mode Django sees markcoroutinefunction and
        # awaits the coroutine returned here; in sync mode this is the response.
        return self.get_response(request)


class OnSiteAuthMiddleware:
    """
    Authenticate MCP tool requests from on-site agents (same container).

    When the MCP server runs alongside Django (on-site), it sends
    X-SciTeX-OnSite: <username> instead of Bearer token auth.
    Only accepts requests from trusted Docker/localhost origins.
    """

    TRUSTED_PREFIXES = ("127.", "10.", "172.", "192.168.", "::1")

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self._acall(request)
        self._sync_body(request)
        return self.get_response(request)

    async def _acall(self, request):
        await sync_to_async(self._sync_body, thread_sensitive=True)(request)
        return await self.get_response(request)

    def _sync_body(self, request):
        if request.user.is_authenticated:
            return

        username = request.META.get("HTTP_X_SCITEX_ONSITE")
        if not username:
            return

        # Only trust internal network sources
        remote_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        if not remote_ip:
            remote_ip = request.META.get("REMOTE_ADDR", "")
        if not any(remote_ip.startswith(p) for p in self.TRUSTED_PREFIXES):
            logger.warning("OnSite auth rejected from untrusted IP: %s", remote_ip)
            return

        from django.contrib.auth.models import User

        try:
            user = User.objects.get(username=username)
            request.user = user
            request._on_site_auth = True
            # Exempt from CSRF — MCP tools don't have CSRF tokens
            request._dont_enforce_csrf_checks = True
        except User.DoesNotExist:
            logger.warning("OnSite auth: user %s not found", username)


class GuestSessionMiddleware:
    """
    Track user state including current/last accessed project.

    For logged-in users:
    - Tracks current project in session
    - Used for smart module navigation

    For visitor users (no longer used):
    - Previously generated guest session IDs
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self._acall(request)
        self._sync_body(request)
        return self.get_response(request)

    async def _acall(self, request):
        await sync_to_async(self._sync_body, thread_sensitive=True)(request)
        return await self.get_response(request)

    def _sync_body(self, request):
        # Track current project from URL for logged-in users
        if request.user.is_authenticated:
            # Check if URL matches /<username>/<project>/...
            import re

            pattern = r"^/([^/]+)/([^/?]+)/"
            match = re.match(pattern, request.path)

            if match:
                username = match.group(1)
                project_slug = match.group(2)

                # If this is a project page (not 'projects' or other reserved words)
                if (
                    project_slug not in ["projects"]
                    and username == request.user.username
                ):
                    # Update session with current project
                    request.session["current_project_slug"] = project_slug
                    request.session.modified = True
