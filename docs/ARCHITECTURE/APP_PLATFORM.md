# SciTeX App Platform -- Platform-Side Architecture

scitex-hub is the host platform that discovers, validates, and mounts third-party apps without importing any app-specific code.

## Core Principle: App Ignorance

scitex-hub must never `import figrecipe`, `import my_cool_app`, or reference any app by name in its core logic. All app interaction flows through generic interfaces:

- **Manifest-driven registration** -- apps declare themselves via `manifest.json`
- **Entry-point discovery** -- pip-installed apps register via `scitex_modules` entry points
- **Generic URL mounting** -- all apps mount under `/apps/<app_name>/`

## App Discovery

Apps are discovered through three mechanisms, in priority order:

1. **Built-in manifests** -- `apps/workspace/<app>_app/manifest.json` loaded at startup by `workspace_app/registry.py`
2. **Pip entry points** -- `discover_external_modules()` scans `importlib.metadata.entry_points(group="scitex_modules")` and calls `register_module()` for each
3. **Dev app loader** -- `apps_app/services/dev_app_loader.py` synthesizes `ModuleConfig` from user project directories at `data/users/<owner>/proj/<repo>/`

All paths converge on the **ModuleConfig** dataclass and the `register_module()` function in `apps/infra/workspace_app/registry.py`.

## ModuleConfig -- The Registration Contract

Every app, whether built-in or external, is represented by a `ModuleConfig`:

```python
@dataclass
class ModuleConfig:
    name: str           # URL slug: "figrecipe"
    label: str          # Display: "FigRecipe"
    app_name: str       # Django app: "figrecipe_app"
    icon_fa: str        # "fas fa-palette"
    partial_template: str
    context_builder: str  # dotted path to callable
    privileges: list    # [{"type": "filesystem", "scope": "project"}]
    order: int          # tab bar sort position
    ...
```

## URL Mounting Pattern

Apps mount at `/apps/<name>/` by default. The platform's `config/urls.py` includes each registered app's URL patterns. For apps with a Django-side package (like figrecipe), scitex-hub provides a thin wrapper that injects platform context:

```
/apps/figrecipe/figrecipe/<endpoint>
      ^^^^^^^^^                        -- platform prefix
               ^^^^^^^^^^^^^^^^^       -- delegated to figrecipe._django.views.api_dispatch
```

## Context Injection

The `_inject_project_context(request)` function in each app's URL wrapper:

1. Resolves the user's current project via `get_current_project(request)`
2. Injects `working_dir` into `request.GET` so the app can locate files
3. Passes through to the app's own `api_dispatch` unchanged

This is the **only** place scitex-hub touches app internals -- and it does so generically.

## Runtime Context Provided to Apps

scitex-hub provides these values to any mounted app:

| Context         | Source                          | Access                        |
|-----------------|---------------------------------|-------------------------------|
| `working_dir`   | User's current project path     | `request.GET["working_dir"]`  |
| `user`          | Authenticated Django user       | `request.user`                |
| `dark_mode`     | Body class `dark-theme`         | DOM: `body.classList`         |
| `is_embedded`   | Template data attribute         | DOM: `data-embedded="true"`   |
| `csrf_token`    | Django middleware                | Cookie / hidden field         |

## Manifest Schema (v2.0.0)

The `manifest.json` file is the single source of truth for app metadata:

```json
{
  "$schema": "scitex-app-manifest",
  "$schema_version": "2.0.0",
  "name": "figrecipe",
  "label": "FigRecipe",
  "icon": "fas fa-palette",
  "version": "0.14.0",
  "privileges": [
    {"type": "filesystem", "scope": "project", "reason": "Read/write figure recipes"}
  ],
  "dependencies": {"python": ["matplotlib", "figrecipe"]},
  "builtin": true
}
```

## App Validation

Before an app is approved for the platform, `app_validator.py` runs:

1. **Structure check** -- required files: `apps.py`, `views.py`, `urls.py`, `LICENSE`, `README.md`, `templates/<app>/index_partial.html`
2. **Security scan** -- forbidden patterns: `subprocess`, `os.system`, `eval()`, `exec()`, `__import__`
3. **Manifest validation** -- schema version, required fields, privilege declarations

Validation runs against the local filesystem first; falls back to Gitea API for remote-only repos.

## What scitex-hub Does NOT Do

- Does not import app Python packages in core code
- Does not hardcode app names in URL routing
- Does not manage app-specific database models
- Does not bundle app CSS/JS -- apps provide their own assets

## Key Files

| File | Purpose |
|------|---------|
| `apps/infra/workspace_app/registry.py` | ModuleConfig + register/discover |
| `apps/workspace/apps_app/services/app_loader.py` | Approved app loading |
| `apps/workspace/apps_app/services/dev_app_loader.py` | Dev app loading |
| `apps/infra/platform_app/manifest/loader.py` | YAML manifest parser + validator |
| `apps/infra/project_app/services/app_validator.py` | Structure + security validation |

## Cross-References

- **scitex-ui** (`docs/APP_SANDBOX.md`) -- Frontend CSS isolation, `<AppSandbox>` component, theme injection
- **scitex-app** (`docs/APP_SDK.md`) -- `FilesBackend` protocol, path resolution, app SDK
- **figrecipe** (`docs/SCITEX_APP_INTEGRATION.md`) -- Reference implementation of the app contract
