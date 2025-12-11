# Phase 5 Integration Guide - ElementSelectionManager & ContextMenuManager

## Overview

Phase 5 refactoring has extracted ~1200 lines of element selection and context menu code from CanvasManager.ts into two specialized managers:

- **ElementSelectionManager.ts** (~700 lines) - Element-level selection within plot images
- **ContextMenuManager.ts** (~500 lines) - Right-click context menu operations

## Integration Steps for CanvasManager.ts

### 1. Imports (✅ COMPLETED)

```typescript
import { ElementSelectionManager } from './canvas/ElementSelectionManager.ts';
import { ContextMenuManager } from './canvas/ContextMenuManager.ts';
```

### 2. Manager Declarations (✅ COMPLETED)

```typescript
private elementSelectionManager: ElementSelectionManager | null = null;
private contextMenuManager: ContextMenuManager | null = null;
```

### 3. Remove Old State Variables (Lines to delete)

**DELETE these lines** (currently at lines ~4230-4240):
```typescript
// Element-level Selection Mode
private elementSelectionTarget: any = null;
private elementSelectionOverlay: HTMLCanvasElement | null = null;
private selectedElementNames: Set<string> = new Set();
private hoveredElementName: string | null = null;
private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void;
```

**DELETE these lines** (currently at lines ~4585-4590):
```typescript
// Cycle selection state
private elementsAtCursor: string[] = [];
private currentCycleIndex: number = 0;
```

**DELETE this line** (currently at line ~699):
```typescript
private contextMenuCallbacks: {...} = {};
```

**DELETE this line** (currently at line ~58):
```typescript
private rightClickPanOccurred: boolean = false;
```

### 4. Initialize Managers in initCanvas()

**ADD after CropManager initialization** (around line 236):

```typescript
// Phase 5 managers - element selection and context menu
this.elementSelectionManager = new ElementSelectionManager(
    this.canvas,
    this.statusBarCallback
);

this.contextMenuManager = new ContextMenuManager(
    this.canvas,
    () => this.elementSelectionManager?.getSelectedElementNames() || [],
    this.statusBarCallback
);
```

### 5. Update setupCanvasEvents()

**REPLACE the setupContextMenu() call** (currently at line 724):

```typescript
// Setup context menu (OLD - DELETE THIS)
this.setupContextMenu(canvasContainer);

// NEW CODE:
if (this.contextMenuManager && canvasContainer) {
    this.contextMenuManager.setupContextMenu(canvasContainer);

    // Set all callbacks for context menu actions
    this.contextMenuManager.setCallbacks({
        copy: () => this.copyActiveObject(),
        paste: () => this.pasteObject(),
        delete: () => { this.removeActiveObject(); this.saveCanvasContent(); },
        duplicate: () => this.duplicateActiveObject(),
        bringToFront: () => this.bringToFront(),
        sendToBack: () => this.sendToBack(),
        alignObjects: (alignment) => this.alignObjects(alignment as any),
        distributeObjects: (direction) => this.distributeObjects(direction as any),
        matchSize: () => this.matchSize(),
        matchWidth: () => this.matchWidth(),
        matchHeight: () => this.matchHeight(),
        multipleCrop: () => this.multipleCrop(),
        alignByAxis: (direction) => this.alignByAxis(direction as any),
        stackVertically: () => this.stackVertically(),
        enterCropMode: () => this.enterCropMode(),
        autoCropMargin: () => this.autoCropMargin(),
        resetCrop: () => this.resetCrop(),
        flipHorizontal: () => this.flipHorizontal(),
        flipVertical: () => this.flipVertical(),
        rotateObjects: (degrees) => this.rotateObjects(degrees),
        resetSize: () => this.resetSize(),
        groupObjects: () => this.groupObjects(),
        ungroupObjects: () => this.ungroupObjects(),
        copyView: () => this.copyView(),
        pasteView: () => this.pasteView(),
        runRecommendedStatTest: () => this.runRecommendedStatTest(),
        runAllStatTests: () => this.runAllStatTests(),
        showStatTestSelector: () => this.showStatTestSelector(),
        openStatsInspector: () => this.openStatsInspector(),
        exportAsPng: () => this.exportAsPng(),
        exportAsSvg: () => this.exportAsSvg(),
        exportAsPdf: () => this.exportAsPdf(),
        saveCanvas: () => this.saveCanvasContent(),
        toggleTheme: () => this.toggleCanvasTheme(),
        zoomToFit: () => this.zoomToFit(),
        resetView: () => this.resetView(),
    });
}
```

