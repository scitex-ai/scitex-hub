# Workspace Files Tree - Filtering Specification

This document provides a systematic specification of all filtering criteria used in the WorkspaceFilesTree component.

## Filtering Criteria Order

Filters are applied in this specific order:

1. **Directory Whitelist** (ALLOWED_DIRECTORIES)
2. **Directory Blacklist** (HIDDEN_FOLDERS)
3. **Extension Whitelist** (MODE_FILE_EXTENSIONS)
4. **Extension Blacklist** (disabledExtensions)
5. **Filename Patterns** (future)

---

## 1. Directory Whitelist (ALLOWED_DIRECTORIES)

**Purpose**: Restrict tree to show only specific directories per mode

**Location**: `ModeFilters.ts` → `ALLOWED_DIRECTORIES`

**Behavior**:
- If a path is NOT within an allowed directory → **HIDE**
- If a path IS a parent of an allowed directory → **SHOW** (to maintain tree structure)
- If no directories specified → **SHOW ALL** (no restriction)

**Configuration**:
```typescript
export const ALLOWED_DIRECTORIES: Record<WorkspaceMode, string[]> = {
  scholar: ['scitex/scholar'],     // ✓ Only scholar directory
  vis: ['scitex/vis'],             // ✓ Only vis directory
  writer: ['scitex/writer'],       // ✓ Only writer directory
  code: [],                        // ✓ All directories (no restriction)
  all: [],                         // ✓ All directories (no restriction)
};
```

**Examples**:

### Vis Mode (allowed: `['scitex/vis']`)

| Path | Check | Result | Reason |
|------|-------|--------|--------|
| `scitex/` | Parent of `scitex/vis/` | ✓ SHOW | Needed for tree structure |
| `scitex/vis/` | Equals allowed dir | ✓ SHOW | Matches whitelist |
| `scitex/vis/data.csv` | Inside allowed dir | ✓ SHOW | Within whitelist |
| `scitex/writer/` | Sibling | ✗ HIDE | Not in whitelist, not a parent |
| `scitex/scholar/` | Sibling | ✗ HIDE | Not in whitelist, not a parent |
| `src/` | Unrelated | ✗ HIDE | Not in whitelist, not a parent |

---

## 2. Directory Blacklist (HIDDEN_FOLDERS)

**Purpose**: Hide common system folders across all modes

**Location**: `ModeFilters.ts` → `HIDDEN_FOLDERS`

**Behavior**:
- If directory name matches a pattern → **HIDE**
- If path contains a blacklisted folder → **HIDE**

**Configuration**:
```typescript
export const HIDDEN_FOLDERS: Record<WorkspaceMode, string[]> = {
  scholar: ['node_modules', '.git', '__pycache__', '.venv', 'build'],
  vis: ['node_modules', '.git', '__pycache__', '.venv'],
  writer: ['node_modules', '.git', '__pycache__', '.venv', 'build'],
  code: ['.git'],  // Even in code mode, .git is too noisy
  all: [],
};
```

**Examples**:

| Path | Pattern | Result |
|------|---------|--------|
| `node_modules/` | 'node_modules' | ✗ HIDE |
| `.git/` | '.git' | ✗ HIDE |
| `scitex/vis/__pycache__/` | '__pycache__' | ✗ HIDE |
| `scitex/.venv/` | '.venv' | ✗ HIDE |
| `build/output/` | 'build' | ✗ HIDE |

---

## 3. Extension Whitelist (MODE_FILE_EXTENSIONS)

**Purpose**: Show only relevant file types per mode

**Location**: `ModeFilters.ts` → `MODE_FILE_EXTENSIONS`

**Behavior**:
- If extension IS in whitelist → **SHOW**
- If extension is NOT in whitelist → **HIDE**
- If whitelist is `'all'` → **SHOW ALL** extensions

**Configuration**:
```typescript
export const MODE_FILE_EXTENSIONS: Record<WorkspaceMode, string[] | 'all'> = {
  scholar: ['.bib'],  // Only bibliography files

  vis: [
    '.csv', '.tsv', '.json',           // Data files
    '.png', '.jpg', '.jpeg', '.svg',   // Images
    '.pdf',                             // Documents
  ],

  writer: [
    '.tex', '.bib',                     // LaTeX files
    '.png', '.jpg', '.jpeg', '.svg',    // Images
    '.pdf', '.eps',                     // Figures
  ],

  code: 'all',  // All extensions
  all: 'all',   // All extensions
};
```

