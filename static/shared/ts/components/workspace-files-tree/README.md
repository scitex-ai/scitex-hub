# Workspace Files Tree - Shared Component

## Overview

The WorkspaceFilesTree is a unified, shared component that provides file navigation across all SciTeX workspace modules (Scholar, Vis, Writer, Code). It features mode-specific filtering, automatic focus management, and persistent state.

### Key Features

- **Mode-specific filtering**: Show only relevant files for each workspace module
- **Standardized filtering criteria**: Clear ALLOW/DENY/PRESERVE naming convention
- **Default focus paths**: Automatically expand and focus on the most relevant directory
- **Focus memory**: Remember last focused directory per mode using localStorage
- **Navigation API**: Programmatic control for scrolling, folding, and focusing
- **Always visible files**: `.gitkeep` and other critical files bypass all filtering
- **Empty directory handling**: Keep important directories visible even when empty

## Quick Start

```typescript
// Initialize the tree
const tree = new WorkspaceFilesTree({
  mode: 'vis',
  containerId: 'files-tree',
  username: 'john',
  slug: 'my-project',
});

await tree.initialize();

// Use navigation API
tree.focus('scitex/vis/data.csv', { foldOthers: true });
```

## Centralized Configuration

All filtering rules are defined in **`FilteringCriteria.ts`** with standardized naming and clear priorities.

### Available Modes

- **`scholar`**: Bibliography management - shows only `.bib` files in `scitex/scholar/`
- **`vis`**: Visualization - shows data files (`.csv`, `.tsv`, `.json`) and images in `scitex/vis/`
- **`writer`**: Document writing - shows LaTeX files and figures in `scitex/writer/`
- **`console`**: Full development - shows all files, focused on `scripts/`
- **`all`**: Fallback mode - shows all files

---

## Table of Contents

