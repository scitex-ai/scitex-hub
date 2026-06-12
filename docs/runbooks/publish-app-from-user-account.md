# Publish a SciTeX App From a User Account

Audience: agent or operator driving the **agent-programmatic publish flow**
end-to-end (the operator-12834 / 12845 directive — demonstrate that hub
apps are user-creatable, customizable, published from a personal account,
all via the CLI client with no manual UI step).

The flow takes a thin-wrapper Django app, registers a corresponding
**project** under the user's namespace on `https://scitex.ai`, develop-installs
it locally, then **submits** it to the central registry. Submission opens
a cross-repo PR; merge equals approval (MELPA-style).

## Glossary

- **Workspace JWT** — the `Authorization: Bearer <jwt>` token the hub CLI
  uses for `/api/...` endpoints (`project create`, `app submit`). Default
  TTL: 60 minutes (`config/settings/settings_auth.py`,
  `SIMPLE_JWT.ACCESS_TOKEN_LIFETIME`).
- **Registry** — `scitex-apps/<slug>` on the central Gitea
  (`git.scitex.ai`). Cross-repo PRs `user/<slug>` → `scitex-apps/<slug>`
  land here; merging surfaces the app marketplace-wide.
- **Editable install** — when scitex-hub is `pip install -e .` from a
  worktree (common in dev), the running `scitex-hub` CLI imports from
  the worktree's `src/`. Patches to that worktree take effect on the
  next invocation, no re-install.

## 0. Prerequisites

1. `scitex-hub` CLI on `PATH`. Verify:
   ```bash
   scitex-hub --version
   ```
2. The thin-wrapper app source in a directory containing `manifest.json`.
   (See `app init` below.)
3. **Workspace JWT** delivered via cached token file (see §2).

## 1. Set the hub server target

The CLI honours `SCITEX_HUB_URL` for both `project create` (via the
Python API in `scitex_hub.project`) and `app submit` (via the
`--server` flag, which falls back to the same env var).

```bash
export SCITEX_HUB_URL=https://scitex.ai
```

That's the **bare Django host** — no trailing slash, no `/api/` prefix.
The CLI builds `{SCITEX_HUB_URL}/api/...` URLs internally. `git.scitex.ai`
is the Gitea host the Django backend reaches *server-side* via the
project-creation signal; the CLI never talks to Gitea directly.

## 2. Workspace JWT — token-only, no interactive login

The user account (`ywatanabe` for the demo) is a Google-OAuth account
created via allauth; there is no usable password. So the standard
`/api/token/` username/password exchange is not available. Use one of:

### 2a. Server-minted JWT (TODAY — zero code changes)

On the prod Django shell (someone with `docker compose exec` access on
the prod NAS):

```bash
docker compose \
  -f deployment/docker/docker-compose.yml \
  -f deployment/docker/docker-compose.prod.yml \
  exec -T django \
  python manage.py shell -c "$(cat <<'PY'
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
u = get_user_model().objects.get(username='ywatanabe')
t = RefreshToken.for_user(u).access_token
t.set_exp(lifetime=timedelta(hours=2))   # safety margin over the 60-min default
print(str(t))
PY
)"
```

The printed string is a SimpleJWT access token signed for that user.
Drop it into the hub's cached-token location:

```bash
mkdir -p ~/.scitex/cloud/runtime
cat > ~/.scitex/cloud/runtime/token.json <<'JSON'
{"server": "https://scitex.ai", "access": "<paste the JWT here>"}
JSON
```

`_workspace_auth.load_cached_token()` reads this file. The first
`scitex-hub` call that needs a JWT cache-hits this entry; no
`/api/token/` round-trip, no prompt.

### 2b. APIKey PAT (FOLLOW-UP — requires server-side PR)

The `scitex_xxxx` API-key UI exists at
`https://scitex.ai/api-keys/` but is not yet wired into the JWT
endpoints (`api_project_create_jwt`, `api_submit_jwt`). The durable
agent-programmatic-publish path adds an `APIKeyAuthentication` DRF
class so a UI-generated PAT auths against those endpoints. Once that
lands, the runbook §2 above becomes "Operator generates a PAT in the
UI → drops it into the same `token.json`". Tracked as the
`scitex-hub-apikey-on-jwt-endpoints` card.

## 3. Scaffold the thin-wrapper app

Use `scitex-hub app init` to generate the boilerplate, then customise
three files (apps.py, urls.py, manifest.json) to forward to the
upstream package.

