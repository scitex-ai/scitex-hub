<!-- ---
!-- Timestamp: 2025-11-29 00:53:48
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/REFACTORING/05_TYPESCRIPT_HIGH.md
!-- --- -->

# Task 05: Refactor High-Priority TypeScript Files

## Objective
Split large active TypeScript files into smaller, focused modules.

## Target Files (Active, not backups)

| File                                                                   | Lines | Priority |
|------------------------------------------------------------------------|-------|----------|
| apps/writer_app/static/writer_app/ts/modules/pdf-preview.ts            | 617   | HIGH     |
| apps/public_app/static/public_app/ts/tools/plot-viewer.ts              | 593   | HIGH     |
| apps/project_app/static/project_app/ts/repository/admin_maintenance.ts | 592   | HIGH     |
| apps/vis_app/static/vis_app/ts/vis-editor.ts                         | 546   | MEDIUM   |
| apps/writer_app/static/writer_app/ts/utils/section-dropdown.ts         | 539   | MEDIUM   |
| static/shared/ts/collaboration/writer-collaboration.ts                 | 534   | MEDIUM   |
| apps/writer_app/static/writer_app/ts/modules/editor-controls.ts        | 524   | MEDIUM   |
| apps/writer_app/static/writer_app/ts/editor/collaborative-editor-manager.ts | 523 | MEDIUM |
| apps/writer_app/static/writer_app/ts/editor/preview-panel-manager.ts   | 515   | MEDIUM   |

---

## Task 5.1: Refactor pdf-preview.ts (617 lines)

### Target Structure
```
apps/writer_app/static/writer_app/ts/modules/pdf-preview/
├── index.ts              # Main export
├── PDFPreviewManager.ts  # Main class
├── viewer.ts             # PDF viewing logic
├── navigation.ts         # Page navigation
├── zoom.ts               # Zoom controls
└── events.ts             # Event handlers
```

### Steps
1. Create directory `pdf-preview/`
2. Extract viewer logic to `viewer.ts`
3. Extract navigation to `navigation.ts`
4. Extract zoom controls to `zoom.ts`
5. Keep main class in `PDFPreviewManager.ts`
6. Create `index.ts` with re-exports
7. Update imports in templates

### Verification
```bash
npx tsc --noEmit
# Check browser console for errors
```

---

## Task 5.2: Refactor plot-viewer.ts (593 lines)

### Target Structure
```
apps/public_app/static/public_app/ts/tools/plot-viewer/
├── index.ts
├── PlotViewer.ts        # Main class
├── renderers.ts         # Plot rendering
├── controls.ts          # UI controls
└── export.ts            # Export functionality
```

---

## Task 5.3: Refactor admin_maintenance.ts (592 lines)

### Target Structure
```
apps/project_app/static/project_app/ts/repository/admin/
├── index.ts
├── maintenance.ts       # Main maintenance functions
├── cleanup.ts           # Cleanup operations
├── backup.ts            # Backup operations
└── ui.ts                # UI handlers
```

---

## Task 5.4: Refactor vis-editor.ts (546 lines)

### Target Structure
```
apps/vis_app/static/vis_app/ts/vis/
├── index.ts
├── VisEditor.ts       # Main class
├── graph.ts             # Graph operations
├── layout.ts            # Layout algorithms
├── interactions.ts      # Mouse/keyboard
└── export.ts            # Export to image
```

---

## Task 5.5: Refactor section-dropdown.ts (539 lines)

### Target Structure
```
apps/writer_app/static/writer_app/ts/utils/section-dropdown/
├── index.ts
├── SectionDropdown.ts   # Main class
├── navigation.ts        # Section navigation
├── rendering.ts         # Dropdown rendering
└── events.ts            # Event handlers
```

---

## General Pattern for TS Refactoring

1. **Analyze**: List classes/functions with `grep -E "^export |^class |^function "`
2. **Plan**: Group by responsibility
3. **Create**: Directory + files
4. **Extract**: Move code preserving exports
5. **Index**: Create barrel file (index.ts)
6. **Update**: Fix imports in consumers
7. **Verify**: `npx tsc --noEmit`
8. **Commit**: One logical chunk per commit

## Verification
```bash
# TypeScript compilation
npx tsc --noEmit

# File size check
./scripts/check_file_sizes.sh --verbose | grep "TypeScript"
```

## Completion Criteria
- All files under 256 lines
- No TypeScript errors
- Browser console clean