**Examples**:

### Vis Mode (extensions: `['.csv', '.png', '.pdf', ...]`)

| File | Extension | In Whitelist? | Result |
|------|-----------|---------------|--------|
| `data.csv` | `.csv` | ✓ Yes | ✓ SHOW |
| `plot.png` | `.png` | ✓ Yes | ✓ SHOW |
| `report.pdf` | `.pdf` | ✓ Yes | ✓ SHOW |
| `analysis.py` | `.py` | ✗ No | ✗ HIDE |
| `README.md` | `.md` | ✗ No | ✗ HIDE |
| `config.json` | `.json` | ✓ Yes | ✓ SHOW |

---

## 4. Extension Blacklist (disabledExtensions)

**Purpose**: Gray out certain file types while keeping them visible

**Location**: `TreeFilter` config → `disabledExtensions`

**Behavior**:
- If extension is in blacklist → **SHOW but DISABLED** (grayed out)
- File is visible but not clickable

**Configuration**:
```typescript
// Example usage (currently deprecated in favor of whitelist)
disabledExtensions: ['.py', '.js', '.ts']
```

**Visual Effect**:
```
✓ data.csv         (clickable)
✓ plot.png         (clickable)
⊘ script.py        (visible but grayed out, not clickable)
```

**Note**: This is currently deprecated. The extension whitelist (criterion #3) handles this more cleanly by completely hiding non-whitelisted files.

---

## 5. Filename Patterns (FUTURE)

**Purpose**: Filter files by name patterns (not yet implemented)

**Planned Usage**:
```typescript
// Future implementation
FILENAME_BLACKLIST = {
  vis: ['*.tmp', '*.cache', '.DS_Store'],
  writer: ['*.aux', '*.log', '*.out'],
};
```

---

## Complete Filtering Flow

```
┌─────────────────────────────────────┐
│  File/Directory from API            │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 1. DIRECTORY WHITELIST               │
│    Is path within ALLOWED_DIRECTORIES?│
└──────────────┬───────────────────────┘
               │ Yes
               ▼
┌──────────────────────────────────────┐
│ 2. DIRECTORY BLACKLIST               │
│    Is path in HIDDEN_FOLDERS?        │
└──────────────┬───────────────────────┘
               │ No
               ▼
┌──────────────────────────────────────┐
│ Is this a directory?                 │
└──────┬───────────────────────┬───────┘
       │ Yes                   │ No (it's a file)
       │                       ▼
       │              ┌──────────────────────────┐
       │              │ 3. EXTENSION WHITELIST   │
       │              │    Is ext in whitelist?  │
       │              └──────┬───────────────────┘
       │                     │ Yes
       │                     ▼
       │              ┌──────────────────────────┐
       │              │ 4. EXTENSION BLACKLIST   │
       │              │    Is ext blacklisted?   │
       │              └──────┬───────────────────┘
       │                     │ No
       ▼                     ▼
    SHOW                  SHOW
```

---

## Empty Directory Handling

After filtering, empty directories are normally removed to reduce clutter. However, certain directories are preserved even when empty:

### Preserved Empty Directories

1. **Directories in ALWAYS_VISIBLE_FOLDERS**
   - Example: In vis mode, `scitex/vis/figures/` is kept even if empty

2. **Directories matching ALLOWED_DIRECTORIES**
   - Example: In vis mode, `scitex/vis/` itself is kept even if empty
   - This ensures the root allowed directory is always visible

### Why This Matters

- **User clarity**: Shows where files should be placed
- **Prevents confusion**: Users can see the expected directory structure
- **Facilitates uploads**: Drag-and-drop targets remain visible

**Example**: In vis mode, even if `scitex/vis/` has no files (or only `.gitkeep`), it will still be visible because it matches `ALLOWED_DIRECTORIES['vis']`.

### Special Case: `.gitkeep` Files

`.gitkeep` files are commonly used to keep empty directories in git repositories. Our system handles them specially:

**Server-side**:
- `.gitkeep` files are included in the file tree API response (not filtered out like other hidden files)
- This ensures directories containing only `.gitkeep` appear non-empty to the server

**Client-side**:
- `.gitkeep` files are filtered out by extension whitelisting (they don't match any allowed extensions)
- After filtering, directories containing only `.gitkeep` become empty
- Empty directories matching `ALLOWED_DIRECTORIES` are preserved (see above)

**Result**: Directories with only `.gitkeep` files appear in the tree, but the `.gitkeep` files themselves are hidden from view.

**Example Flow** (Vis Mode):
```
1. Server sends: scitex/vis/ → children: [.gitkeep]
2. Client filters: .gitkeep doesn't match [.csv, .png, ...] → removed
3. Directory check: scitex/vis/ is now empty
4. Preservation: scitex/vis/ matches ALLOWED_DIRECTORIES['vis'] → kept
5. User sees: scitex/vis/ (empty but visible)
```

---

## Default Focus Behavior

Each workspace mode automatically expands and focuses on a default directory when loaded:

- **Scholar**: `scitex/scholar/`
- **Vis**: `scitex/vis/`
- **Writer**: `scitex/writer/01_manuscript/`
- **Code**: `scripts/`
- **All**: (no default focus)

**Focus Memory**: The system remembers the last focused directory per mode in localStorage and restores it on subsequent visits.

---

## Mode-Specific Complete Rules

### Scholar Mode

- ✅ **Directory Whitelist**: `scitex/scholar/`
- ✅ **Directory Blacklist**: `node_modules`, `.git`, `__pycache__`, `.venv`, `build`
- ✅ **Extension Whitelist**: `.bib`
- ❌ **Extension Blacklist**: None

**Result**: Only `.bib` files within `scitex/scholar/` directory

---

### Vis Mode

- ✅ **Directory Whitelist**: `scitex/vis/`
- ✅ **Directory Blacklist**: `node_modules`, `.git`, `__pycache__`, `.venv`
- ✅ **Extension Whitelist**: `.csv`, `.tsv`, `.json`, `.png`, `.jpg`, `.jpeg`, `.pdf`, `.svg`
- ❌ **Extension Blacklist**: None

**Result**: Only data/image files within `scitex/vis/` directory

---

### Writer Mode

- ✅ **Directory Whitelist**: `scitex/writer/`
- ✅ **Directory Blacklist**: `node_modules`, `.git`, `__pycache__`, `.venv`, `build`
- ✅ **Extension Whitelist**: `.tex`, `.bib`, `.png`, `.jpg`, `.jpeg`, `.pdf`, `.svg`, `.eps`
- ❌ **Extension Blacklist**: None
- ✅ **Doctype-Responsive**: Can further restrict to `01_manuscript/`, `02_supplementary/`, or `03_revision/`

**Result**: Only document files within `scitex/writer/` directory (optionally filtered by doctype)

---

### Code Mode

- ✅ **Directory Whitelist**: None (all directories)
- ✅ **Directory Blacklist**: `.git`
- ✅ **Extension Whitelist**: `'all'` (all extensions)
- ❌ **Extension Blacklist**: None

**Result**: All files except `.git/` directory

---

## Checklist for Adding New Filtering Criteria

When adding a new filter type, follow this checklist:

- [ ] **Define the criterion**
  - [ ] What is it filtering? (directory/filename/extension/content)
  - [ ] Whitelist or blacklist approach?
  - [ ] Per-mode or global?

- [ ] **Add to ModeFilters.ts**
  - [ ] Create configuration constant
  - [ ] Add TypeScript types
  - [ ] Document with examples

- [ ] **Update TreeFilter.ts**
  - [ ] Import configuration from ModeFilters
  - [ ] Add logic to `isHidden()` or create new method
  - [ ] Maintain systematic order (1-5)

- [ ] **Test all modes**
  - [ ] Scholar mode
  - [ ] Vis mode
  - [ ] Writer mode
  - [ ] Code mode

- [ ] **Update documentation**
  - [ ] Add to FILTERING_SPEC.md
  - [ ] Update README.md
  - [ ] Add examples

---

## Configuration Files

| File | Purpose |
|------|---------|
| `ModeFilters.ts` | Central configuration for all filtering rules |
| `TreeFilter.ts` | Applies filtering logic to tree items |
| `FILTERING_SPEC.md` | This specification document |
| `README.md` | User-facing documentation with examples |
