"""The Hub's caller for leaf APIs served at /api/v1/ (``SCITEX_API_CALLER``).

scitex-sdk serves every admitted ``scitex.apis`` plugin generically
(``scitex_sdk.app.api_serve``) and asks the HOST who is calling and what the
credential grants. This is that answer, and it knows nothing about any leaf:

* ``Authorization: Bearer scitex_…`` — the Hub's personal API key. Its scopes
  are the key's own (``<package>:<resource>:<read|write>``, wildcards
  ``*``, ``*:read``, ``<package>:*:read``…). A presented key that does not
  resolve is refused outright (the SDK answers 401 problem+json) — a bad
  bearer never falls back to anonymous or to the session.
* a logged-in browser session — every scope; the user's PROJECT rights still
  come from ``project_access`` and the SDK enforces CSRF on its writes.
* anything else — ``None`` (401).
"""

from __future__ import annotations

from scitex_sdk.app.api_exec import ApiCaller


def api_caller(request):
    from apps.infra.accounts_app.auth import resolve_api_key

    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        key, _reason = resolve_api_key(header[7:].strip())
        if key is None:
            return None
        request.user = key.user
        return ApiCaller(
            user=key.user,
            scopes=tuple(str(s) for s in (key.scopes or [])),
            via="token",
            token_id=key.key_prefix,
        )
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return ApiCaller(user=user, scopes=("*",), via="session")
    return None