```bash
scitex-hub app init /tmp/scitex_live_paper_app \
    --name scitex_live_paper_app \
    --label "SciTeX Live Paper" \
    --icon "fas fa-file-lines" \
    --description "Interactive live-paper viewer + claim provenance"
```

Then in the generated directory:

**`urls.py`** — replace the placeholder list with a shim that includes
the upstream package's URL conf:
```python
from django.urls import include, path
from . import views
app_name = "scitex_live_paper_app"
urlpatterns = [
    path("info/", views.index_view, name="info"),
    path("", include("scitex_live_paper._django.urls")),
]
```

**`apps.py`** — boot-permissive `ready()` so missing upstream warns
instead of crashing import:
```python
def ready(self) -> None:
    try:
        import scitex_live_paper._django  # noqa: F401
    except ImportError:
        _logger.warning(
            "scitex_live_paper_app: `scitex-live-paper` is not installed..."
        )
```

**`manifest.json`** — declare the python dependency so the hub knows
what to install for the user when they enable the app:
```json
"dependencies": { "python": ["scitex-live-paper>=0.1.0a0"], "system": [] }
```

## 4. Create the user project

```bash
scitex-hub project create scitex-live-paper-app
```

The naming convention:
- **Django module** (snake_case): `scitex_live_paper_app`
- **Gitea slug** (hyphenated, suffixed `-app`): `scitex-live-paper-app`

Once the operator-12845 client-tidy PR lands you can mark the project
as an app at creation time:

```bash
scitex-hub project create scitex-live-paper-app --category app
# or the equivalent shortcut:
scitex-hub app create scitex-live-paper
```

The `--app` shorthand and the `scitex-hub app create` group are wired
to call `project_create(category="app")` which sets `is_app=True`
server-side and auto-suffixes `_app` if missing.

At the API layer the call hits `POST /api/projects/create/` →
`api_project_create_jwt`, authenticated by the JWT from §2. The Django
signal handler then creates the corresponding Gitea repo at
`git.scitex.ai/<user>/<slug>` automatically.

## 5. Install the app source into the project

The local app source you scaffolded in §3 needs to be pushed to the
Gitea repo created in §4. With a Gitea remote configured, the
`install-dev` flow handles this:

```bash
scitex-hub app install-dev /tmp/scitex_live_paper_app
```

(This step still depends on having a Gitea push credential — for the
agent-runs-it demo, the operator's Gitea token gets injected into the
container env.)

## 6. Submit for review

```bash
scitex-hub app submit /tmp/scitex_live_paper_app
```

Hits `POST /api/apps/submit/` → `api_submit_jwt` with the JWT from §2.
This:
1. Looks up the user's project by name.
2. Pins the HEAD commit of the user's Gitea repo.
3. Creates an `AppsModule` record (or updates one) + a
   `ModuleSubmission`.
4. Opens a cross-repo PR `user/<slug>` → `scitex-apps/<slug>`.
5. Returns the PR URL.

Track review status by querying the registry:
```bash
gh -R scitex-apps/scitex-live-paper-app pr list
```

Merge of the PR equals approval — at that point the
`api_registry_webhook` handler sets `visibility=public,
is_verified=True` on the AppsModule, and the app becomes visible in
the marketplace browse view.

## Troubleshooting

- **401 on `app submit`** with a valid-looking JWT: the older
  `_publish.py` URL pointed at `/apps/store/api/<module_name>/submit/`
  which routes to a `@login_required` view (session-only). The fixed
  URL is `/api/apps/submit/`. If you're running an editable install,
  patch `src/scitex_hub/appmaker/_publish.py:51` and re-invoke; no
  re-install needed.
- **JWT expired mid-flow**: by default 60 min — re-mint via §2a. The
  `set_exp(lifetime=timedelta(hours=2))` variant gives a 2 h window.
- **Name conflict** (`HTTP 400` "already exists"): a previous attempt
  reserved the slug. Either delete with `scitex-hub project delete
  <slug> --yes` or pick a new name.
- **`scitex-hub` CLI says "API key required"** when calling MCP
  endpoints (not JWT endpoints): that's a separate `SCITEX_HUB_API_KEY`
  env var read by `_mcp_tools/api.py`; not relevant for the publish
  flow which only uses JWT.

## Related

- `docs/runbooks/local-staging-orochi-cloud.md` — local-staging
  variant of this flow (against a localhost Django + ngrok).
- Operator messages 12834, 12845, 12871 (publish-from-user-account
  directive + naming convention).
- Card `scitex-hub-apikey-on-jwt-endpoints` — durable server-side PR
  that replaces the §2a one-liner with a UI-generated PAT path.
