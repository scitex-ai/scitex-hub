# Data Table Module - Migration Guide

## Summary

The data-table component has been copied from figrecipe_app to create a shared module at:
- TypeScript: `/static/shared/ts/components/data-table/`
- CSS: `/static/shared/css/components/data-table/`

## What Was Done

### 1. TypeScript Module Structure

All TypeScript files have been copied from `apps/figrecipe_app/static/figrecipe_app/ts/vis/data-table/` to the shared location:

- `DataTableManager.ts` - Main orchestrator class
- `TableData.ts` - Data management, CSV import
- `TableRendering.ts` - Rendering & virtual scrolling
- `TableSelection.ts` - Cell/column/row selection
- `TableEditing.ts` - Cell editing & keyboard navigation
- `TableClipboard.ts` - Copy/paste operations
- `TableFillHandle.ts` - Fill handle drag functionality
- `TableColumnRow.ts` - Column/row operations & resizing
- `types.ts` - Type definitions and constants
- `index.ts` - Module exports

### 2. Import Path Updates

All imports have been updated to use relative paths within the module:
- Changed from `'../types.ts'` to `'./types.ts'`
- Changed from `'./data-table/TableXxx.ts'` to `'./TableXxx.ts'`

### 3. CSS Files

Created merged CSS file: `/static/shared/css/components/data-table/data-table.css`

This file combines:
- `data-table.css` - Basic table styling and tabs
- `editable-table.css` - Editable table features

### 4. CSS Variables Used

The module uses these CSS variables (apps should define them):

```css
/* Background colors */
--vis-bg-primary
--vis-bg-secondary
--vis-bg-hover

/* Border colors */
--workspace-border-default
--workspace-border-muted

/* Text colors */
--text-primary
--text-muted

/* Status colors */
--status-success
--status-success-bg
--status-error
--status-error-bg
--status-warning
```

## Next Steps (NOT DONE YET)

### Step 1: Update figrecipe_app to use shared module

Modify `apps/figrecipe_app/static/figrecipe_app/ts/` to import from the shared location:

```typescript
// OLD
import { DataTableManager } from './vis/DataTableManager.ts';

// NEW
import { DataTableManager } from '/static/shared/js/components/data-table/DataTableManager.ts';
```

### Step 2: Update CSS imports in figrecipe_app

```html
<!-- OLD -->
<link rel="stylesheet" href="/static/figrecipe_app/css/vis/data-table.css">
<link rel="stylesheet" href="/static/figrecipe_app/css/vis/editable-table.css">

<!-- NEW -->
<link rel="stylesheet" href="/static/shared/css/components/data-table/data-table.css">
```

### Step 3: Compile TypeScript

The shared module needs to be compiled:

```bash
make env=dev compile-ts
```

### Step 4: Test figrecipe_app

Ensure figrecipe_app still works with the shared module.

### Step 5: Migrate console_app

Update console_app to use the shared module instead of its own implementation.

### Step 6: Clean up old files

After successful migration and testing, remove the old figrecipe_app-specific data-table files.

## Files Created

### TypeScript (Source)
- `/static/shared/ts/components/data-table/DataTableManager.ts`
- `/static/shared/ts/components/data-table/TableClipboard.ts`
- `/static/shared/ts/components/data-table/TableColumnRow.ts`
- `/static/shared/ts/components/data-table/TableData.ts`
- `/static/shared/ts/components/data-table/TableEditing.ts`
- `/static/shared/ts/components/data-table/TableFillHandle.ts`
- `/static/shared/ts/components/data-table/TableRendering.ts`
- `/static/shared/ts/components/data-table/TableSelection.ts`
- `/static/shared/ts/components/data-table/types.ts`
- `/static/shared/ts/components/data-table/index.ts`

### Documentation
- `/static/shared/ts/components/data-table/README.md`
- `/static/shared/ts/components/data-table/MIGRATION.md` (this file)

### CSS
- `/static/shared/css/components/data-table/data-table.css` (merged complete version)

## Notes

- The figrecipe_app files have NOT been modified yet
- The shared module is self-contained and ready to use
- CSS uses `--vis-bg-*` variables which should map to app-specific variables
- All imports use `.ts` extensions for proper ES module support
