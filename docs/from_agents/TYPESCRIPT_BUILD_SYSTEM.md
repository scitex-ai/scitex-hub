# TypeScript Build System - Complete Guide

**Last Updated:** 2025-11-03
**Status:** ✅ Fully Configured and Working

---

## Overview

SciTeX Cloud uses TypeScript for frontend development with automatic compilation to JavaScript. The build system is integrated into Makefiles for seamless development and deployment workflows.

## Directory Structure

```
Project Root
├── tsconfig/                    ← Build configuration
│   ├── package.json            ← NPM scripts
│   ├── tsconfig.json           ← Global TS config
│   └── tsconfig.writer.json    ← Writer app specific config
│
├── static/ts/                   ← Global TypeScript sources
│   ├── types/                  (shared type definitions)
│   └── utils/                  (shared utilities: api, csrf, storage, ui)
│
├── static/js/                   ← Global compiled JavaScript
│   ├── types/                  (compiled + type defs)
│   └── utils/                  (compiled + type defs)
│
└── apps/writer_app/static/writer_app/
    ├── ts/                      ← Writer app TypeScript sources
    │   ├── index.ts
    │   ├── helpers.ts
    │   ├── modules/            (11 modules)
    │   └── utils/              (5 utilities)
    │
    └── js/                      ← Writer app compiled JavaScript
        ├── index.js
        ├── helpers.js
        ├── modules/            (compiled)
        └── utils/              (compiled)
```

## Build Commands

### Using Makefile (Recommended)

```bash
# Development environment
make ENV=dev build-ts           # Build TypeScript only
make ENV=dev setup              # Full setup (includes build-ts)
make ENV=dev rebuild            # Full rebuild (includes build-ts)

# Production environment
make ENV=prod build-ts          # Build TypeScript only
make ENV=prod setup             # Full setup (includes build-ts)

# From docker environment directory
cd deployment/docker/docker_dev
make build-ts                   # Direct build
```

### Using NPM Directly

```bash
cd frontend

# Build writer app (recommended - with cleanup)
npm run build:writer

# Build global utilities
npm run build

# Watch mode (development)
npm run build:watch

# Type check only (no compilation)
npm run type-check
```

## Build Process Flow

### Writer App Build (`npm run build:writer`)

1. **Compile TypeScript**
   - Input: `/apps/writer_app/static/writer_app/ts/**/*.ts`
   - Also includes: `/static/ts/types/`, `/static/ts/utils/`
   - Output: `/apps/writer_app/static/writer_app/js/**/*.js`
   - Generates: `.js`, `.d.ts`, `.js.map` files

2. **Auto-cleanup Nested Directories**
   - Removes: `js/apps/` (duplicate from path preservation)
   - Removes: `js/static/` (duplicate from path preservation)
   - Result: Clean, flat structure

### Why Cleanup is Needed

When TypeScript compiler (`tsc`) includes files from outside `rootDir`, it preserves the directory structure:

```
Source: /static/ts/utils/api.ts
RootDir: /
Output: /apps/writer_app/static/writer_app/js/static/ts/utils/api.js
                                            ^^^^^^^^^^^^^^^^^^^
                                            Preserved path structure
```

The cleanup step removes these nested duplicates, keeping only the correct flat structure.

## TypeScript Configuration

### `tsconfig.writer.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ES2020",
    "rootDir": "../apps/writer_app/static/writer_app/ts",
    "outDir": "../apps/writer_app/static/writer_app/js",
    "baseUrl": "..",
    "paths": {
      "@/types": ["static/ts/types/index.ts"],
      "@/utils": ["static/ts/utils/index.ts"]
    },
    // ...strict type checking options
  },
  "include": [
    "../apps/writer_app/static/writer_app/ts/**/*"
  ]
}
```

### Key Settings Explained

| Setting | Value | Purpose |
|---------|-------|---------|
| `rootDir` | `../apps/writer_app/static/writer_app/ts` | Source directory |
| `outDir` | `../apps/writer_app/static/writer_app/js` | Output directory |
| `baseUrl` | `..` | Base for path resolution |
| `paths` | `@/types`, `@/utils` | Import aliases for global utilities |

## Import Patterns

### In Writer TypeScript Files

```typescript
// Import global utilities (shared across apps)
import { getCsrfToken } from '@/utils/csrf.js';
import { StorageManager } from '@/utils/storage';
import { WriterConfig } from '@/types';

// Import local writer modules
import { EditorModule } from './modules/editor';
import { CompilationService } from './modules/compilation';
```

### Path Alias Resolution

| Alias | Resolves To | Purpose |
|-------|-------------|---------|
| `@/types` | `/static/ts/types/` | Shared type definitions |
| `@/utils` | `/static/ts/utils/` | Shared utilities (API, CSRF, storage) |
| `./modules/` | `/apps/writer_app/static/writer_app/ts/modules/` | Local modules |

## Makefile Integration

### Root Makefile (`/Makefile`)

```makefile
build-ts: validate
	@echo "Building TypeScript ($(ENV))..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build-ts
```

Delegates to environment-specific Makefile.

### Environment Makefiles

#### Development (`deployment/docker/docker_dev/Makefile`)

```makefile
build-ts:
	@echo "Building TypeScript..."
	@cd ../../.. && cd frontend && npm run build:writer
	@echo "✅ TypeScript compiled"

setup: start migrate build-ts collectstatic
	@echo "✅ Development setup complete!"

