# Frontend Build Architecture: TypeScript, Vite, Django, Docker & Browser Cache

## Overview

This document describes the relationships between TypeScript, JavaScript, Vite, Django, Docker, tsconfig, vite.config, and browser cache handling in SciTeX Hub.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Browser Request                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Django Template Tags (apps/public_app/templatetags/vite.py)            │
│  ├── {% vite_hmr_client %}  → Injects Vite client (dev only)            │
│  ├── {% vite_script %}      → Smart loading with fallback chain         │
│  └── {% vite_legacy_script %}→ Build ID cache busting                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      ▼                           ▼
           ┌──────────────────┐        ┌──────────────────┐
           │  DEV: Vite HMR   │        │  PROD: Manifest  │
           │  Port 5173       │        │  Content Hashes  │
           │  (TypeScript)    │        │  (Built JS)      │
           └──────────────────┘        └──────────────────┘
```

## Component Relationships

### 1. TypeScript Configuration

**Files:**
- `tsconfig/tsconfig.base.json` - Base compiler options
- `tsconfig/tsconfig.json` - Root configuration for shared TS
- `apps/*/static/*/tsconfig.json` - Per-app configurations

**Key Settings (tsconfig.base.json):**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "allowJs": false,          // TypeScript-only enforcement
    "strict": false,           // Relaxed for build success
    "sourceMap": true
  }
}
```

**Path Aliases:**
- `@/*` → `static/shared/ts/*`
- `@/types/*` → `static/shared/ts/types/*`
- `@/utils/*` → `static/shared/ts/utils/*`

### 2. Vite Configuration

**File:** `vite.config.ts`

**Development Server:**
- Port: 5173
- Host: 0.0.0.0 (Docker accessible)
- HMR host: 127.0.0.1
- Polling enabled for Docker/WSL compatibility

**Build Output:**
- Directory: `staticfiles/vite/`
- Manifest: `staticfiles/vite/.vite/manifest.json`
- File naming: `[name]-[hash].js` (content-hash based)

**Entry Points (26+):**
| App | Entry |
|-----|-------|
| console_app | workspace |
| figrecipe_app | vis-editor, editor-inline |
| writer_app | index, collaboration-panel |
| project_app | clone_button, create_project_type, init-git-gutter, projects/settings |
| scholar_app | scholar-config, bibtex/status-tiles |
| public_app | visitor-status, server-status, landing-demos-inline |
| accounts_app | profile, account-settings, ssh_keys, remote_credentials |
| social_app | explore-inline |
| shared | theme-switcher, tooltip-auto-position, main, dropdown, django-messages, element-inspector, code-blocks, confirm-modal, header |

### 3. Django Integration

**Template Tags:** `apps/public_app/templatetags/vite.py`

**`{% vite_hmr_client %}`**
- Injects Vite client script in development (`DEBUG=True`)
- Returns empty string in production

**`{% vite_script 'entry_name' %}`**
- Simple two-mode operation (no fallback complexity):
  - `DEBUG=True` → Load from Vite dev server `http://127.0.0.1:5173/{ts_path}`
  - `DEBUG=False` → Load from manifest `staticfiles/vite/{hashed_file}`

**`{% vite_legacy_script 'path' %}`**
- For non-migrated scripts
- Uses `?v={build_id}` query parameter

### 4. Docker Configuration

**File:** `deployment/docker/docker_dev/docker-compose.yml`

**Port Mappings:**
- 8000 → Django app
- 5173 → Vite dev server (HMR)
- 5678 → debugpy
- 2200 → SSH gateway

**Volume Exclusions (important for performance):**
```yaml
volumes:
  - /app/staticfiles      # Excluded from host mount
  - /app/.cache           # Excluded from host mount
  - /app/.jsbuild         # TypeScript compiled JS - Docker only
```

**Node.js:** Version 20 (installed via nodesource)

### 5. Browser Cache Handling

#### Development Mode

**JSNoCacheMiddleware** (`config/middleware.py`):
```python
# Applied to all .js files in /static/
response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
response['Pragma'] = 'no-cache'
response['Expires'] = '0'
```

**cache_buster Context Processor** (`config/context_processors.py`):
- Checks JS directory modification times every 2 seconds
- Provides `{{ build_id }}` template variable (Unix timestamp)

#### Production Mode

- Content-hash filenames: `workspace-a1b2c3d4.js`
- Immutable caching (browser caches forever)
- New deployment = new hash = automatic cache invalidation

## Data Flow

### Script Loading (Simple Two-Mode)

```
{% vite_script 'console_app/workspace' %}
        │
        ▼
┌───────────────────┐
│ settings.DEBUG?   │
└───────────────────┘
        │
   ┌────┴────┐
   ▼         ▼
 True      False
   │          │
   ▼          ▼
┌─────────┐ ┌─────────────────┐
│ Vite    │ │ Vite Manifest   │
│ Server  │ │ (hashed files)  │
│ :5173   │ └─────────────────┘
└─────────┘

No fallback chain - simple and predictable.
Development requires: npm run dev
Production requires: npm run build
```

## Critical Files Summary

| File | Purpose |
|------|---------|
| `vite.config.ts` | Vite build/dev configuration |
| `tsconfig/tsconfig.base.json` | TypeScript compiler options |
| `apps/public_app/templatetags/vite.py` | Django-Vite integration |
| `config/middleware.py` | JSNoCacheMiddleware |
| `config/context_processors.py` | cache_buster |
| `deployment/docker/docker_dev/docker-compose.yml` | Docker services |
| `package.json` | Node.js dependencies |

