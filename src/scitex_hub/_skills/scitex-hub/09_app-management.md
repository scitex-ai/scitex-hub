---
description: |
  [TOPIC] App Management CLI
  [DETAILS] SciTeX app plugin management — scaffold new apps, validate, submit for review, manage preferences, check dependencies, build Apptainer containers. Apps must end in _app or -app..
tags: [scitex-hub-app-management]
---

# App Management CLI

All commands under `scitex-hub app`.

## Scaffold a New App

```bash
scitex-hub app init [target_dir] [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `target_dir` | `.` | Directory to scaffold in |
| `-n / --name` | (dir name) | App module name (must end with `_app`) |
| `-l / --label` | `""` | Human-readable label |
| `-i / --icon` | `fas fa-puzzle-piece` | Font Awesome icon class |
| `-d / --description` | `""` | Short description |
| `-f / --frontend` | `html` | `html` or `react` (React+Vite+Zustand) |
| `--overwrite` | (flag) | Overwrite existing files |

Creates: `apps.py`, `views.py`, `urls.py`, `tests.py`, `skill.py`, `manifest.json`, templates, static, agents config, README, LICENSE.

```bash
scitex-hub app init .
scitex-hub app init /path/to/my_app --name my_awesome_app
scitex-hub app init . -n demo_app -l "Demo" -i "fas fa-flask" -f react
```

## Validate

```bash
scitex-hub app validate [app_dir]    # check structure, security, manifest
```

Exits 1 if any issue found. Run before submitting.

## Development

```bash
scitex-hub app dev [app_dir] [--port PORT]    # show dev server instructions
```

## Submit for Review

```bash
scitex-hub app submit [app_dir] [--server URL]
```

Validates locally, authenticates via JWT, submits to server. Opens a PR on the central `scitex/apps` registry (MELPA-style: merge = approval).

## Browse Apps

```bash
scitex-hub app list [--server URL]    # list available apps
scitex-hub app info <app_name>        # detailed app info
scitex-hub app current                # show active app (SCITEX_CURRENT_APP)
scitex-hub app switch <app_name>      # switch active app
```

## Preferences

```bash
scitex-hub app prefs get <app_name>               # show saved prefs
scitex-hub app prefs set <app_name> key=val ...   # set prefs
scitex-hub app prefs delete <app_name>            # clear prefs
scitex-hub app prefs list                         # list all saved prefs
```

```bash
scitex-hub app prefs set writer theme=dark font_size=14
scitex-hub app prefs set scholar engine=crossref
```

## Dependencies

```bash
scitex-hub app check-deps [app_dir]                    # check deps from manifest.json
scitex-hub app install-deps [app_dir] -t python        # install python deps
scitex-hub app install-deps [app_dir] -t system        # install system deps
scitex-hub app install-deps [app_dir] -t node          # install node deps
scitex-hub app install-deps [app_dir] -t r             # install R deps
```

Reads `manifest.json` for dependency lists.

## Containers

```bash
scitex-hub app build-container [app_dir] [-o output_dir]
```

Reads `container` field from `manifest.json`, builds an Apptainer `.sif` image.

## MCP Tools

| Tool | What it does |
|------|-------------|
| `cloud_app_list_all` | List all apps |
| `cloud_app_get_info` | App details |
| `cloud_app_get_current` | Active app |
| `cloud_app_switch_to` | Switch active app |
| `cloud_app_get_prefs` | Get app preferences |
| `cloud_app_set_prefs` | Set app preferences |
| `cloud_app_check_deps` | Check dependencies |

# EOF