rebuild: down build up migrate build-ts collectstatic
	@echo "✅ Rebuild complete!"
```

#### Production (`deployment/docker/docker_prod/Makefile`)

```makefile
build-ts:
	@echo "Building TypeScript..."
	@cd ../../.. && cd frontend && npm run build:writer
	@echo "✅ TypeScript compiled"

collectstatic: docker-check-health build-ts
	@echo "Collecting static files..."
	@$(COMPOSE) exec -T web python manage.py collectstatic --noinput
```

Production's `collectstatic` automatically triggers `build-ts` first!

## Development Workflow

### Standard Development

```bash
# 1. Start development environment
make ENV=dev start

# 2. Make changes to TypeScript files
# Edit files in: apps/writer_app/static/writer_app/ts/

# 3. Rebuild TypeScript
make ENV=dev build-ts

# 4. Collect static files (if needed)
make ENV=dev collectstatic

# 5. Reload Django (hot reload enabled)
# Changes appear automatically
```

### Watch Mode (Continuous Compilation)

```bash
cd frontend
npm run build:watch

# TypeScript auto-recompiles on file changes
# Django hot-reloads automatically
# No manual build needed!
```

## Deployment Workflow

### Development Deployment

```bash
make ENV=dev setup
# Runs: start → migrate → build-ts → collectstatic
```

### Production Deployment

```bash
make ENV=prod setup
# Runs: build → up → migrate → collectstatic (→ build-ts)

# Or rebuild:
make ENV=prod rebuild
# Runs: down → build → up → migrate → collectstatic (→ build-ts)
```

## File Organization Rules

### ✅ DO:
- Edit only `.ts` files in `/ts/` directories
- Run `make build-ts` after TypeScript changes
- Commit `.ts` source files to Git
- Use watch mode during active development

### ❌ DON'T:
- Edit `.js` files in `/js/` (they get overwritten!)
- Manually write `.d.ts` files (auto-generated)
- Commit compiled files to Git (see .gitignore)
- Skip build step before deployment

## .gitignore Configuration

```gitignore
# TypeScript compiled output (build artifacts, not source)
apps/writer_app/static/writer_app/js/*.js
apps/writer_app/static/writer_app/js/*.js.map
apps/writer_app/static/writer_app/js/*.d.ts
apps/writer_app/static/writer_app/js/**/*.js
apps/writer_app/static/writer_app/js/**/*.js.map
apps/writer_app/static/writer_app/js/**/*.d.ts

# Keep old monolithic files directory
!apps/writer_app/static/writer_app/js/.old_monolithic_files/

# Exception: Keep non-TypeScript JavaScript
!apps/writer_app/static/writer_app/js/api-client.js

# Global static compiled output
static/js/**/*.js
static/js/**/*.d.ts
static/js/**/*.js.map
```

## Troubleshooting

### Issue: Nested directories appear (js/apps/, js/static/)

**Solution:** Already handled! The build script auto-removes them:
```bash
npm run build:writer
# Internally runs: tsc ... && rm -rf ../apps/.../js/apps ../apps/.../js/static
```

### Issue: Compiled files appear in /ts/ directory

**Cause:** Missing or incorrect `outDir` in tsconfig
**Solution:** Use `tsconfig.writer.json` with correct `outDir`:
```json
{
  "compilerOptions": {
    "outDir": "../apps/writer_app/static/writer_app/js"
  }
}
```

### Issue: Build fails with "Cannot find module '@/types'"

**Cause:** Path aliases not resolving correctly
**Solution:** Ensure `baseUrl` and `paths` are set in tsconfig:
```json
{
  "compilerOptions": {
    "baseUrl": "..",
    "paths": {
      "@/types": ["static/ts/types/index.ts"],
      "@/utils/*": ["static/ts/utils/*"]
    }
  }
}
```

## Current Status

### ✅ Fully Working

- TypeScript compilation: ✅ Working
- Auto-cleanup: ✅ Configured
- Makefile integration: ✅ Complete
- Development workflow: ✅ Streamlined
- Production workflow: ✅ Automated

### 📊 TypeScript Adoption

| Category | Status |
|----------|--------|
| **Writer App** | 95% TypeScript (18/19 files) |
| **Build System** | 100% Configured |
| **Makefile Integration** | 100% Complete |
| **Output Structure** | 100% Clean (no nesting) |

### 🎯 Remaining Work (Optional)

- [ ] Migrate `api-client.js` → `api-client.ts` (last JavaScript file)
- [ ] Update .gitignore to exclude compiled files
- [ ] Add TypeScript build to CI/CD pipeline
- [ ] Document build process for contributors

## Quick Reference

### Build Commands

```bash
# Development
make ENV=dev build-ts              # Build TypeScript
make ENV=dev setup                 # Full setup (auto-builds TS)
cd frontend && npm run build:watch # Watch mode

# Production
make ENV=prod build-ts             # Build TypeScript
make ENV=prod collectstatic        # Collects static (auto-builds TS)
```

### File Locations

| What | Where |
|------|-------|
| **TS Config** | `/tsconfig/tsconfig.writer.json` |
| **NPM Scripts** | `/tsconfig/package.json` |
| **TS Source** | `/apps/writer_app/static/writer_app/ts/` |
| **JS Output** | `/apps/writer_app/static/writer_app/js/` |
| **Global Utils** | `/static/ts/{types,utils}/` |

---

**Build system is production-ready!** 🚀
