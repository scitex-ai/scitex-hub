---
description: |
  [TOPIC] User publish runbook — end-to-end App Store flow
  [DETAILS] Human-facing walkthrough for publishing an App to the scitex-hub
  app store. Covers one-time PAT setup, project scaffold, local iteration,
  cross-repo submit, and on-hub verification. Audience: a USER (not an agent).
tags: [scitex-hub-user-publish-runbook, scitex-hub-runbook]
audience: user
---

# User Publish Runbook — From Zero to a Listed App

> **Audience:** a human user who wants to publish an App to the
> scitex-hub App Store at https://scitex.ai.
>
> **Not in scope:** the agent-driven publish flow (handled by a separate
> skill). Anything that requires lead approval or NAS-side actions is
> called out as **STOP** and not executed by this runbook.

## 0. Pre-conditions

- An account on hub-prod — register at https://scitex.ai/accounts/signup/.
- `scitex-hub` CLI installed locally:

  ```bash
  pip install scitex-hub
  scitex-hub --version
  ```

- Git installed and configured (`git config --global user.email`).

## 1. One-time auth — get a PAT (Personal Access Token)

```bash
scitex-hub auth login
# Username: ywatanabe
# Password: ********
# -> PAT stored at ~/.scitex/cloud/credentials.json (mode 0600)
```

`scitex-hub auth login` exchanges your username+password for a long-lived
PAT, caches it locally, and uses it for every subsequent `app submit` /
`project create` call. You do **not** type the password again.

> **Ships shortly:** the `auth login` command lands with card #2
> (`scitex-hub auth` subcommand). If your local CLI does not yet have
> `auth`, run `scitex-hub --version` and upgrade with
> `pip install --upgrade scitex-hub`.

Verify:

```bash
scitex-hub auth whoami
# -> ywatanabe (PAT: pat_********, expires 2027-06-13)
```

## 2. Create the app project

Apps must end in `_app` (project convention — see ADR-0002). The CLI
appends the suffix automatically when you pass `--category app`:

```bash
scitex-hub project create my-app --category app
#  + Gitea repo  : ywatanabe/my-app_app
#  + Workspace   : ~/.scitex/cloud/projects/my-app_app/
#  + Django slug : my-app_app

cd ~/.scitex/cloud/projects/my-app_app
scitex-hub app init .
# Scaffolds the upstream-mirror _django shape:
#   apps.py  views.py  urls.py  tests.py  skill.py
#   manifest.json  templates/  static/  README.md  LICENSE
```

## 3. Build + iterate locally

Run the local-staging hub so you can hit your app in a browser:

```bash
make staging-up           # docker compose up for local staging
# webapp:  http://localhost:31294/apps/<you>/my-app_app/
```

Full pre-flight, port table, and back-out steps live in
[`docs/runbooks/local-staging-orochi-cloud.md`](../../../../docs/runbooks/local-staging-orochi-cloud.md).
Re-read it before the first run — staging requires `SECRETS/.env.staging`
and free ports `31294`/`2213`.

Iterate: edit `views.py` / templates / `manifest.json`, refresh the
browser. When green:

```bash
scitex-hub app validate .   # structure, manifest, security — exits 1 on error
```

## 4. Submit

```bash
scitex-hub app submit .
# - validates locally
# - reads PAT from ~/.scitex/cloud/credentials.json
# - pushes  ywatanabe/my-app_app  ->  scitex-apps/my-app_app  (cross-repo PR)
# - prints  PR URL  on success
```

The submit endpoint opens a **cross-repo PR** from your fork to
`scitex-apps/<app>`. Merge is approval (MELPA-style): a maintainer
reviews `manifest.json`, the diff, and the CI green, then merges.

## 5. Verify on the hub

Once the registry PR merges, your app is auto-listed:

- Listing page: `https://scitex.ai/apps/`
- Detail page:  `https://scitex.ai/apps/<author>/<name>/`
  (e.g. `https://scitex.ai/apps/ywatanabe/my-app_app/`)

The listing pulls from `manifest.json`, so the icon / label / description
you set in step 2 are what users see.

## 6. Troubleshooting

| Symptom (CLI output) | Cause | Fix |
|----------------------|-------|-----|
| `401 Unauthorized — PAT expired or revoked` | Cached PAT is stale | `scitex-hub auth login` again |
| `409 Conflict — project name already taken` | Slug `<name>_app` collides on Gitea | `scitex-hub project rename <slug> <new-name>` or pick a unique name |
| `404 Not Found — /api/v1/apps/submit/` | CLI talking to an old hub | Bump CLI: `pip install -U scitex-hub`; verify `scitex-hub config show` points at `https://scitex.ai` |
| `manifest.json: missing required field 'category'` | Scaffold edited by hand | Re-run `scitex-hub app validate .` and patch the field it names |

If `app submit` exits with anything other than `0`, **nothing was pushed
upstream** — fix locally and re-run; it's idempotent.

## 7. Reference

- [ADR-0002 — SciTeX Django App Standard](../../../../docs/adrs/0002-scitex-django-app-standard.md) — the `_app` suffix + manifest contract.
- PR #272 — `scitex-hub project create --category app` plumbing.
- PR #273 — `scitex-hub app submit` cross-repo PR opener.
- PR #274 — `/apps/<author>/<name>/` detail-page route on hub-prod.
- Related skills: [`08_project-management.md`](08_project-management.md),
  [`09_app-management.md`](09_app-management.md),
  [`11_deployment-staging.md`](11_deployment-staging.md).

# EOF