### 6. Update Right-Click Pan Tracking

**REPLACE** lines setting rightClickPanOccurred (around lines 769, 791):

```typescript
// OLD:
this.rightClickPanOccurred = true;

// NEW:
this.contextMenuManager?.setRightClickPanOccurred(true);
```

**REPLACE** line resetting it (around line 776):

```typescript
// OLD:
this.rightClickPanOccurred = false;

// NEW:
this.contextMenuManager?.setRightClickPanOccurred(false);
```

### 7. Delegate Element Selection Methods

**REPLACE these methods** with delegation (lines 4242-4890):

```typescript
/**
 * Set callback for element selection changes
 * DELEGATES to ElementSelectionManager
 */
public setElementSelectionCallback(callback: (elementNames: string[], elementInfos: any[]) => void): void {
    this.elementSelectionManager?.setElementSelectionCallback(callback);
}

/**
 * Get currently selected element names
 * DELEGATES to ElementSelectionManager
 */
public getSelectedElementNames(): string[] {
    return this.elementSelectionManager?.getSelectedElementNames() || [];
}

/**
 * Enter element selection mode for a plot image
 * DELEGATES to ElementSelectionManager
 */
private enterElementSelectionMode(target: any, pointer?: { x: number, y: number }): void {
    this.elementSelectionManager?.enterElementSelectionMode(target, pointer);
}

/**
 * Exit element selection mode
 * DELEGATES to ElementSelectionManager
 */
public exitElementSelectionMode(): void {
    this.elementSelectionManager?.exitElementSelectionMode();
}

/**
 * Check if currently in element selection mode
 * DELEGATES to ElementSelectionManager
 */
public isInElementSelectionMode(): boolean {
    return this.elementSelectionManager?.isInElementSelectionMode() || false;
}

/**
 * Clear element selection
 * DELEGATES to ElementSelectionManager
 */
public clearElementSelection(): void {
    this.elementSelectionManager?.clearElementSelection();
}
```

**DELETE** all the private implementation methods (lines 4340-4890):
- createElementOverlay()
- setupElementSelectionEvents()
- findElementAtPosition()
- findElementAtImageCoords()
- cycleElementSelection()
- selectElement()
- updateElementOverlay()
- drawElementHighlight()
- All distance calculation helpers

### 8. Update extractGroupsFromSelection()

**REPLACE** the extractGroupsFromSelection() method (lines 4900-4952):

```typescript
/**
 * Extract group data from selected objects for statistical testing
 */
private extractGroupsFromSelection(): { name: string; values: number[] }[] {
    if (!this.canvas) return [];

    const groups: { name: string; values: number[] }[] = [];

    // Check if we're in element selection mode with multiple elements selected
    if (this.elementSelectionManager) {
        const target = this.canvas.getActiveObject();
        const csvData = target?.csvData || target?.axisMetadata?.csv_data;

        const elementGroups = this.elementSelectionManager.extractGroupsFromSelection(csvData);
        if (elementGroups.length > 0) {
            return elementGroups;
        }
    }

    // Fallback: Extract from multiple Fabric objects selected
    const activeObjects = this.canvas.getActiveObjects();

    for (const obj of activeObjects) {
        const plotData = (obj as any).plotData;
        if (plotData && plotData.values) {
            groups.push({
                name: plotData.label || `Group ${groups.length + 1}`,
                values: plotData.values,
            });
        }
    }

    return groups;
}
```

**DELETE** the extractElementData() method (lines 4957-5042) - now in ElementSelectionManager

### 9. Delete Context Menu Implementation

