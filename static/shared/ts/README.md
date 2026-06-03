# SciTeX TypeScript Source Code

This directory contains the TypeScript source code for SciTeX Hub applications.

## Directory Structure

```
ts/
├── types/
│   └── index.ts              # Shared type definitions
│       ├── WriterConfig
│       ├── EditorState
│       ├── CompilationJob
│       ├── HistoryEntry
│       └── SectionMetadata
│
├── utils/
│   ├── csrf.ts               # CSRF token utility
│   │   └── getCsrfToken()
│   │
│   ├── storage.ts            # Storage management
│   │   └── StorageManager class
│   │       ├── save<T>(key, data)
│   │       ├── load<T>(key)
│   │       ├── exists(key)
│   │       ├── remove(key)
│   │       └── clear()
│   │
│   ├── api.ts                # API client with CSRF
│   │   └── ApiClient class
│   │       ├── get<T>(url)
│   │       ├── post<T>(url, body)
│   │       ├── put<T>(url, body)
│   │       ├── patch<T>(url, body)
│   │       └── delete<T>(url)
│   │
│   ├── ui.ts                 # UI utilities
│   │   ├── showToast(message, type, duration)
│   │   ├── setButtonLoading(button, isLoading)
│   │   ├── showSpinner(containerId)
│   │   ├── Modal class
│   │   ├── debounce<T>(func, wait)
│   │   ├── throttle<T>(func, limit)
│   │   └── confirm(message)
│   │
│   └── index.ts              # Utils export index
│
└── writer/
    ├── index.ts              # Main writer app entry point
    │   ├── setupWorkspaceInitialization()
    │   ├── initializeEditor()
    │   ├── setupEditorListeners()
    │   ├── setupSectionListeners()
    │   ├── setupCompilationListeners()
    │   └── setupThemeListener()
    │
    └── modules/
        ├── editor.ts         # Editor module
        │   └── WriterEditor class
        │       ├── getContent()
        │       ├── setContent(content)
        │       ├── getWordCount()
        │       ├── addToHistory(content, wordCount)
        │       ├── undo()
        │       ├── redo()
        │       └── onChange(callback)
        │
        ├── sections.ts       # Sections manager
        │   └── SectionsManager class
        │       ├── getAll()
        │       ├── getVisible()
        │       ├── get(id)
        │       ├── add(section)
        │       ├── update(id, changes)
        │       ├── setContent(id, content)
        │       ├── getContent(id)
        │       ├── switchTo(id)
        │       ├── reorder(orderMap)
        │       ├── exportCombined()
        │       └── getTotalWordCount()
        │
        ├── compilation.ts    # Compilation manager
        │   └── CompilationManager class
        │       ├── compile(options)
        │       ├── getStatus(jobId)
        │       ├── cancel(jobId)
        │       ├── onProgress(callback)
        │       ├── onComplete(callback)
        │       └── onError(callback)
        │
        └── index.ts          # Modules export index
```

## Import Paths

Using TypeScript path aliases configured in `tsconfig.json`:

```typescript
// Shared utilities
import { getCsrfToken } from '@/utils/csrf';
import { StorageManager, globalStorage } from '@/utils/storage';
import { ApiClient, apiClient } from '@/utils/api';
import { showToast, debounce } from '@/utils/ui';

// Shared types
import { WriterConfig, EditorState } from '@/types';

// Writer modules
import { WriterEditor } from '@/writer/modules/editor';
import { SectionsManager } from '@/writer/modules/sections';
import { CompilationManager } from '@/writer/modules/compilation';

// Or from index files
import { getCsrfToken, showToast } from '@/utils';
import { WriterEditor, SectionsManager, CompilationManager } from '@/writer/modules';
```

## Module Sizes

| Module | Lines | Responsibility |
|--------|-------|-----------------|
| `types/index.ts` | 45 | Type definitions |
| `utils/csrf.ts` | 35 | CSRF token handling |
| `utils/storage.ts` | 90 | LocalStorage management |
| `utils/api.ts` | 115 | API client |
| `utils/ui.ts` | 180 | UI utilities |
| `writer/modules/editor.ts` | 180 | CodeMirror wrapper |
| `writer/modules/sections.ts` | 240 | Section management |
| `writer/modules/compilation.ts` | 210 | Compilation management |
| `writer/index.ts` | 380 | Main app entry |
| **Total** | **~1505** | **Complete app logic** |

## Building

### Development
```bash
npm run build:watch
```

Automatically recompiles on file changes.

### Production
```bash
npm run build
```

One-time compilation to `static/js/` and `apps/*/static/*/js/`.

### Type Checking
```bash
npm run type-check
```

Check for type errors without compiling.

## Module Dependencies

```
writer/index.ts
├── types/
├── utils/
│   ├── csrf
│   ├── storage
│   └── ui
└── writer/modules/
    ├── editor.ts
    ├── sections.ts
    └── compilation.ts
        └── utils/api
```

## Compilation Output

After building, compiled JavaScript is available at:

- **Utilities**: `static/js/utils/`
- **Types**: `static/js/types/`
- **Writer App**: `static/js/writer/`

## Adding New Modules

To add a new app module (e.g., Scholar):

1. Create `static/ts/scholar/` directory
2. Create modules in `static/ts/scholar/modules/`
3. Create `static/ts/scholar/index.ts` as entry point
4. Import shared utilities from `@/utils`
5. Use shared types from `@/types`

Example structure:
```
scholar/
├── index.ts
└── modules/
    ├── search.ts
    ├── results.ts
    └── index.ts
```

## Configuration

- **TypeScript Config**: `../../tsconfig.json`
- **Build Scripts**: `../../package.json`
- **Dependencies**: `../../package.json`

## Documentation

See project root for detailed guides:
- `TYPESCRIPT_SETUP.md` - Quick start
- `TYPESCRIPT_MIGRATION.md` - Complete reference
- `TYPESCRIPT_REFACTOR_SUMMARY.md` - Architecture overview

## Testing

Each module can be tested independently:

```typescript
// Test editor module
import { WriterEditor } from '@/writer/modules/editor';

const editor = new WriterEditor({ elementId: 'test-editor' });
editor.setContent('test');
assert(editor.getContent() === 'test');
```

## Linting & Formatting

```bash
npm run lint      # ESLint
npm run format    # Prettier
```

## Common Issues

1. **Module not found**: Check import paths match `baseUrl` and `paths` in `tsconfig.json`
2. **"Cannot find name 'CodeMirror'"**: Ensure CodeMirror is loaded before the app
3. **Type errors**: Run `npm run type-check` to see all issues
4. **Build fails**: Run `npm install` to ensure dependencies installed

---

**Ready to develop?** See `TYPESCRIPT_SETUP.md` for the quick start guide.
