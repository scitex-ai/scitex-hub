# SciTeX Module Independence Specification

## Design Philosophy

**Core Principles:**
- **Independence > Convenience** - Modules should work independently
- **Explicit > Implicit** - Cross-module references must be explicit (symlinks)
- **Clear Structure** - Obvious places for files, easy for local users

## Directory Structure

```
scitex/
├── scholar/
│   └── bib_files/              ← Only .bib files
│       └── references.bib
│
├── code/
│   └── (free structure)        ← No restrictions for developers
│
├── vis/
│   ├── data/                   ← Input data (.csv, .npy, .json)
│   ├── figures/                ← Output figures (.png, .pdf, .svg)
│   └── exports/                ← 🔗 Share with other modules
│       ├── plot_1.png
│       └── analysis.csv
│
└── writer/
    ├── 01_manuscript/
    │   ├── main.tex
    │   └── figures/            ← 🔗 symlinks to vis/exports/
    │       ├── plot_1.png → ../../vis/exports/plot_1.png
    │       └── analysis.csv → ../../vis/exports/analysis.csv
    │
    ├── 02_supplementary/
    │   └── figures/            ← 🔗 symlinks to vis/exports/
    │
    └── shared/
        └── references.bib      ← 🔗 symlink to scholar/bib_files/references.bib
```

## Module Reference Rules

### Scholar Module (`scitex/scholar/`)

**Purpose:** Bibliography management

**Input:**
- `.bib` files uploaded by user

**Output:**
- `bib_files/` directory for organized bibliography

**Can Reference:**
- Nothing (independent)

**Can Be Referenced By:**
- `writer/` via symlink to `scholar/bib_files/references.bib`

**Restrictions:**
- Only `.bib` files allowed
- No subdirectories

### Vis Module (`scitex/vis/`)

**Purpose:** Data visualization and analysis

**Input:**
- `data/` - Raw data files (`.csv`, `.tsv`, `.json`, `.npy`, `.npz`)
- `panels/` - Panel configurations
- `ai/` - AI-generated visualizations

**Output:**
- `figures/` - Generated visualizations (`.png`, `.pdf`, `.svg`)
- `exports/` - Files ready for other modules to reference

**Can Reference:**
- Nothing (independent)

**Can Be Referenced By:**
- `writer/` via symlinks to `vis/exports/*`

**Restrictions:**
- Only data and image files
- No direct access to other modules

### Writer Module (`scitex/writer/`)

**Purpose:** Document writing (manuscript, supplementary, revision)

**Input:**
- References via symlink: `shared/references.bib → scholar/bib_files/references.bib`
- Figures via symlinks: `01_manuscript/figures/* → vis/exports/*`

**Output:**
- `.tex` files
- Compiled PDFs

**Can Reference:**
- `scholar/bib_files/` via symlink
- `vis/exports/` via symlink

**Can Be Referenced By:**
- Nothing

**Restrictions:**
- Only `.tex`, `.bib`, and image files
- Must use symlinks for cross-module references

### Code Module (`scitex/code/`)

**Purpose:** Full development environment

**Input:**
- Anything

**Output:**
- Anything

**Can Reference:**
- Everything (no restrictions)

**Can Be Referenced By:**
- Nothing (development only)

**Restrictions:**
- None - this is the developer's workspace

## Cross-Module Reference Mechanism

### Symlink-Based Sharing

**Why Symlinks?**
1. ✅ **Explicit** - Clear what is shared
2. ✅ **Trackable** - Git can track symlinks
3. ✅ **Local-friendly** - Works on local filesystems
4. ✅ **Independence** - Modules remain independent
5. ✅ **No duplication** - Single source of truth

**IMPORTANT: All symlinks MUST be relative paths**
- ✅ Portable across different systems
- ✅ Works on Windows, Mac, Linux
- ✅ No absolute path dependencies
- ✅ Git-friendly