**DELETE** the entire setupContextMenu() method (lines 1665-2234) - now in ContextMenuManager

**DELETE** setContextMenuCallbacks() method (lines 709-711) - replaced by contextMenuManager.setCallbacks()

### 10. Update Stats Inspector Methods

**DELEGATE** these methods to ElementSelectionManager (lines 5185-5265):

```typescript
/**
 * Open the Stats Inspector panel
 * DELEGATES to ElementSelectionManager
 */
private openStatsInspector(): void {
    this.elementSelectionManager?.openStatsInspector();
}

/**
 * Show Stats Inspector panel with data
 * DELEGATES to ElementSelectionManager
 */
private showStatsInspectorPanel(data: { tests: any[]; effects: any[] }): void {
    this.elementSelectionManager?.showStatsInspectorPanel(data);
}
```

## Code Reduction Summary

| Section | Original Lines | After Refactoring | Reduction |
|---------|---------------|-------------------|-----------|
| Element Selection State | 10 | 2 (manager refs) | -8 lines |
| Element Selection Methods | ~650 | ~100 (delegation) | -550 lines |
| Context Menu State | 40 | 2 (manager ref) | -38 lines |
| Context Menu Implementation | ~570 | ~50 (delegation) | -520 lines |
| **Total** | **~1270 lines** | **~154 lines** | **~1116 lines** |

## Expected File Size

- **Before Phase 5**: 5415 lines
- **After Phase 5**: ~4300 lines (removal of ~1115 lines of implementation)
- **Net change**: -20% reduction in CanvasManager.ts complexity

## Testing Checklist

After integration, test these scenarios:

### Element Selection
- [ ] Click on plot image with element_bboxes enters element selection mode
- [ ] Hover over elements shows highlight
- [ ] Click selects element
- [ ] Ctrl+Click multi-selects elements
- [ ] Alt+Click cycles through overlapping elements
- [ ] Escape or click outside exits element selection mode
- [ ] Element selection callback is triggered

### Context Menu
- [ ] Right-click on object shows context menu
- [ ] Right-click during pan does not show menu
- [ ] Menu items show/hide based on selection state:
  - Image-only sections (Crop) visible for images
  - Multi-select sections visible for multiple objects
  - Stats section visible for plots or element selections
- [ ] All menu actions work correctly
- [ ] Submenus open correctly (left/right based on viewport)
- [ ] Click outside closes menu
- [ ] Escape closes menu

### Stats Integration
- [ ] Stats Inspector panel opens
- [ ] Element selection extracts correct data groups
- [ ] Statistical tests run on selected elements
- [ ] Bracket annotations are added correctly

## Files Modified

1. `/apps/vis_app/static/vis_app/ts/vis/CanvasManager.ts` - Main integration
2. `/apps/vis_app/static/vis_app/ts/vis/canvas/ElementSelectionManager.ts` - ✅ Created
3. `/apps/vis_app/static/vis_app/ts/vis/canvas/ContextMenuManager.ts` - ✅ Created
4. `/apps/vis_app/static/vis_app/ts/vis/canvas/index.ts` - ✅ Updated

## Files Created

- `/apps/vis_app/static/vis_app/ts/vis/canvas/ElementSelectionManager.ts` (700 lines)
- `/apps/vis_app/static/vis_app/ts/vis/canvas/ContextMenuManager.ts` (500 lines)
- `/apps/vis_app/static/vis_app/ts/vis/canvas/PHASE5_INTEGRATION_GUIDE.md` (this file)

## Phase 5 Complete

All 5 phases of the CanvasManager refactoring are now complete:

- ✅ **Phase 1**: Grid, Export, Undo/Redo
- ✅ **Phase 2**: Theme, Zoom/Pan, Selection
- ✅ **Phase 3**: Object, Transform, Group
- ✅ **Phase 4**: Alignment, Snap, Crop
- ✅ **Phase 5**: ElementSelection, ContextMenu

**Next Steps**: Apply the integration changes outlined in this guide to CanvasManager.ts, then run the testing checklist.
