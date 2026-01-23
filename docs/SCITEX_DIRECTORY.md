# SciTeX Directory Structure

## Overview

SciTeX uses a per-user directory structure to isolate user data, cache, and configuration. This document describes how directory paths are resolved in both local CLI usage and Django cloud deployment.

## Directory Structure

```
.scitex/
└── scholar/
    ├── cache/
    │   ├── auth/           # Authentication tokens/cookies
    │   ├── chrome/         # Browser profile cache
    │   ├── engine/         # Search engine response cache
    │   ├── url/            # URL resolution cache
    │   └── pdf_downloader/ # Download state cache
    ├── config/             # User configuration overrides
    ├── library/
    │   ├── downloads/      # Staging area for new PDFs
    │   ├── MASTER/         # Canonical paper storage
    │   └── {project}/      # Project-specific symlinks
    ├── log/                # Operation logs
    ├── backup/             # Backup files
    └── workspace/          # Temporary workspace files
        ├── logs/
        └── screenshots/
```

## Path Resolution

### Local CLI Usage

For local/CLI usage, the path is resolved from environment or defaults:

```
Priority:
1. $SCITEX_DIR environment variable
2. ~/.scitex (default)
```

Example:
```bash
# Use default
scitex-scholar search "neural networks"
# → Uses ~/.scitex/scholar/

# Use custom directory
export SCITEX_DIR=/mnt/research/.scitex
scitex-scholar search "neural networks"
# → Uses /mnt/research/.scitex/scholar/
```

### Django Cloud Deployment

For Django multi-user environments, paths are resolved per-user:

```
Priority:
1. SCITEX_USER_DATA_ROOT env var (containerized setups)
2. USER_DATA_ROOT Django setting
3. {BASE_DIR}/data/users/{username}/.scitex (default)
```

**Directory Layout:**
```
scitex-cloud/
└── data/
    ├── users/
    │   ├── alice/.scitex/scholar/...
    │   ├── bob/.scitex/scholar/...
    │   └── {username}/.scitex/scholar/...
    └── visitor/
        ├── {session_key}/.scitex/scholar/...
        └── shared/.scitex/scholar/...
```

## Thread-Safety in Django

**Important:** Never use `os.environ["SCITEX_DIR"]` in multi-user Django. Environment variables are process-global and cause race conditions between concurrent requests.

### Correct Usage

```python
from apps.scholar_app.integrations.scitex_scholar import (
    get_user_scitex_dir,
    get_scholar_config,
)

# Get user-specific directory
user_dir = get_user_scitex_dir(request.user)
# → /path/to/scitex-cloud/data/users/alice/.scitex

# Get configured ScholarConfig (thread-safe)
config = get_scholar_config(request.user)

# Pass config to scitex.scholar components
from scitex.scholar.pipelines import ScholarPipelineMetadataParallel
pipeline = ScholarPipelineMetadataParallel(config=config)
```

### Incorrect Usage (Race Condition!)

```python
# DON'T DO THIS in Django
import os
os.environ["SCITEX_DIR"] = f"/data/users/{user.username}/.scitex"
config = ScholarConfig()  # Race condition with other requests!
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SCITEX_DIR` | Base scitex directory (CLI only) | `~/.scitex` |
| `SCITEX_USER_DATA_ROOT` | Per-user root (containerized Django) | None |
| `SCITEX_SCHOLAR_*` | Scholar-specific overrides | See default.yaml |

### Django Settings

```python
# settings.py
USER_DATA_ROOT = '/app/data/users'  # Optional override
```

## API Reference

### `get_user_scitex_dir(user, session_key=None) -> Path`

Returns the user-specific `.scitex` directory path.

**Args:**
- `user`: Django User instance or None
- `session_key`: Optional session key for anonymous users

**Returns:** Path to user's `.scitex` directory

### `get_scholar_config(user=None) -> ScholarConfig`

Returns a ScholarConfig with user-specific paths.

**Args:**
- `user`: Django User instance or None

**Returns:** Configured ScholarConfig instance

### `ScholarConfig(scholar_dir=None, config_path=None)`

Initialize scholar configuration.

**Args:**
- `scholar_dir`: Explicit path (bypasses env var, thread-safe)
- `config_path`: Custom YAML config file path

## See Also

- `scitex.scholar.config.ScholarConfig` - Configuration management
- `scitex.scholar.config.core._PathManager` - Path structure definitions
- `apps/scholar_app/integrations/scitex_scholar.py` - Django integration