**Allowed Symlink Patterns:**
```bash
# ✅ GOOD - Writer references Scholar bibliography (relative path)
writer/shared/references.bib → ../../scholar/bib_files/references.bib

# ✅ GOOD - Writer references Vis figures (relative path)
writer/01_manuscript/figures/plot_1.png → ../../../vis/exports/plot_1.png

# ❌ BAD - Absolute path
writer/shared/references.bib → /home/user/project/scitex/scholar/bib_files/references.bib

# ❌ BAD - Direct access without symlink
writer/01_manuscript/main.tex directly accessing ../vis/figures/plot_1.png

# ❌ BAD - Scholar referencing other modules
scholar/bib_files/data.csv → ../../vis/exports/data.csv
```

### Symlink Display in File Tree

Symlinks should be clearly visible in the file tree with the target path:

```
writer/
├── shared/
│   └── references.bib → ../../scholar/bib_files/references.bib
├── 01_manuscript/
│   ├── main.tex
│   └── figures/
│       ├── plot_1.png → ../../../vis/exports/plot_1.png
│       └── analysis.csv → ../../../vis/exports/analysis.csv
└── 02_supplementary/
    └── figures/
        └── supp_fig_1.png → ../../../vis/exports/supp_fig_1.png
```

**Display Format:**
- **Filename** + **→** + **Relative target path**
- Example: `plot_1.png → ../../../vis/exports/plot_1.png`
- Use muted color for the arrow and target path
- Add symlink icon: 🔗

## UI Implementation: Ctrl+Drag Symlink Creation

### User Interaction

**Normal Drag:**
- **Action:** Move or copy file
- **Visual:** "📄 Move here"
- **Cursor:** Default drag cursor

**Ctrl+Drag:**
- **Action:** Create symlink
- **Visual:** "🔗 Link here"
- **Cursor:** Link cursor with indicator

### Implementation Pseudocode

```typescript
// FileTree component
const handleDragStart = (e: DragEvent, sourcePath: string) => {
  e.dataTransfer.setData('path', sourcePath);
  e.dataTransfer.setData('type', getFileType(sourcePath));

  // Track Ctrl key state
  window.addEventListener('keydown', handleCtrlKeyDown);
  window.addEventListener('keyup', handleCtrlKeyUp);
};

const handleDrop = (e: DragEvent, targetPath: string) => {
  e.preventDefault();

  const sourcePath = e.dataTransfer.getData('path');
  const targetFullPath = joinPath(targetPath, basename(sourcePath));

  if (e.ctrlKey) {
    // Create symlink with RELATIVE path
    const relativePath = calculateRelativePath(targetPath, sourcePath);
    createSymlink(relativePath, targetFullPath);
    showToast(`🔗 Linked: ${basename(sourcePath)} → ${relativePath}`);
  } else {
    // Normal move/copy
    moveFile(sourcePath, targetFullPath);
    showToast(`📄 Moved: ${basename(sourcePath)}`);
  }

  // Clean up event listeners
  window.removeEventListener('keydown', handleCtrlKeyDown);
  window.removeEventListener('keyup', handleCtrlKeyUp);
};

const calculateRelativePath = (from: string, to: string): string => {
  // Convert absolute paths to relative
  // e.g., from: writer/01_manuscript/figures
  //       to: vis/exports/plot_1.png
  //       result: ../../../vis/exports/plot_1.png
  const fromParts = from.split('/');
  const toParts = to.split('/');

  // Find common ancestor
  let i = 0;
  while (i < fromParts.length && i < toParts.length && fromParts[i] === toParts[i]) {
    i++;
  }

  // Go up from 'from' directory
  const upLevels = fromParts.length - i;
  const upPath = '../'.repeat(upLevels);

  // Go down to 'to' file
  const downPath = toParts.slice(i).join('/');

  return upPath + downPath;
};

const DragOverlay = ({ isCtrlPressed, targetPath }: Props) => {
  // Show different visual feedback
  return (
    <div className={`drag-overlay ${isCtrlPressed ? 'link-mode' : 'move-mode'}`}>
      <div className="drag-icon">
        {isCtrlPressed ? '🔗' : '📄'}
      </div>
      <div className="drag-text">
        {isCtrlPressed ? 'Link here' : 'Move here'}
      </div>
    </div>
  );
};
```