1. [Filtering System](#filtering-system)
2. [Navigation API](#navigation-api)
3. [Configuration Details](#configuration-details)
4. [Usage Examples](#usage-examples)
5. [Advanced Topics](#advanced-topics)

---

## Filtering System

### Standardized Naming Convention

All filtering criteria follow a clear, standardized naming pattern:

| Prefix | Type | Purpose | Example |
|--------|------|---------|---------|
| `ALLOW_*` | Whitelist | What IS allowed | `ALLOW_DIRECTORIES`, `ALLOW_EXTENSIONS` |
| `DENY_*` | Blacklist | What is NOT allowed | `DENY_DIRECTORIES`, `DENY_FILENAMES` |
| `PRESERVE_*` | Preservation | What to keep even when empty | `PRESERVE_EMPTY_DIRECTORIES` |

### Filtering Priority Order

Filters are applied in a specific order (higher priority = applied first):

| Priority | Criterion | Type | Description |
|----------|-----------|------|-------------|
| **0** | `ALWAYS_VISIBLE_FILENAMES` | Override | Files that bypass ALL filtering |
| **1** | `ALLOW_DIRECTORIES` | Whitelist | Only show these directories |
| **2** | `DENY_DIRECTORIES` | Blacklist | Hide these directories |
| **3** | `ALLOW_FILENAMES` | Whitelist | Only show files with these names |
| **4** | `DENY_FILENAMES` | Blacklist | Hide files with these names |
| **5** | `ALLOW_EXTENSIONS` | Whitelist | Only show these extensions |
| **6** | `DENY_EXTENSIONS` | Blacklist | Hide these extensions |
| **7** | `PRESERVE_EMPTY_DIRECTORIES` | Preservation | Keep these dirs even when empty |

### Filtering Flow Diagram

```
┌─────────────────────────────────┐
│  File/Directory from API        │
└────────────┬────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│ 0. ALWAYS_VISIBLE_FILENAMES       │
│    Is this .gitkeep or similar?   │
└────────────┬───────────────────────┘
             │ NO
             ▼
┌────────────────────────────────────┐
│ 1. ALLOW_DIRECTORIES (Whitelist)  │
│    Is path within allowed dirs?   │
└────────────┬───────────────────────┘
             │ YES
             ▼
┌────────────────────────────────────┐
│ 2. DENY_DIRECTORIES (Blacklist)   │
│    Is path in denied dirs?        │
└────────────┬───────────────────────┘
             │ NO
             ▼
┌────────────────────────────────────┐
│ 3. ALLOW_FILENAMES (Whitelist)    │
│    Is filename in allowed list?   │
└────────────┬───────────────────────┘
             │ YES (or not specified)
             ▼
┌────────────────────────────────────┐
│ 4. DENY_FILENAMES (Blacklist)     │
│    Is filename in denied list?    │
└────────────┬───────────────────────┘
             │ NO
             ▼
┌────────────────────────────────────┐
│ 5. ALLOW_EXTENSIONS (Whitelist)   │
│    Is extension in allowed list?  │
└────────────┬───────────────────────┘
             │ YES (or 'all')
             ▼
┌────────────────────────────────────┐
│ 6. DENY_EXTENSIONS (Blacklist)    │
│    Is extension in denied list?   │
└────────────┬───────────────────────┘
             │ NO
             ▼
┌────────────────────────────────────┐
│ 7. PRESERVE_EMPTY_DIRECTORIES     │
│    Keep if empty and preserved?   │
└────────────┬───────────────────────┘
             │
             ▼
          SHOW
```

**Key Principles:**
- Whitelists are checked BEFORE blacklists
- Higher priority rules can override lower priority rules
- `ALWAYS_VISIBLE_FILENAMES` bypasses ALL other rules
- Empty directories are hidden UNLESS preserved

---

## Navigation API

The tree provides a comprehensive navigation API for programmatic control:

### Basic Navigation

```typescript
// Scroll to a file/directory
tree.scrollTo('scitex/vis/data.csv', smooth: true);

// Expand a directory
tree.unfold('scitex/vis/figures');

// Collapse a directory
tree.fold('scitex/vis/figures');

// Toggle expansion
tree.toggle('scitex/vis');

// Collapse all directories
tree.foldAll();
```

### Advanced Navigation

```typescript
// Collapse all except path to target
tree.foldExcept('scitex/vis/data.csv');
// This expands: scitex, scitex/vis
// And collapses everything else

// Focus on target (comprehensive action)
tree.focus('scitex/vis/figures/plot.png', {
  foldOthers: true,   // Collapse all other directories
  highlight: true,    // Highlight the target
  smooth: true,       // Smooth scrolling
});
```

### Focus Behavior

When `tree.focus()` is called, it performs these actions automatically:

1. **Expands** all parent directories to the target
2. **Scrolls** to the target element
3. **Highlights** the target (optional pulsing animation)
4. **Collapses** all other directories (if `foldOthers: true`)
5. **Saves** the focus path to localStorage for restoration

**Focus Persistence:**
- Each mode remembers its last focused path separately
- On first load: Uses `DEFAULT_FOCUS_PATHS[mode]`
- On reload: Restores last focused path for that mode
- Persists across browser sessions (localStorage)

---

## Configuration Details

All configuration is centralized in **`FilteringCriteria.ts`**.

### 1. ALLOW_DIRECTORIES (Priority: 1 - Highest)

**Purpose:** Directory whitelist - only paths within these directories are shown

```typescript
export const ALLOW_DIRECTORIES: Record<WorkspaceMode, string[]> = {
  scholar: ['scitex/scholar'],   // Only scitex/scholar/ directory
  vis: ['scitex/vis'],           // Only scitex/vis/ directory
  writer: ['scitex/writer'],     // Only scitex/writer/ directory
  code: [],                      // All directories (no restriction)
  all: [],                       // All directories (no restriction)
};
```

Empty array `[]` = no restriction (show all directories)

### 2. DENY_DIRECTORIES (Priority: 2 - High)

**Purpose:** Directory blacklist - hide these directories (applied after ALLOW)

```typescript
export const DENY_DIRECTORIES: Record<WorkspaceMode, string[]> = {
  scholar: ['node_modules', '.git', '__pycache__', '.venv', 'build'],
  vis: ['node_modules', '.git', '__pycache__', '.venv'],
  writer: ['node_modules', '.git', '__pycache__', '.venv', 'build'],
  code: ['.git'],  // Only hide .git in code mode
  all: [],
};
```

### 3. ALLOW_FILENAMES (Priority: 3)

**Purpose:** Filename whitelist - only show files with these exact names

Currently not heavily used, but available for specific files like `README.md`, `package.json`, etc.

### 4. DENY_FILENAMES (Priority: 4)

**Purpose:** Filename blacklist - hide files with these exact names

Used to hide specific files like `.DS_Store`, `Thumbs.db`, etc.

### 5. ALLOW_EXTENSIONS (Priority: 5)

**Purpose:** Extension whitelist - only show these file extensions

```typescript
export const ALLOW_EXTENSIONS: Record<WorkspaceMode, string[] | 'all'> = {
  scholar: ['.bib'],
  vis: ['.csv', '.tsv', '.json', '.png', '.jpg', '.jpeg', '.pdf', '.svg'],
  writer: ['.tex', '.bib', '.png', '.jpg', '.jpeg', '.pdf', '.svg', '.eps'],
  code: 'all',
  all: 'all',
};
```

Value `'all'` = no restriction (show all extensions)

### 6. DENY_EXTENSIONS (Priority: 6)

**Purpose:** Extension blacklist - hide these file extensions

Currently used for hiding temporary or cache files.

### 7. PRESERVE_EMPTY_DIRECTORIES (Priority: 7 - Lowest)

**Purpose:** Keep these directories visible even when empty after filtering

```typescript
export const PRESERVE_EMPTY_DIRECTORIES: Record<WorkspaceMode, string[]> = {
  scholar: [
    'scitex/scholar',
    'scitex/scholar/references',
    'scitex/scholar/bibliography',
  ],
  vis: [
    'scitex/vis',
    'scitex/vis/ai',
    'scitex/vis/figures',
    'scitex/vis/data',
    'scitex/vis/panels',
    'scitex/vis/previews',
  ],
  writer: [
    'scitex/writer',
    'scitex/writer/01_manuscript',
    'scitex/writer/02_supplementary',
    'scitex/writer/03_revision',
    'scitex/writer/shared',
  ],
  code: [],
  all: [],
};
```

This ensures important directory structures remain visible for drag-and-drop operations.

### 8. DEFAULT_FOCUS_PATHS

**Purpose:** Default directory to focus and expand when entering each workspace mode

```typescript
export const DEFAULT_FOCUS_PATHS: Record<WorkspaceMode, string> = {
  scholar: 'scitex/scholar',              // Focus on bibliography directory
  vis: 'scitex/vis',                      // Focus on visualization directory
  writer: 'scitex/writer/01_manuscript',  // Focus on manuscript directory
  code: 'scripts',                        // Focus on scripts/ (NOT scitex/console/)
  all: '',
};
```

**Focus Memory Behavior:**
- On first visit: Expands to `DEFAULT_FOCUS_PATHS[mode]`
- On subsequent visits: Expands to last focused directory (remembered per mode)
- Focus is saved automatically when using `tree.focus()` or navigating
- Focus memory is per-mode and persists across browser sessions

### 9. ALWAYS_VISIBLE_FILENAMES

**Purpose:** Files that bypass ALL filtering rules (Priority: 0 - Override)

```typescript
export const ALWAYS_VISIBLE_FILENAMES: string[] = [
  '.gitkeep',
];
```

These files are always shown regardless of extension whitelists, making empty directories usable for drag-and-drop.

---

## Usage Examples

### Scholar App

```typescript
const tree = new WorkspaceFilesTree({
  mode: 'scholar',
  containerId: 'file-tree',
  username: 'john',
  slug: 'my-research',
});

await tree.initialize();

// Tree will automatically:
// 1. Show only scitex/scholar/ directory
// 2. Show only .bib files
// 3. Focus on scitex/scholar/ by default
// 4. Always show .gitkeep files
```

### Vis App

```typescript
const tree = new WorkspaceFilesTree({
  mode: 'vis',
  containerId: 'file-tree',
  username: 'john',
  slug: 'my-project',
});

await tree.initialize();

// Later: Focus on a specific data file
tree.focus('scitex/vis/data/experiment.csv', {
  foldOthers: true,
  highlight: true,
});

// This path will be remembered for next visit
```

### Writer App

```typescript
const tree = new WorkspaceFilesTree({
  mode: 'writer',
  containerId: 'file-tree',
  username: 'john',
  slug: 'my-paper',
});

await tree.initialize();

// Tree will automatically:
// 1. Show only scitex/writer/ directory
// 2. Show only .tex, .bib, and image files
// 3. Focus on scitex/writer/01_manuscript/ by default
// 4. Preserve empty manuscript/supplementary/revision directories
```

### Console App

```typescript
const tree = new WorkspaceFilesTree({
  mode: 'console',
  containerId: 'file-tree',
  username: 'john',
  slug: 'my-project',
});

await tree.initialize();

// Tree will automatically:
// 1. Show ALL directories (no restriction)
// 2. Show ALL file types (no extension filtering)
// 3. Focus on scripts/ by default
// 4. Only hide .git directory
```

---

## Advanced Topics

### Handling Empty Directories

Directories are preserved even when empty if they match:
- `PRESERVE_EMPTY_DIRECTORIES` (e.g., `scitex/vis/figures/`, `scitex/writer/01_manuscript/`)

### `.gitkeep` Files

`.gitkeep` files are handled specially:
- **Always visible**: Included in `ALWAYS_VISIBLE_FILENAMES` (bypasses all filtering)
- **Purpose**: Makes empty directories usable for drag-and-drop
- **Result**: Directories with only `.gitkeep` show the file and remain visible

This ensures important directory structures remain visible for file operations.

### Module Independence & Cross-Module References

**Design Philosophy:** Independence > Convenience, Explicit > Implicit

SciTeX modules are designed to be independent while allowing controlled sharing via **symlinks**.

#### Directory Structure for Sharing

```
scitex/
├── scholar/
│   └── bib_files/              ← Bibliography files (.bib)
│
├── vis/
│   ├── data/                   ← Input data
│   ├── figures/                ← Generated figures
│   └── exports/                ← 🔗 Shared with other modules
│
└── writer/
    ├── shared/                 ← 🔗 Symlinks to scholar/bib_files/
    ├── 01_manuscript/figures/  ← 🔗 Symlinks to vis/exports/
    ├── 02_supplementary/figures/
    └── 03_revision/figures/
```

#### Allowed Symlink Patterns

**✅ Allowed:**
- `vis/exports/*` → `writer/*/figures/*` (Vis figures to Writer)
- `scholar/bib_files/*` → `writer/shared/*` (Scholar bibliography to Writer)
- Within same module (any symlink)

**❌ Not Allowed:**
- Direct cross-module access without symlinks
- Scholar referencing other modules
- Circular references

#### Benefits

**For Cloud Users:**
- Ctrl+Drag to create symlinks (planned feature)
- Clear visual indication of shared resources
- No confusion about file locations

**For Local Users:**
```bash
git clone https://github.com/user/project
ls scitex/
# scholar/  code/  vis/  writer/  ← Clear structure

cd scitex/writer/01_manuscript/figures
ls -la
# plot_1.png → ../../vis/exports/plot_1.png  ← Symlink works locally
```

**For Details:** See `MODULE_INDEPENDENCE_SPEC.md` for complete specification including:
- Module reference rules
- Symlink validation
- Ctrl+Drag UI implementation
- Migration guide

### How to Add a New File Type

To add support for a new file type in a specific mode:

1. Open **`FilteringCriteria.ts`**
2. Find the mode in `ALLOW_EXTENSIONS`
3. Add the extension to the array (include the leading dot)

**Example**: Add `.txt` files to writer mode:

```typescript
export const ALLOW_EXTENSIONS: Record<WorkspaceMode, string[] | 'all'> = {
  writer: [
    '.tex',
    '.bib',
    '.txt',  // ← Add this line
    '.png',
    // ... rest of extensions
  ],
  // ... other modes
};
```

4. TypeScript will auto-compile via watch mode

### How to Hide a Folder

To hide a folder from a specific mode:

1. Open **`FilteringCriteria.ts`**
2. Find the mode in `DENY_DIRECTORIES`
3. Add the folder name to the array

**Example**: Hide `temp` folder in all modes:

```typescript
export const DENY_DIRECTORIES: Record<WorkspaceMode, string[]> = {
  scholar: ['node_modules', '.git', '__pycache__', '.venv', 'build', 'temp'],
  vis: ['node_modules', '.git', '__pycache__', '.venv', 'temp'],
  writer: ['node_modules', '.git', '__pycache__', '.venv', 'build', 'temp'],
  code: ['.git', 'temp'],
  // ...
};
```

### How to Change Default Focus

To change the default focus path for a mode:

1. Open **`FilteringCriteria.ts`**
2. Find the mode in `DEFAULT_FOCUS_PATHS`
3. Update the path

**Example**: Change writer mode to focus on revision directory:

```typescript
export const DEFAULT_FOCUS_PATHS: Record<WorkspaceMode, string> = {
  writer: 'scitex/writer/03_revision',  // Changed from 01_manuscript
  // ... other modes
};
```

Note: This only affects first-time visitors. Returning users will see their last focused path.

## Writer Mode: Document Type Filtering

Writer mode has special support for document type (doctype) filtering. When a doctype is selected, the tree only shows files relevant to that document type.

### Document Type Directories

```typescript
export const WRITER_DOCTYPE_DIRECTORIES = {
  manuscript: ['scitex/writer/01_manuscript', '01_manuscript'],
  supplementary: ['scitex/writer/02_supplementary', '02_supplementary'],
  revision: ['scitex/writer/03_revision', '03_revision'],
};
```

### Using Doctype-Responsive Filtering

```javascript
import { createWriterDoctypeFilter } from './ModeFilters.js';

// Show only manuscript files
const manuscriptFilter = createWriterDoctypeFilter('manuscript');

// Show only supplementary files
const supplementaryFilter = createWriterDoctypeFilter('supplementary');

// Show all writer files (no doctype restriction)
const allWriterFilter = createWriterDoctypeFilter(null);
```

**Note**: The `shared` directory is always visible regardless of doctype.

## Usage in Apps

Each app automatically gets the correct filtering by specifying the mode:

### Scholar App
```javascript
const tree = new WorkspaceFilesTree({
  mode: 'scholar',  // Only .bib files visible
  containerId: 'file-tree',
  username: '{{ username }}',
  slug: '{{ slug }}',
});
```

### Vis App
```javascript
const tree = new WorkspaceFilesTree({
  mode: 'vis',  // Only data/image files visible
  containerId: 'file-tree',
  username: '{{ username }}',
  slug: '{{ slug }}',
});
```

### Writer App
```javascript
const tree = new WorkspaceFilesTree({
  mode: 'writer',  // Only document files visible
  containerId: 'file-tree',
  username: '{{ username }}',
  slug: '{{ slug }}',
});
```

### Console App
```javascript
const tree = new WorkspaceFilesTree({
  mode: 'console',  // All files visible
  containerId: 'file-tree',
  username: '{{ username }}',
  slug: '{{ slug }}',
});
```

## Filter Behavior

The filtering system applies multiple layers of rules:

### 1. Directory Filtering (First Pass)
Files outside the allowed directories are hidden:
- **Scholar**: Only shows `scitex/scholar/` directory
- **Vis**: Only shows `scitex/vis/` directory
- **Writer**: Only shows `scitex/writer/` directory (or doctype-specific subdirectories)
- **Code**: Shows all directories

### 2. System Folder Hiding (Second Pass)
Common system folders are hidden to reduce noise:
- `.git`, `node_modules`, `__pycache__`, `.venv`, `build`

### 3. Extension Filtering (Third Pass)
Files that don't match the mode's allowed extensions are hidden:
- **Scholar**: Only `.bib` files
- **Vis**: Only data/image files (`.csv`, `.png`, `.pdf`, etc.)
- **Writer**: Only document files (`.tex`, `.bib`, images)
- **Code**: All file types

### 4. Empty Folder Cleanup (Final Pass)
Folders that become empty after filtering are also hidden.

### Complete Example: Vis Mode

```
Project Structure:        What Vis Sees:
├── scitex/              ├── scitex/
│   ├── scholar/         │   └── vis/         (scholar/ hidden - sibling)
│   ├── writer/          │       ├── data.csv ✓
│   └── vis/             │       ├── plot.png ✓
│       ├── data.csv     │       └── script.py (hidden - wrong extension)
│       ├── plot.png
│       └── script.py    (writer/ hidden - sibling)
├── src/                 (src/ hidden - wrong directory)
└── node_modules/        (node_modules/ hidden - system folder)
```

**Key Point**: Sibling directories (like `scitex/writer/` and `scitex/scholar/`) are completely hidden in Vis mode. Only `scitex/vis/` and its parent `scitex/` are shown.

### Directory Filtering Logic

The filter determines visibility with this logic:

1. **Is this path INSIDE an allowed directory?** → ✓ SHOW
   - Example: `scitex/vis/data.csv` is inside `scitex/vis/` → SHOW

2. **Is this path a PARENT of an allowed directory?** → ✓ SHOW
   - Example: `scitex/` is parent of `scitex/vis/` → SHOW

3. **Otherwise** → ✗ HIDE
   - Example: `scitex/writer/` is sibling to `scitex/vis/` → HIDE

## Benefits

✅ **Reduced Cognitive Load** - Users only see relevant files for their current task
✅ **Consistent UX** - Same tree component with mode-specific behavior
✅ **Easy Maintenance** - Single configuration file for all modes
✅ **Performance** - Fewer DOM nodes to render
✅ **Backward Compatible** - Falls back to showing all files if mode not specified

## Migration from Legacy Filters

The old `MODE_FILTERS` in `types.ts` is deprecated. The new centralized configuration in `FilteringCriteria.ts` provides:

- **Standardized naming**: `ALLOW_*`, `DENY_*`, `PRESERVE_*` pattern
- **Clear priorities**: Numbered 0-7 for predictable behavior
- **Better organization**: Separate file with comprehensive documentation
- **More comprehensive**: 9 different filtering criteria
- **Easier to understand and maintain**: Self-documenting code
- **Better documentation**: This README and inline comments

Legacy code will continue to work via `ModeFilters.ts`, but new code should use `FilteringCriteria.ts`.

---

## Where to Find Documentation

The workspace-files-tree component has comprehensive documentation across multiple files:

### 📄 Component Documentation

| File | Location | Purpose |
|------|----------|---------|
| **README.md** | `static/shared/ts/components/workspace-files-tree/` | **This file** - Overview, filtering system, configuration |
| **API.md** | `static/shared/ts/components/workspace-files-tree/` | Navigation API reference with examples |
| **FILTERING_SPEC.md** | `static/shared/ts/components/workspace-files-tree/` | Detailed filtering specification |
| **MODULE_INDEPENDENCE_SPEC.md** | `static/shared/ts/components/workspace-files-tree/` | Module independence & symlink-based cross-module references |
| **FilteringCriteria.ts** | `static/shared/ts/components/workspace-files-tree/` | Source of truth for all filtering rules |

### 🎯 Quick Reference

**For Developers:**
- **How to use the tree?** → Start with [Quick Start](#quick-start) above
- **How to navigate programmatically?** → See [Navigation API](#navigation-api)
- **How filtering works?** → See [Filtering System](#filtering-system)
- **Need detailed API docs?** → Read `API.md`

**For Configuration:**
- **Add a file type?** → Edit `ALLOW_EXTENSIONS` in `FilteringCriteria.ts`
- **Hide a folder?** → Edit `DENY_DIRECTORIES` in `FilteringCriteria.ts`
- **Change default focus?** → Edit `DEFAULT_FOCUS_PATHS` in `FilteringCriteria.ts`
- **Preserve empty dir?** → Edit `PRESERVE_EMPTY_DIRECTORIES` in `FilteringCriteria.ts`

**For Understanding:**
- **Filtering priority order?** → See [Filtering Priority Order](#filtering-priority-order)
- **Filtering flow diagram?** → See [Filtering Flow Diagram](#filtering-flow-diagram)
- **Mode-specific behavior?** → See [Available Modes](#available-modes)

### 📁 File Locations

```
static/shared/
├── css/components/
│   └── workspace-files-tree.css           # Styling
└── ts/components/workspace-files-tree/
    ├── README.md                           # Overview & filtering (this file)
    ├── API.md                              # Navigation API reference
    ├── FILTERING_SPEC.md                   # Detailed filtering spec
    ├── MODULE_INDEPENDENCE_SPEC.md         # 🔗 Module independence & symlinks
    ├── FilteringCriteria.ts                # ⭐ Filtering configuration
    ├── WorkspaceFilesTree.ts               # Main component
    ├── TreeFilter.ts                       # Filtering logic
    ├── TreeNavigation.ts                   # Navigation logic
    ├── TreeState.ts                        # State management
    ├── TreeRenderer.ts                     # Rendering logic
    └── types.ts                            # TypeScript types
```

### 🔗 Related Documentation

- **App Integration**: See individual app READMEs (scholar_app, figrecipe_app, writer_app, console_app)
- **CSS Styling**: See `workspace-files-tree.css` for styling details
- **TypeScript Types**: See `types.ts` for type definitions

---

**Last Updated:** 2025-11-26
**Component Version:** 2.0 (Standardized Filtering System)
