"""App-aware adapter over the SDK's existing disabled-scope provider hooks."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from scitex_sdk.ui.project_scope import ProjectEntry


_APP_PATH = re.compile(r"^/apps/([a-z][a-z0-9-]*)(?:/|$)")


def request_scope_app(request):
    """The mounted app wins over caller query data; shared APIs carry context."""
    match = _APP_PATH.match(getattr(request, "path_info", ""))
    return match.group(1) if match else request.GET.get("app")


def scope_policy(request):
    app = request_scope_app(request)
    if app is None:
        # The context-free endpoint is the existing global profile selector.
        # It does not grant access to an app or authorize resource operations.
        return {"user": True, "project": True}
    policy = getattr(settings, "SCITEX_APP_SCOPE_CAPABILITIES", {}).get(app)
    if policy is None:
        return {"user": False, "project": False, "reason": "Scope support is not configured for this app."}
    if not isinstance(policy, dict) or any(type(policy.get(k)) is not bool for k in ("user", "project")):
        raise ImproperlyConfigured("App scope capabilities require explicit user/project booleans")
    return policy


class ScopeCapabilityProjectProvider:
    """Preserve provider authorization while publishing/enforcing app support.

    The context query chooses a UI/application capability policy, never a user
    identity, project ACL or filesystem root. Resource APIs retain their own
    authorization. Mounted app paths take precedence over a forged app query.
    """

    def __init__(self, provider):
        self.provider = provider

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def project_provider_url(self, request, base_url):
        app = request_scope_app(request)
        if app is None:
            return base_url
        parts = urlsplit(base_url)
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "app"]
        query.append(("app", app))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    def user_scope_disabled_reason(self, request):
        policy = scope_policy(request)
        return None if policy["user"] else policy.get("reason", "This app works with one project at a time.")

    def _project_reason(self, request):
        policy = scope_policy(request)
        return None if policy["project"] else policy.get("reason", "This app does not operate on individual projects.")

    def list_projects(self, request):
        reason = self._project_reason(request)
        return [ProjectEntry(
            id=entry.id, name=entry.name, detail=getattr(entry, "detail", ""),
            disabled=bool(reason) or getattr(entry, "disabled", False),
            disabled_reason=getattr(entry, "disabled_reason", "") or reason or "",
        ) for entry in self.provider.list_projects(request)]

    def last_visited(self, request):
        return None if self._project_reason(request) else self.provider.last_visited(request)

    def current_scope(self, request):
        selection = self.provider.current_scope(request)
        if selection is None:
            return None
        if selection.scope == "user" and self.user_scope_disabled_reason(request):
            return None
        if selection.scope == "project" and selection.id not in {
            p.id for p in self.list_projects(request) if not p.disabled
        }:
            return None
        return selection

    def remember(self, request, project_id):
        allowed = {p.id for p in self.list_projects(request) if not p.disabled}
        if project_id not in allowed:
            raise ValueError("project not accessible")
        self.provider.remember(request, project_id)

    def remember_scope(self, request, selection):
        if selection.scope == "user":
            if self.user_scope_disabled_reason(request):
                raise ValueError("user scope not available")
        elif selection.id not in {p.id for p in self.list_projects(request) if not p.disabled}:
            raise ValueError("project not accessible")
        self.provider.remember_scope(request, selection)