### Validation Rules

Before creating symlink, validate:

1. **Source exists** - File/directory must exist
2. **Target directory exists** - Parent directory must exist
3. **No name collision** - Target path must not exist
4. **Allowed pattern** - Must match module reference rules:
   - ✅ `vis/exports/*` → `writer/*/figures/*`
   - ✅ `scholar/bib_files/*` → `writer/shared/*`
   - ❌ Any other cross-module symlink

```typescript
const isSymlinkAllowed = (source: string, target: string): boolean => {
  // Writer can link from Vis exports
  if (source.startsWith('scitex/vis/exports/') &&
      target.startsWith('scitex/writer/') &&
      target.includes('/figures/')) {
    return true;
  }

  // Writer can link from Scholar bib_files
  if (source.startsWith('scitex/scholar/bib_files/') &&
      target.startsWith('scitex/writer/') &&
      target.includes('/shared/')) {
    return true;
  }

  // Within same module is always allowed
  if (getModule(source) === getModule(target)) {
    return true;
  }

  return false;
};
```

## Benefits

### For Cloud Users
- Clear visual indication of shared resources
- Drag-and-drop symlink creation
- No confusion about file locations

### For Local Users
```bash
# Clone the template
git clone https://github.com/user/scitex-template

# Structure is immediately clear
ls scitex/
# scholar/  code/  vis/  writer/

# Know exactly where to put files
cp my_data.csv scitex/vis/data/

# Symlinks work locally
cd scitex/writer/01_manuscript
ls -la figures/
# plot_1.png -> ../../vis/exports/plot_1.png
```

### For Git/Version Control
```bash
# Symlinks are tracked by git
git status
# modified: scitex/writer/01_manuscript/figures/plot_1.png (symlink)

# Easy to see what's shared
git ls-files -s scitex/writer/01_manuscript/figures/
# 120000 ... plot_1.png  (symlink)
```

## Migration Path

### Existing Projects

1. **Create exports directories:**
   ```bash
   mkdir -p scitex/vis/exports
   mkdir -p scitex/scholar/bib_files
   ```

2. **Move shared files:**
   ```bash
   mv scitex/vis/figures/plot_1.png scitex/vis/exports/
   ```

3. **Create symlinks:**
   ```bash
   cd scitex/writer/01_manuscript/figures
   ln -s ../../../vis/exports/plot_1.png .
   ```

### New Projects

Templates will include the structure by default:
```
scitex-template/
└── scitex/
    ├── scholar/
    │   └── bib_files/.gitkeep
    ├── code/
    │   └── .gitkeep
    ├── vis/
    │   ├── data/.gitkeep
    │   ├── figures/.gitkeep
    │   └── exports/.gitkeep
    └── writer/
        ├── 01_manuscript/figures/.gitkeep
        ├── 02_supplementary/figures/.gitkeep
        └── shared/.gitkeep
```

## Implementation Checklist

- [ ] Add `exports/` directory to vis module filtering
- [ ] Add `bib_files/` directory to scholar module filtering
- [ ] Implement Ctrl+Drag symlink UI in file tree
- [ ] Add visual feedback for drag operations
- [ ] Implement symlink validation rules
- [ ] Add API endpoint for symlink creation
- [ ] Update project templates with new structure
- [ ] Document symlink workflow in user guide
- [ ] Add symlink indicator icons in file tree (🔗)
- [ ] Test symlink behavior on Windows/Mac/Linux

---

**Design Rationale:** "Constraints become guardrails" - By limiting cross-module access to explicit symlinks, we maintain module independence while allowing controlled sharing. This makes the system easier to understand and more maintainable.
