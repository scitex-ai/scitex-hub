# App scope capabilities

Installed SDK AppConfigs expose the leaf-owned manifest `scope_capabilities`
object with literal `user` and `project` booleans. This declares operational
support independently of storage tenancy. Omission disables unsupported
choices visibly; deployments may restrict declared support further using
`SCITEX_APP_SCOPE_CAPABILITIES`, but cannot enable undeclared operations.

`AppAwareHubProjectProvider` wraps the existing authorized Hub provider.
Mounted identity comes from the SDK's manifest mount route, or the actual
Django resolved callback's owning AppConfig for host-mounted aliases.
Manifest package slugs are never guessed into mount aliases.

The SDK disabled-scope hooks expose reasons and reject selection on the
server. Unsupported stored selections appear unselected without rewriting
profiles. Context-free legacy profile selection is unchanged.

The SDK provider URL hook carries mounted app context as `?app=` on shared
GET/POST APIs. A mounted path takes precedence over query context. This
chooses capability policy only; project ACLs and filesystem confinement
remain provider-owned.

`tests/apps/infra/project_app/test_scope_capabilities.py` drives the real
SDK dispatcher and installed SDK AppConfig manifest with a filesystem-backed
provider for all four permission combinations, refused-write persistence,
forged context, unknown apps and stale selections.
