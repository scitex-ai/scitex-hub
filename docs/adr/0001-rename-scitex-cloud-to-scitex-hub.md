<!-- ---
!-- Timestamp: 2026-05-23
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md
!-- --- -->

# ADR 0001 — Rename `scitex-cloud` to `scitex-hub`

- **Status**: Accepted
- **Date**: 2026-05-23
- **Deciders**: ywatanabe (lead), proj-scitex-hub (agent)
- **Affects**: PyPI package name, GitHub repo name, Python module name, display name, sub-app `hub_app`

## Context

The project has been named `scitex-cloud` since inception. The word
"cloud" strongly implies an internet-hosted, vendor-operated service. In
reality this project is the opposite: an AGPL-licensed, **self-hostable**
research platform designed to run anywhere — laptop, lab server, NAS, or
cloud. The `scitex-cloud` name therefore actively mis-sells the project's
core value proposition (Freedom 0: run your research anywhere, on your
own terms).

The "hub" framing is closer to reality:

- It is a **project hub** — repository hosting (Gitea), workspace shell,
  app store, AI co-pilot, all wired around a single project filesystem.
- It is the **GitHub-for-research** the README pitches in row 7 of the
  problem table.
- It composes well with the existing umbrella: `scitex[hub]` already
  maps to this package (see README §"Part of SciTeX").

## Decision

Rename `scitex-cloud` → `scitex-hub` end-to-end:

1. PyPI distribution name: `scitex-cloud` → `scitex-hub`
2. Python module name: `scitex_cloud` → `scitex_hub`
3. GitHub repository: `ywatanabe1989/scitex-cloud` → `ywatanabe1989/scitex-hub`
4. Display name in docs, README, badges, screenshots: "SciTeX Cloud" → "SciTeX Hub"
5. Sub-app: `apps/workspace/hub_app` → `apps/workspace/repo_app`
   (to avoid the "hub_app inside scitex_hub" naming nesting; `repo_app`
   also matches its actual responsibility — a Gitea-backed repo browser).

### Migration policy

Hard cutover, **no silent fallback** (per CLAUDE.md):

- The old PyPI distribution `scitex-cloud` gets one final release that,
  on import, raises an explicit `ImportError` pointing to `scitex-hub`
  and the migration guide URL. No re-export shim. No `DeprecationWarning`
  that lets callers proceed.
- The `scitex_cloud` Python module is removed entirely from the new code
  base; no compat alias.
- The local working tree at `/home/ywatanabe/proj/scitex-cloud` becomes
  `/home/ywatanabe/proj/scitex-hub`. The `~/proj/scitex-hub` symlink
  already in place keeps agent paths working during the transition.
- GitHub auto-redirects old repo URLs for a grace period; we rely on
  that rather than maintaining a mirror.

### Snapshot

The pre-rename HEAD `379018c4` is tagged `pre-rename-cloud-to-hub` so
the full rename is invertible — this also matches the reverse-rename
safety contract of `scitex-dev rename-symbols`.

## Consequences

**Positive**

- Name matches the product: a self-hostable, project-centric research hub.
- Resolves the `scitex_cloud.apps.workspace.hub_app` naming nesting that
  was already confusing in conversation and documentation.
- `pip install scitex[hub]` (umbrella, already wired) finally points to
  a package whose name matches the optional-extra it serves.

**Negative / cost**

- Breaks existing installs (`pip install scitex-cloud` no longer works
  silently). Mitigated by the explicit error + migration URL.
- Existing external links to `github.com/ywatanabe1989/scitex-cloud` rely
  on GitHub's redirect, which is eventual, not forever.
- Documentation, screenshots, and CHANGELOG entries up to v0.17.6 still
  carry the old name; we keep historical CHANGELOG text intact and add
  a new "Renamed" entry at the top.
- One churn-heavy commit series touching most files. Mitigated by using
  `scitex-dev rename-symbols` (cross-reference-aware, dry-run-first,
  reverse-rename-invertible).

## Alternatives considered

1. **Keep `scitex-cloud`, add a "hub" tagline.** Rejected — the package
   name is the most-cited identifier; a tagline can't outrun an
   `import scitex_cloud` line on every example.
2. **Soft-deprecate with `DeprecationWarning` + alias module.** Rejected
   by CLAUDE.md's "no silent fallback" rule, and by the fact that we
   are still in alpha (data formats already change between releases).
3. **Move only the display name, leave the package name alone.**
   Rejected — gives the worst of both worlds: branding says "Hub",
   `pip show` says `scitex-cloud`, agents and docs disagree.

## References

- README.md §"Part of SciTeX" (`scitex[hub]` umbrella mapping already
  exists)
- CLAUDE.md "No silent fallback"
- `scitex-dev rename-symbols` (the bulk renamer used for the migration)
- Tag `pre-rename-cloud-to-hub` at `379018c4`

<!-- EOF -->
