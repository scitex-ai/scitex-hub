"""Explicit runtime scope support; independent of app storage/manifest scope.

These flags describe supported application operations, not project ACLs.
Project ownership/membership is still enforced by the host project provider.
Deployments may replace this mapping to restrict a capability further.
"""

SCITEX_APP_SCOPE_CAPABILITIES = {
    "scholar": {"user": True, "project": True},
    "cards": {"user": True, "project": True},
    "storage": {"user": True, "project": True},
    # These engines need one project/workspace; no aggregate engine exists.
    "writer": {"user": False, "project": True},
    "figrecipe": {"user": False, "project": True},
    "stats": {"user": False, "project": True},
    "live-paper": {"user": False, "project": True},
    # The current archive is global; a project-filtered archive is not shipped.
    "journal": {"user": True, "project": False},
    "agentic-journal": {"user": True, "project": False},
}
