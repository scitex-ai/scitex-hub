"""Project request middleware."""

from __future__ import annotations

import re

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

# Backwards-compatible import path used by MIDDLEWARE.
from .middleware_onsite_auth import OnSiteAuthMiddleware  # noqa: F401


class AuthenticatedProjectSessionMiddleware:
    """Remember the active project for authenticated users only."""

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

    @staticmethod
    def _sync_body(request):
        if not request.user.is_authenticated:
            return

        match = re.match(r"^/([^/]+)/([^/?]+)/", request.path)
        if not match:
            return

        username, project_slug = match.groups()
        if project_slug != "projects" and username == request.user.username:
            request.session["current_project_slug"] = project_slug
            request.session.modified = True
