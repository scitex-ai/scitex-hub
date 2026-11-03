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
identity. Embedded pages receive the metadata without an extra host header.

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
