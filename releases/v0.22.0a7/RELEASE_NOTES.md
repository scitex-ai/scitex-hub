# v0.22.0a7 — Authentication and MCP REST compatibility

This alpha fixes inactive-account key validation and restores generic REST
execution of mounted MCP tools through FastMCP's public client interface.
The public catalog and documentation use the same protocol schemas.

## Access requirements

- HTTP host MCP requires an active platform superuser and a key with `mcp`
  or `*` scope. Authentication-store failures return unavailable status.
- Generic MCP REST execution requires an active platform superuser. API keys
  additionally need `api` or `*` scope. Tool names and legacy public flags do
  not grant anonymous execution.
- API keys belonging to inactive accounts are rejected centrally. Rejected
  keys do not record successful use.
- Public tool metadata remains readable. Project clients use the leaf apps'
  scoped Web APIs. Agent/container host operations remain excluded from the
  generic bridge.

There are no database schema migrations. Source acceptance, published package
verification, and development/production runtime acceptance are separate
release steps. This note does not claim that deployment has occurred.