---

## Potential Issues and Concerns

### CRITICAL Issues

#### 1. ~~Incomplete JS Path Mappings in vite.py~~ FIXED
**Status:** Resolved by removing the tsc fallback entirely.

The system now uses a simple two-mode approach:
- `DEBUG=True` → Vite dev server (requires `npm run dev`)
- `DEBUG=False` → Vite manifest (requires `npm run build`)

No fallback chain means no incomplete mappings to maintain.

#### 2. Deleted global.d.ts File
**Status:** `git status` shows `deleted: static/shared/ts/global.d.ts`

Multiple TypeScript files still reference this:
- `static/shared/ts/utils/highlight-js-bibtex.ts`
- `apps/project_app/static/project_app/ts/repository/file_edit.ts`
- `apps/project_app/static/project_app/ts/repository/file_view.ts`
- `apps/project_app/static/project_app/ts/users/profile.ts`

**Impact:** TypeScript compilation may fail or produce incorrect types.

**Recommendation:** Either restore the file or update all references.

### HIGH Priority Issues

#### 3. Duplicate package.json with Different Versions
**Files:**
- `/package.json` - TypeScript 5.2.2, @typescript-eslint 8.47.0
- `/tsconfig/package.json` - TypeScript 5.2.2, @typescript-eslint 6.5.0

**Impact:** Version mismatch between eslint plugins could cause inconsistent linting behavior.

**Recommendation:** Consolidate to single package.json or ensure versions are synchronized.

#### 4. HMR Host Configuration Mismatch
**In vite.config.ts:**
```javascript
server: {
  host: '0.0.0.0',      // Listens on all interfaces
  hmr: {
    host: '127.0.0.1',  // HMR only on localhost
  }
}
```

**In vite.py:**
```python
# Always uses 127.0.0.1
sock.connect_ex(('127.0.0.1', port))
```

**Impact:** HMR may not work when accessing Django from external hosts (e.g., `http://192.168.x.x:8000`). The browser will try to connect to `127.0.0.1:5173` which won't be accessible.

**Recommendation:** For external access, HMR host should match the request host or use relative WebSocket URLs.

#### 5. Relaxed TypeScript Configuration
**In tsconfig.base.json:**
```json
{
  "strict": false,
  "noImplicitAny": false,
  "strictNullChecks": false,
  "noUnusedLocals": false,
  "noUnusedParameters": false
}
```

**Impact:** Type safety is significantly reduced. Runtime errors may occur that TypeScript could have caught.

**Recommendation:** Gradually enable strict checks, starting with `noImplicitAny: true`.

### MEDIUM Priority Issues

#### 6. ~~Socket Detection Timeout~~ FIXED
**Status:** Resolved by using `settings.DEBUG` directly instead of socket detection.

No more network calls on every template render. Zero latency overhead.

#### 7. cache_buster Scans Multiple Directories
**In context_processors.py:35-40:**
```python
js_dirs = [
    Path(settings.BASE_DIR) / 'apps/console_app/static/console_app/js',
    Path(settings.BASE_DIR) / 'apps/figrecipe_app/static/figrecipe_app/js',
    Path(settings.BASE_DIR) / 'apps/writer_app/static/writer_app/js',
    Path(settings.BASE_DIR) / 'static/shared/js',
]
```

**Impact:** Recursively scans 4 directories every 2 seconds. With many files, this could cause performance issues.

**Recommendation:** Consider using file watchers or reducing scan frequency.

#### 8. No Production Build Validation
**Concern:** No automated check that:
- All entry points in vite.config.ts exist as actual files
- Manifest is generated correctly before deployment
- All template `{% vite_script %}` calls have corresponding entries

**Recommendation:** Add CI/CD step to validate build artifacts.

### LOW Priority Issues

#### 9. Hardcoded Port Numbers
Multiple files hardcode port 5173:
- `vite.config.ts:29`
- `vite.py:27`
- `docker-compose.yml:76`

**Recommendation:** Use environment variable for Vite port.

#### 10. Mixed Path Styles
Entry names use inconsistent path separators:
- `console_app/workspace` (forward slash)
- `scholar_app/bibtex/status-tiles` (nested forward slash)

TypeScript paths use:
- `apps/console_app/static/console_app/ts/workspace.ts`

**Impact:** Potential confusion when adding new entries.

**Recommendation:** Document the naming convention clearly.

---

## Recommendations Summary

| Priority | Issue | Action |
|----------|-------|--------|
| CRITICAL | Incomplete JS fallback mappings | Complete `_entry_to_js_path()` or remove fallback |
| CRITICAL | Deleted global.d.ts | Restore file or update references |
| HIGH | Duplicate package.json | Consolidate or sync versions |
| HIGH | HMR external access | Consider dynamic HMR host |
| HIGH | Relaxed TypeScript | Enable `noImplicitAny` |
| MEDIUM | Socket timeout | Cache Vite status check |
| MEDIUM | Directory scanning | Optimize cache_buster |
| MEDIUM | No build validation | Add CI checks |
| LOW | Hardcoded ports | Use environment variables |
| LOW | Inconsistent paths | Document conventions |

---

*Last updated: 2025-12-05*
