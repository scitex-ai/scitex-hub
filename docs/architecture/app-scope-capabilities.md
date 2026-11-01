# App scope capabilities

`config/settings/settings_scope.py` declares operational support for user
(All projects) and individual-project views separately. This is independent
of manifest/storage tenancy and never grants project access. Scholar keeps
its implemented user-wide library view; single-project engines expose All
as disabled. The current Journal archive supports user-wide browsing but
has no implemented project archive filter.

`AppAwareHubProjectProvider` wraps the existing authorized Hub provider.
The SDK optional disabled-scope hooks publish unavailable choices with
reasons and refuse selection on the server. Unsupported stored selections
are shown as unselected without rewriting the user's profile. Unknown app
contexts fail closed; the context-free legacy profile picker is unchanged.

The SDK provider URL hook carries the mounted app as `?app=` on the shared
scope API. A mounted `/apps/<app>/` path takes precedence over query context.
This context chooses capability policy only; resource authorization and
filesystem confinement remain the underlying providers' responsibility.

Regression evidence: `tests/apps/infra/project_app/test_scope_capabilities.py`
drives the real SDK HTTP dispatcher and a concrete filesystem provider for
all four permission combinations, rejected-write persistence, forged
context, unknown apps and stale selections. Runtime policy changes require
coordinated host deployment and browser qualification.
