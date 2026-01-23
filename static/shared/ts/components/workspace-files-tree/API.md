# Workspace Files Tree - Public API

## Overview

The WorkspaceFilesTree component provides a comprehensive API for navigation and filtering with standardized naming conventions.

## Navigation API

### Basic Navigation

```typescript
// Scroll to a file/directory
tree.scrollTo('scitex/vis/data.csv', smooth?: boolean);

// Expand a directory
tree.unfold('scitex/vis');

// Collapse a directory
tree.fold('scitex/vis');

// Toggle directory expansion
tree.toggle('scitex/vis');
```

### Advanced Navigation

```typescript
// Focus on a specific target (expand path, scroll, highlight)
tree.focus('scitex/vis/figures/plot.png', {
  foldOthers?: boolean,  // Collapse all other directories (default: false)
  highlight?: boolean,   // Highlight the target (default: true)
  smooth?: boolean,      // Smooth scrolling (default: true)
});

// Collapse all except path to target
tree.foldExcept('scitex/vis/data.csv');

// Collapse all directories
tree.foldAll();
```

## Usage Examples

### Example 1: Focus on a Specific File

```typescript
// In vis mode, focus on a specific data file
const tree = new WorkspaceFilesTree({
  mode: 'vis',
  containerId: 'file-tree',
  username: 'john',
  slug: 'my-project',
});

await tree.initialize();

// Focus on the file, folding everything else
tree.focus('scitex/vis/data.csv', {
  foldOthers: true,
  highlight: true,
});
```

### Example 2: Navigate to Recently Modified File

```typescript
// After detecting a file change, navigate to it
function onFileModified(filePath: string) {
  tree.scrollTo(filePath, true);  // Smooth scroll
}
```

### Example 3: Expand Only Relevant Directories

```typescript
// When loading a specific document in writer mode
tree.foldExcept('scitex/writer/01_manuscript/main.tex');
// This expands: scitex, scitex/writer, scitex/writer/01_manuscript
// And collapses everything else
```

## Filtering API

### Filtering Criteria (Standardized)

All filtering criteria follow a standardized naming convention:

| Criterion | Type | Priority | Description |
|-----------|------|----------|-------------|
| `ALLOW_DIRECTORIES` | Whitelist | 1 (Highest) | Only show these directories |
| `DENY_DIRECTORIES` | Blacklist | 2 (High) | Hide these directories |
| `ALLOW_FILENAMES` | Whitelist | 3 (Medium-High) | Only show files with these names |
| `DENY_FILENAMES` | Blacklist | 4 (Medium) | Hide files with these names |
| `ALLOW_EXTENSIONS` | Whitelist | 5 (Medium-Low) | Only show these extensions |
| `DENY_EXTENSIONS` | Blacklist | 6 (Low) | Hide these extensions |
| `PRESERVE_EMPTY_DIRECTORIES` | Preservation | 7 (Lowest) | Keep these directories even when empty |

### Filtering Configuration

Filtering criteria are defined in `FilteringCriteria.ts`:

```typescript
import {
  ALLOW_DIRECTORIES,
  DENY_DIRECTORIES,
  ALLOW_FILENAMES,
  DENY_FILENAMES,
  ALLOW_EXTENSIONS,
  DENY_EXTENSIONS,
  PRESERVE_EMPTY_DIRECTORIES,
} from './FilteringCriteria.js';

// Example: Check if vis mode allows a directory
const visAllowed = ALLOW_DIRECTORIES['vis'];  // ['scitex/vis']

// Example: Check if .csv files are allowed in vis mode
const visExtensions = ALLOW_EXTENSIONS['vis'];  // ['.csv', '.png', ...]
```

## Filtering Flow

```
┌─────────────────────────────────┐
│  File/Directory from API        │
└────────────┬────────────────────┘
             │
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

## Mode-Specific Behavior

### Scholar Mode
```typescript
mode: 'scholar'

Filtering:
- Directories: Only scitex/scholar/
- Extensions: Only .bib files
- Focus: scitex/scholar/
```

### Vis Mode
```typescript
mode: 'vis'

Filtering:
- Directories: Only scitex/vis/
- Extensions: .csv, .tsv, .json, .png, .jpg, .pdf, .svg
- Focus: scitex/vis/
- Preserved: scitex/vis/figures/, scitex/vis/data/, etc.
```

### Writer Mode
```typescript
mode: 'writer'

Filtering:
- Directories: Only scitex/writer/
- Extensions: .tex, .bib, .png, .jpg, .pdf, .svg, .eps
- Focus: scitex/writer/01_manuscript/
- Preserved: scitex/writer/01_manuscript/, 02_supplementary/, etc.
```

### Code Mode
```typescript
mode: 'code'

Filtering:
- Directories: All (no restriction)
- Extensions: All (no restriction)
- Focus: scripts/
- Only .git is hidden
```

## Best Practices

### 1. Use Standardized Names

✅ **Good**:
```typescript
ALLOW_DIRECTORIES  // Clear: this is a whitelist of directories
DENY_EXTENSIONS    // Clear: this is a blacklist of extensions
```

❌ **Bad**:
```typescript
HIDDEN_FOLDERS     // Ambiguous: hidden from what? blacklist?
VIEWABLE_FILES     // Unclear: viewable or whitelisted?
```

### 2. Follow Priority Order

Whitelists should be checked before blacklists:
1. `ALLOW_*` (whitelist) - Define what IS allowed
2. `DENY_*` (blacklist) - Define what is NOT allowed

### 3. Separate Concerns

- **Directory filtering**: `ALLOW_DIRECTORIES`, `DENY_DIRECTORIES`
- **Filename filtering**: `ALLOW_FILENAMES`, `DENY_FILENAMES`
- **Extension filtering**: `ALLOW_EXTENSIONS`, `DENY_EXTENSIONS`
- **Preservation**: `PRESERVE_EMPTY_DIRECTORIES`

### 4. Use Focus API for Navigation

```typescript
// Instead of manually expanding each parent
tree.stateManager.expand('scitex');
tree.stateManager.expand('scitex/vis');
tree.scrollTo('scitex/vis/data.csv');

// Use focus() which does it all
tree.focus('scitex/vis/data.csv');
```

## Debugging

### Check Current State

```typescript
// Check if a directory is expanded
tree.stateManager.isExpanded('scitex/vis');

// Get all expanded directories
tree.stateManager.getExpanded();

// Check if path is visible
tree.navigation.isPathVisible('scitex/vis/data.csv');
```

### Console Logging

The component logs navigation actions:
```
[TreeNavigation] Scrolled to: scitex/vis/data.csv
[TreeNavigation] Folded: scitex/writer
[TreeNavigation] Focusing on: scitex/vis/figures/plot.png
```

## Migration Guide

### From Old System

**Old**:
```typescript
HIDDEN_FOLDERS = ['node_modules', '.git']
MODE_FILE_EXTENSIONS = { vis: ['.csv', '.png'] }
```

**New**:
```typescript
DENY_DIRECTORIES = { vis: ['node_modules', '.git'] }
ALLOW_EXTENSIONS = { vis: ['.csv', '.png'] }
```

### Benefits of New System

1. **Standardized naming**: `ALLOW_*` vs `DENY_*` is immediately clear
2. **Clear priority**: Higher number = lower priority
3. **Separated concerns**: Directory, filename, extension filters are separate
4. **Better documentation**: Each criterion has its own section
5. **Easier to extend**: Add new criteria following the same pattern
