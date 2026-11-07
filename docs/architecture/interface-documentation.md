# Provider-backed interface documentation

`/apps/docs/#overview` and `/docs/web-api/` explain the same five interfaces:
Python, CLI, MCP, Web API and installed skills. Domain behavior belongs to each
leaf package. Dev discovers documentation and skills and dispatches audit/hook
providers; SDK defines shared Web contracts; Hub supplies browser navigation and
explicit host admission.

Hub projects `scitex_dev.list_doc_providers()` and the SDK's installed
`scitex.apis` declarations. Catalog rendering does not load entry points, import
leaf handlers, start servers, query user data or probe live APIs. Duplicate
provider names remain ambiguous rather than selecting an arbitrary owner. An
older Dev without the discovery API produces an explicit unavailable state.

`GET /docs/web-api/catalog.json` is the same inert projection for agents.
`?package=scitex-scholar` filters by normalized distribution identity, not a
filesystem path. POST/PUT/DELETE are refused. An entry point without a valid
installed inert descriptor does not advertise verified routes. A valid descriptor
still does not prove host admission or a responding endpoint. Historical section
URLs remain clearly unverified references and do not display the old executable
examples or credential-bearing setup snippets.

Use `scitex-dev dev skills list --package PACKAGE --json` for installed skills.
Hub does not guess that a package-specific MCP installer exists. Follow a leaf's
registered documentation or skill for its explicit setup contract.

For GUI pages, the existing module registry supplies `pip_package`. Hub writes
`data-stx-api-docs-url` onto the owned page body. The SDK AppHeader (TypeScript or
React) renders that URL through its existing action slot. The SDK knows no Hub
route or package catalog. A page without a registered owner receives no invented
identity. Embedded pages receive the metadata without an extra host header. Both generic
workspace switchers consume registry-derived `X-SciTeX-API-Docs-URL` fragment
metadata before mounting a replacement pane. They keep an explicit empty pane
attribute for an unknown owner, suppressing stale body inheritance, and use
`stxAppHeader.mount(pane)` rather than relying on cached modules to run again.

## Generic MCP REST compatibility bridge

The separate `/api/v1/tools/` bridge discovers MCP protocol metadata. MCP
registration does not grant a project-scoped Web API admission. Generic
tools require an authenticated, active platform superuser; an API key must also
carry `api` or `*` scope. Ordinary users, staff users without superuser status,
and inactive operators cannot execute them. Tool execution is never made public by a
`docs_`, `introspect_`, or other name prefix. Listings remain publicly readable,
advertise `access: operator` and `is_public: false`, and state the requirements
in `tool_execution_access`. Public documentation/catalog routes remain available.

Project clients use the leaf Web APIs described by the SDK contracts and
authorized by the host's project capabilities. A generic tool's filesystem
arguments and optional active-project default do not establish that boundary.
Agent/container operations and explicit code-execution tools are excluded from
the bridge, including current Hub and legacy Cloud mount aliases. Discovery and
the documentation catalog use the same protocol schemas; discovery never calls
the registered tool implementations.

The HTTP `/mcp` route hosts the complete umbrella server and has the same
operator boundary: its API key must belong to an active platform superuser and
carry `mcp` or `*` scope. Expired/revoked keys and inactive accounts receive 401;
valid keys without operator identity or the required scope receive 403. A failed
authentication database lookup returns 503, not a false invalid-key verdict.
Campaign tokens do not grant this host authority. Local MCP servers and scoped
leaf Web APIs retain their own access contracts.

All shared API-key consumers reject an inactive owner through
`accounts_app.auth.resolve_api_key`, consistently with the identity endpoint.
Refused credentials do not update successful-use timestamps.

## Development rollout and verification

Source qualification is distinct from deployment. Coordinate the reviewed Dev
catalog build, SDK header build and Hub source/artifact before updating Dev. The
new SDK bundle must be rebuilt through the normal UI build and Hub's coherent
Vite build; serve SDK assets through `app_static` content fingerprinting and
publish the new Vite manifest last. Do not replace published wheel RECORDs with
untracked source overlays or relabel an older frontend receipt.

Verify both URLs, the normalized Scholar link, explicit absent/ambiguous states,
JSON 200/400/405, actual browser title, desktop/phone and light/dark rendering.
Record installed provider metadata separately from source declarations and
observe each GUI's real canonical header; GUI registration alone proves neither
an API provider nor a live API. Preserve workers, agent sessions and unrelated
package payloads. This change does not authorize production deployment.


## Selected-package guidance

A normalized selected package also lists its installed, leaf-owned skills using
`scitex_dev.ecosystem.list_skills(package=...)`. Links open an exact
owner/namespace/name resource through `get_skill(..., owner=...)`; the browser does not expose
host paths or the reader's legacy fuzzy matching. Missing, ambiguous, foreign or
escaping resources are refused. Markdown is displayed as escaped documentation,
with an installed version and content fingerprint, rather than executable HTML.
This remains useful when a leaf has no canonical Web descriptor; it does not
certify that historical endpoints are enabled or responding. The old
`/apps/docs/api/` entry delegates to the same provider-backed page.

Owner-preserving reads require Dev's public `owned-skill-read-v1` capability.
Older installations show guidance discovery as unavailable and do not advertise
reader links. The selected distribution remains attached to the resource read,
including SDK namespaces also declared by archived distributions; there is no
fallback to global namespace selection.

Explicit host mounts that are absent from the launcher registry can still
supply a header API-documentation link. The host checks the already-resolved
view's callable globals, code filename and loaded module origin against an
installed distribution's recorded file, then requires an unambiguous registered
Docs provider whose module contains that view. Decorator traversal is bounded.
Missing, conflicting or unproven ownership leaves the link absent; this does
not register a launcher entry or admit a Web API endpoint. Registered module
identities take precedence, including an explicitly unknown owner.
