---
description: |
  [TOPIC] Vite Frontend Build
  [DETAILS] Build modes, SDK-owned exports, entry discovery and frontend validation.
tags: [scitex-hub-vite-frontend]
---

# Vite frontend build

Use the repository's `package.json`, `vite.config.ts`, `vite.entries.ts`,
`vite.sdk-exports.ts` and `vitest.config.ts` as the source of truth. Run the
following commands from the repository root after preparing its declared
frontend dependencies:

```bash
npm run dev
npm run build
npm run test:run
```

`dev` starts Vite's development server. HMR applies to clients connected to that
server. `build` produces the bundled assets and manifest; it does not start a
server. Its npm `prebuild` hook checks installed direct dependencies against
the declarations with `npm ls --depth=0`, before Vite can change output files.
This checks version satisfaction, not complete package integrity or security.
The tunnel preview uses prebuilt assets: the preview action in
`src/scitex_hub/_dev_preview/_actions.py` runs `npm run build` in the declared
Django container. A source edit alone does not establish that those public
assets have changed.

Production uses the verified frontend baked into its qualified image. Follow
[the baked frontend contract](../../../../docs/deployment/baked-frontends.md)
and [the deployment runbook](12_deployment-production.md) for publication.

## Shared components and provider resolution

New shared components belong to scitex-sdk. Vite and Vitest both call
`discoverScitexSdkRoot` and `scitexSdkSubpathAliasesFromRoot` from
`vite.sdk-exports.ts`. The SDK's own `package.json` wildcard exports define the
`@scitex/sdk/...` aliases; consumers do not maintain a second export list.

SDK discovery checks an explicit `SCITEX_SDK_ROOT`, then the declared `.apps/`,
sibling and worktree candidates, and finally the active Python environment's
installed SDK. CI sets `SCITEX_SDK_ROOT` to its admitted installed provider so
an unrelated sibling checkout cannot shadow it.

The current Vite configuration also retains legacy `@scitex/ui` resolution for
compatibility. That existing dependency does not make the archived scitex-ui
repository the destination for new shared components.

## Entry points and templates

`getEntryPoints()` in `vite.entries.ts` combines shared and app source discovery,
installed package entries and explicit overrides. Its source scanner excludes
internal dot/underscore names, declaration files and its declared skip directories.
Use an entry name from that resolver in the existing template tags, for example:

```django
{% load vite %}
{% vite_script 'docs_app/docs-workspace' %}
```

Keep application logic in TypeScript entry files. The configured browser-facing
hostname and WebSocket routes must follow the current request/environment;
a hardcoded LAN address is not a deployment-independent endpoint.

## Validation

Vite transpiles and bundles TypeScript. A successful Vite build is not a complete
semantic type check. The CI job named "TypeScript Compilation & Linting" in
`.github/workflows/tests.yml` currently runs `npm run build`; describe that actual
check rather than claiming it runs the TypeScript compiler. When a change needs
semantic checking, use the relevant existing app configuration or a scoped
`--noEmit` check with explicit compiler options. Do not invent a root tsconfig
or emit JavaScript into the source tree.

Use the existing Vitest and browser fixtures for affected behavior. Asset build,
unit behavior, browser behavior and deployed asset verification establish
different facts; record which checks actually ran.
