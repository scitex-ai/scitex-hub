# CanvasManager Refactoring Plan

## Overview
Split 5,829-line CanvasManager.ts into 16 focused modules (each <400 lines).
Target: Maintainable, testable TypeScript with clear separation of concerns.

## Current State Analysis

### File Statistics
- **Total Lines**: 5,829
- **Total Methods**: 100+ (public + private)
- **Avg Lines/Method**: ~58
- **Main Responsibilities**: 15+ distinct feature areas

### Key Dependencies
- **External**: Fabric.js (canvas manipulation), DOM manipulation
- **Internal**: CANVAS_CONSTANTS from types.ts
- **State**: 40+ private fields tracking zoom, pan, undo/redo, snap, crop, themes, etc.

---

## Module Breakdown

### 1. **CanvasManager.ts** (Core Orchestrator)
**Lines**: ~350 (reduced from 5,829)
**Responsibility**: Initialize, coordinate modules, expose public API

**Keeps**:
- Constructor with callbacks
- `initCanvas()` - delegates to modules
- Public getters/setters for zoom/pan
- Module instances as properties
- Event delegation setup

**State Variables** (delegation pointers only):
```typescript
private canvas: any | null
private gridManager: GridManager
private themeManager: ThemeManager
private undoRedoManager: UndoRedoManager
private zoomPanManager: ZoomPanManager
private objectManager: ObjectManager
private selectionManager: SelectionManager
private alignmentManager: AlignmentManager
private cropManager: CropManager
private transformManager: TransformManager
private groupManager: GroupManager
private snapManager: SnapManager
private elementSelectionManager: ElementSelectionManager
private exportManager: ExportManager
private contextMenuManager: ContextMenuManager
```

**Public API** (delegates to modules):
```typescript
// Grid
public toggleGrid(): void
public drawGrid(isDark: boolean): void
public clearGrid(): void

// Theme
public updateCanvasTheme(isDark: boolean): void
public toggleCanvasTheme(): void

// Undo/Redo
public saveUndoState(): void
public undo(): void
public redo(): void

// Zoom/Pan
public zoomIn(): void
public zoomOut(): void
public zoomToFit(): void
public resetView(): void
public getCanvasZoomLevel(): number
public getCanvasPanOffset(): { x: number, y: number }
public setCanvasZoomLevel(zoom: number): void
public setCanvasPanOffset(x: number, y: number): void

// Objects
public addImage(src: string, options: any): Promise<any>
public addSvg(svgString: string, options: any): Promise<any>
public clearCanvas(): void
public removeActiveObject(): void

// Selection
public getActiveObject(): any
public selectAll(): void
public copyActiveObject(): void
public pasteObject(): void
public duplicateActiveObject(): void

// Alignment
public alignObjects(alignment: string): void
public distributeObjects(direction: string): void
public alignByAxis(direction: string): void
public stackVertically(): void

// Crop
public enterCropMode(): void
public exitCropMode(): void
public applyCrop(): void
public resetCrop(): void
public multipleCrop(): void
public copyView(): void
public pasteView(): void

// Transform
public matchSize(): void
public matchWidth(): void
public matchHeight(): void
public resetSize(): void
public flipHorizontal(): void
public flipVertical(): void
public rotateObjects(degrees: number): void

// Group
public groupObjects(): void
public ungroupObjects(): void
public enterGroupEditMode(group: any): void
public exitGroupEditMode(): void

// Snap
public toggleSnap(): void
public isSnapEnabled(): boolean

// Element Selection
public enterElementSelectionMode(target: any, pointer: any): void
public exitElementSelectionMode(): void
public isInElementSelectionMode(): boolean
public clearElementSelection(): void

// Export
public exportAsPng(): void
public exportAsSvg(): void
public exportAsPdf(): void

// Content Persistence
public saveCanvasContent(): void
public restoreCanvasContent(): Promise<any[]>
public restoreViewState(): void
```

---

### 2. **canvas/GridManager.ts**
**Lines**: ~150
**Responsibility**: Grid rendering and visibility

**State Variables**:
```typescript
private canvas: any
private gridEnabled: boolean = true
```

**Methods**:
- `constructor(canvas: any)`
- `drawGrid(isDark: boolean): void` - Use static SVG files
- `clearGrid(): void` - Remove background image
- `toggleGrid(): void` - Toggle visibility
- `isGridEnabled(): boolean` - Getter

**Dependencies**:
- Canvas instance (injected)
- Static SVG files: `/static/vis_app/img/vis/grid-dark.svg`, `grid-light.svg`
- Status callback (optional, passed from main)

---

### 3. **canvas/ThemeManager.ts**
**Lines**: ~300
**Responsibility**: Theme switching, dark mode image processing

**State Variables**:
```typescript
private canvas: any
private isDarkMode: boolean = false
private originalImageSources: Map<any, string> = new Map()
```

**Methods**:
- `constructor(canvas: any, isDarkMode: boolean)`
- `updateCanvasTheme(isDark: boolean): void`
- `toggleTheme(): void`
- `processImageForDarkMode(img: HTMLImageElement): string` - Pixel manipulation
- `updateImageForTheme(fabricImg: any): void`
- `reprocessAllImagesForTheme(): void`
- `processSvgGroupForDarkMode(group: any): void`
- `restoreSvgGroupColors(group: any): void`
- `reprocessAllSvgGroupsForTheme(): void`
- `isDark(): boolean` - Getter

**Dependencies**:
- Canvas instance
- GridManager (to redraw grid in new theme)

---

### 4. **canvas/UndoRedoManager.ts**
**Lines**: ~120
**Responsibility**: Undo/redo stack management

**State Variables**:
```typescript
private canvas: any
private undoStack: string[] = []
private redoStack: string[] = []
private maxUndoSteps: number = 50
private isUndoRedoing: boolean = false
```

**Methods**:
- `constructor(canvas: any, maxSteps?: number)`
- `saveUndoState(): void`
- `undo(): void`
- `redo(): void`
- `canUndo(): boolean`
- `canRedo(): boolean`
- `clearHistory(): void`

**Dependencies**:
- Canvas instance
- Status callback (optional)

---

### 5. **canvas/ZoomPanManager.ts**
**Lines**: ~400
**Responsibility**: Zoom, pan, view state persistence

**State Variables**:
```typescript
private canvas: any
private canvasZoomLevel: number = 0.22
private canvasPanOffset: { x: number, y: number } = { x: 0, y: 0 }
private canvasIsPanning: boolean = false
private canvasIsZoomDragging: boolean = false
private canvasPanStartPoint: { x: number, y: number } | null = null
private canvasZoomDragStartY: number = 0
private canvasZoomDragStartLevel: number = 1
private canvasWheelThrottleFrame: number | null = null
private canvasAccumulatedZoomDelta: number = 0
private canvasLastZoomMousePos: { x: number, y: number } = { x: 0, y: 0 }
private canvasAccumulatedPanDelta: { x: number, y: number } = { x: 0, y: 0 }
private canvasDragThrottleFrame: number | null = null
private pendingDragUpdate: boolean = false
private panThrottleFrame: number | null = null
private pendingPanUpdate: { x: number, y: number } | null = null
private saveViewStateTimer: ReturnType<typeof setTimeout> | null = null
```

**Methods**:
- `constructor(canvas: any, rulersCallback?: () => void, statusCallback?: (msg: string) => void)`
- `setupEvents(container: HTMLElement): void` - Wheel, mouse events
- `zoomIn(): void`
- `zoomOut(): void`
- `zoomToFit(): void`
- `resetView(): void`
- `applyZoom(): void` - Private
- `updateCanvasTransform(): void`
- `saveViewState(): void` - Debounced localStorage
- `restoreViewState(): void`
- `getZoomLevel(): number`
- `getPanOffset(): { x: number, y: number }`
- `setZoomLevel(zoom: number): void`
- `setPanOffset(x: number, y: number): void`
- `updateCanvasZoomDisplay(): void` - Private

**Dependencies**:
- Canvas instance
- Rulers transform callback (optional, for coordinated zoom)
- Status callback (optional)
- CANVAS_CONSTANTS

---

### 6. **canvas/ObjectManager.ts**
**Lines**: ~350
**Responsibility**: Add/remove objects, content persistence

**State Variables**:
```typescript
private canvas: any
private saveContentDebounceTimer: ReturnType<typeof setTimeout> | null = null
```

**Methods**:
- `constructor(canvas: any, themeManager: ThemeManager)`
- `addImage(src: string, options: any): Promise<any>`
- `addImageFromBase64(base64: string, options: any): Promise<any>`
- `addSvg(svgString: string, options: any): Promise<any>`
- `addSvgFromUrl(url: string, options: any): Promise<any>`
- `clearCanvas(): void`
- `removeActiveObject(): void`
- `saveCanvasContent(): void` - Debounced
- `saveCanvasContentImmediate(): void` - Private
- `restoreCanvasContent(): Promise<any[]>`
- `serializeWithPrecision(obj: any): string` - Private
- `parseWithPrecision(jsonString: string): any` - Private
- `fixZeroScalePathsInJson(json: any): void` - Private

**Dependencies**:
- Canvas instance
- ThemeManager (for dark mode processing)
- UndoRedoManager (save undo state before add/remove)
- CANVAS_CONSTANTS

---

### 7. **canvas/SelectionManager.ts**
**Lines**: ~200
**Responsibility**: Object selection, copy/paste

**State Variables**:
```typescript
private canvas: any
private clipboard: any = null
private selectionCallback?: (obj: any | null) => void
```

**Methods**:
- `constructor(canvas: any)`
- `setSelectionCallback(callback: (obj: any | null) => void): void`
- `getActiveObject(): any`
- `selectAll(): void`
- `copyActiveObject(): void`
- `pasteObject(): void`
- `duplicateActiveObject(): void`
- `clearSelection(): void`

**Dependencies**:
- Canvas instance
- UndoRedoManager (save state before paste/duplicate)

---

### 8. **canvas/AlignmentManager.ts**
**Lines**: ~350
**Responsibility**: Alignment, distribution, axis-based alignment

**State Variables**:
```typescript
private canvas: any
private columnCount: number = 0
private columnGuidePositions: number[] = []
private debugLines: any[] = [] // For axis debug visualization
```

**Methods**:
- `constructor(canvas: any, statusCallback?: (msg: string) => void)`
- `alignObjects(alignment: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v'): void`
- `distributeObjects(direction: 'horizontal' | 'vertical'): void`
- `alignByAxis(direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B'): void` - Axis metadata-based
- `stackVertically(): void`
- `showAxisDebugLines(objects?: any[]): void`
- `clearAxisDebugLines(): void`
- `setColumnGuides(count: number): void`
- `clearColumnGuides(): void`

**Dependencies**:
- Canvas instance
- Status callback (optional)

---

### 9. **canvas/CropManager.ts**
**Lines**: ~400
**Responsibility**: Image cropping (manual, auto-margin, multiple)

**State Variables**:
```typescript
private canvas: any
private cropMode: boolean = false
private cropTarget: any = null
private cropOverlay: HTMLDivElement | null = null
private cropOriginalBound: any = null
private viewClipboard: {
    cropX?: number;
    cropY?: number;
    width?: number;
    height?: number;
    scaleX?: number;
    scaleY?: number;
} | null = null
```

**Methods**:
- `constructor(canvas: any, statusCallback?: (msg: string) => void)`
- `enterCropMode(): void`
- `exitCropMode(): void`
- `applyCrop(): void` - Private
- `resetCrop(): void`
- `multipleCrop(): void` - Apply to multiple selected images
- `createCropOverlay(target: any): void` - Private
- `updateCropOverlay(rect: any, originalBound: any, scaleX: number, scaleY: number): void` - Private
- `getCropCursor(pos: string): string` - Private
- `positionCropHandle(handle: HTMLDivElement, pos: string, width: number, height: number): void` - Private
- `positionCropHandleInOverlay(handle: HTMLDivElement, pos: string, cropX: number, cropY: number, width: number, height: number): void` - Private
- `setupCropHandleDrag(handle: HTMLDivElement, pos: string, target: any, originalBound: any, scaleX: number, scaleY: number): void` - Private
- `setupCropKeyboardListeners(): void` - Private
- `copyView(): void` - Copy crop/scale
- `pasteView(): void` - Paste crop/scale
- `isInCropMode(): boolean`

**Dependencies**:
- Canvas instance
- Status callback (optional)
- UndoRedoManager (save state before crop)

---

### 10. **canvas/TransformManager.ts**
**Lines**: ~280
**Responsibility**: Size matching, flipping, rotation

**State Variables**:
```typescript
private canvas: any
private onObjectResizedCallback?: (obj: any, newWidth: number, newHeight: number) => void
```

**Methods**:
- `constructor(canvas: any, statusCallback?: (msg: string) => void)`
- `setObjectResizedCallback(callback: (obj: any, newWidth: number, newHeight: number) => void): void`
- `matchSize(): void`
- `matchWidth(): void`
- `matchHeight(): void`
- `resetSize(): void`
- `flipHorizontal(): void`
- `flipVertical(): void`
- `rotateObjects(degrees: number): void`
- `nudgeObjects(direction: 'up' | 'down' | 'left' | 'right', resize: boolean): void`

**Dependencies**:
- Canvas instance
- Status callback (optional)
- UndoRedoManager (save state before transform)

---

### 11. **canvas/GroupManager.ts**
**Lines**: ~180
**Responsibility**: Grouping, ungrouping, group edit mode

**State Variables**:
```typescript
private canvas: any
private groupEditMode: boolean = false
private editingGroup: any = null
private editingGroupOriginalObjects: any[] = []
```

**Methods**:
- `constructor(canvas: any, statusCallback?: (msg: string) => void)`
- `groupObjects(): void`
- `ungroupObjects(): void`
- `enterGroupEditMode(group: any): void`
- `exitGroupEditMode(): void`
- `isInGroupEditMode(): boolean`

**Dependencies**:
- Canvas instance
- Status callback (optional)
- UndoRedoManager (save state before group/ungroup)

---

### 12. **canvas/SnapManager.ts**
**Lines**: ~350
**Responsibility**: Smart snapping, alignment guidelines

**State Variables**:
```typescript
private canvas: any
private snapEnabled: boolean = true
private snapThreshold: number = 10
private guidelineOverlay: HTMLDivElement | null = null
private objectMovingThrottleFrame: number | null = null
private pendingMovingTarget: any = null
private lastSnapX: number | null = null
private lastSnapY: number | null = null
private altKeyActive: boolean = false
```

**Methods**:
- `constructor(canvas: any)`
- `setupEvents(): void` - object:moving, mouse:up listeners
- `setupAltKeyTracking(): void`
- `toggleSnap(): void`
- `isSnapEnabled(): boolean`
- `handleObjectSnap(target: any): void` - Private, throttled
- `snapToAxisPositions(target: any, axisObjects: any[]): void` - Private
- `drawGuidelinesCSS(lines: any[]): void` - Private
- `clearAlignmentLines(): void`
- `initGuidelineOverlay(): void` - Private

**Dependencies**:
- Canvas instance

---

### 13. **canvas/ElementSelectionManager.ts**
**Lines**: ~600 (most complex module)
**Responsibility**: Sub-element selection within plots, stats extraction

**State Variables**:
```typescript
private canvas: any
private elementSelectionMode: boolean = false
private elementSelectionTarget: any = null
private elementOverlay: HTMLDivElement | null = null
private selectedElements: Set<string> = new Set()
private highlightedElements: Set<string> = new Set()
private lastClickedElement: string | null = null
private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void
```

**Methods**:
- `constructor(canvas: any, statusCallback?: (msg: string) => void)`
- `setElementSelectionCallback(callback: (elementNames: string[], elementInfos: any[]) => void): void`
- `enterElementSelectionMode(target: any, pointer?: { x: number, y: number }): void`
- `exitElementSelectionMode(): void`
- `isInElementSelectionMode(): boolean`
- `getSelectedElementNames(): string[]`
- `clearElementSelection(): void`
- `createElementOverlay(target: any): void` - Private
- `updateElementOverlay(): void` - Private
- `setupElementSelectionEvents(): void` - Private
- `findElementAtPosition(canvasX: number, canvasY: number): string | null` - Private
- `findElementAtImageCoords(bboxes: any, imgX: number, imgY: number): string | null` - Private
- `findAllElementsAtImageCoords(bboxes: any, imgX: number, imgY: number): string[]` - Private
- `cycleElementSelection(canvasX: number, canvasY: number): string | null` - Private
- `selectElement(elementName: string, addToSelection: boolean): void` - Private
- `drawElementHighlight(ctx: CanvasRenderingContext2D, elementName: string, bbox: any, scaleX: number, scaleY: number, color: string, dashPattern?: number[]): void` - Private
- `distanceToNearestPoint(px: number, py: number, points: number[][]): number` - Private
- `distanceToLine(px: number, py: number, points: number[][]): number` - Private
- `distanceToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number` - Private
- `extractGroupsFromSelection(): { name: string; values: number[] }[]` - Private
- `extractElementData(imgObj: any, elementNames: string[]): { values: number[]; labels: string[] }` - Private
- `openStatsInspector(): void` - Private
- `showStatsInspectorPanel(data: { tests: any[]; effects: any[] }): void` - Private
- `addStatBracketAnnotation(testResult: any): void` - Private

**Dependencies**:
- Canvas instance
- Status callback (optional)
- Stats API endpoint (`/vis/api/plot/stats/`)

---

### 14. **canvas/ExportManager.ts**
**Lines**: ~150
**Responsibility**: Export canvas as PNG, SVG, PDF

**State Variables**:
```typescript
private canvas: any
```

**Methods**:
- `constructor(canvas: any, statusCallback?: (msg: string) => void)`
- `exportAsPng(): void`
- `exportAsSvg(): void`
- `exportAsPdf(): void`

**Dependencies**:
- Canvas instance
- Status callback (optional)

---

### 15. **canvas/ContextMenuManager.ts**
**Lines**: ~600
**Responsibility**: Right-click context menu, action routing

**State Variables**:
```typescript
private canvas: any
private contextMenuElement: HTMLDivElement | null = null
private rightClickPanOccurred: boolean = false
private contextMenuCallbacks: {
    delete?: () => void;
    duplicate?: () => void;
    bringToFront?: () => void;
    sendToBack?: () => void;
} = {}
```

**Methods**:
- `constructor(canvas: any, actionHandlers: ContextMenuActionHandlers)`
- `setupContextMenu(container: HTMLElement): void`
- `setCallbacks(callbacks: typeof this.contextMenuCallbacks): void`
- `showMenu(x: number, y: number, target: any): void` - Private
- `hideMenu(): void` - Private
- `handleAction(action: string, target: any): void` - Private

**Interface** (for dependency injection):
```typescript
interface ContextMenuActionHandlers {
    copy: () => void;
    paste: () => void;
    duplicate: () => void;
    delete: () => void;
    bringToFront: () => void;
    sendToBack: () => void;
    alignLeft: () => void;
    alignRight: () => void;
    alignTop: () => void;
    alignBottom: () => void;
    alignCenterH: () => void;
    alignCenterV: () => void;
    alignByAxisL: () => void;
    alignByAxisC: () => void;
    alignByAxisR: () => void;
    alignByAxisT: () => void;
    alignByAxisM: () => void;
    alignByAxisB: () => void;
    cropManual: () => void;
    cropMargin: () => void;
    cropReset: () => void;
    copyView: () => void;
    pasteView: () => void;
}
```

**Dependencies**:
- Canvas instance
- All managers (for action delegation)

---

## Module Communication Strategy

### 1. **Dependency Injection Pattern**
Main `CanvasManager` creates all modules and passes dependencies:

```typescript
export class CanvasManager {
    // Module instances
    private gridManager: GridManager;
    private themeManager: ThemeManager;
    private undoRedoManager: UndoRedoManager;
    private zoomPanManager: ZoomPanManager;
    private objectManager: ObjectManager;
    private selectionManager: SelectionManager;
    private alignmentManager: AlignmentManager;
    private cropManager: CropManager;
    private transformManager: TransformManager;
    private groupManager: GroupManager;
    private snapManager: SnapManager;
    private elementSelectionManager: ElementSelectionManager;
    private exportManager: ExportManager;
    private contextMenuManager: ContextMenuManager;

    constructor(
        private statusBarCallback?: (message: string) => void,
        private rulersAreaTransformCallback?: () => void
    ) {}

    public initCanvas(): void {
        // Create canvas
        this.canvas = new fabric.Canvas('vis-canvas', { /* ... */ });

        // Initialize modules in dependency order
        this.gridManager = new GridManager(this.canvas);
        this.themeManager = new ThemeManager(this.canvas, isDarkMode);
        this.undoRedoManager = new UndoRedoManager(this.canvas);
        this.zoomPanManager = new ZoomPanManager(
            this.canvas,
            this.rulersAreaTransformCallback,
            this.statusBarCallback
        );
        this.objectManager = new ObjectManager(
            this.canvas,
            this.themeManager
        );
        this.selectionManager = new SelectionManager(this.canvas);
        this.alignmentManager = new AlignmentManager(
            this.canvas,
            this.statusBarCallback
        );
        this.cropManager = new CropManager(
            this.canvas,
            this.statusBarCallback
        );
        this.transformManager = new TransformManager(
            this.canvas,
            this.statusBarCallback
        );
        this.groupManager = new GroupManager(
            this.canvas,
            this.statusBarCallback
        );
        this.snapManager = new SnapManager(this.canvas);
        this.elementSelectionManager = new ElementSelectionManager(
            this.canvas,
            this.statusBarCallback
        );
        this.exportManager = new ExportManager(
            this.canvas,
            this.statusBarCallback
        );

        // Context menu needs access to all action handlers
        this.contextMenuManager = new ContextMenuManager(
            this.canvas,
            this.createContextMenuActionHandlers()
        );

        // Setup events
        this.setupCanvasEvents();
    }

    private createContextMenuActionHandlers(): ContextMenuActionHandlers {
        return {
            copy: () => this.selectionManager.copyActiveObject(),
            paste: () => this.selectionManager.pasteObject(),
            duplicate: () => this.selectionManager.duplicateActiveObject(),
            delete: () => this.objectManager.removeActiveObject(),
            bringToFront: () => this.arrangeObject('front'),
            sendToBack: () => this.arrangeObject('back'),
            alignLeft: () => this.alignmentManager.alignObjects('left'),
            alignRight: () => this.alignmentManager.alignObjects('right'),
            alignTop: () => this.alignmentManager.alignObjects('top'),
            alignBottom: () => this.alignmentManager.alignObjects('bottom'),
            alignCenterH: () => this.alignmentManager.alignObjects('center-h'),
            alignCenterV: () => this.alignmentManager.alignObjects('center-v'),
            alignByAxisL: () => this.alignmentManager.alignByAxis('L'),
            alignByAxisC: () => this.alignmentManager.alignByAxis('C'),
            alignByAxisR: () => this.alignmentManager.alignByAxis('R'),
            alignByAxisT: () => this.alignmentManager.alignByAxis('T'),
            alignByAxisM: () => this.alignmentManager.alignByAxis('M'),
            alignByAxisB: () => this.alignmentManager.alignByAxis('B'),
            cropManual: () => this.cropManager.enterCropMode(),
            cropMargin: () => this.cropManager.multipleCrop(),
            cropReset: () => this.cropManager.resetCrop(),
            copyView: () => this.cropManager.copyView(),
            pasteView: () => this.cropManager.pasteView(),
        };
    }

    private setupCanvasEvents(): void {
        // Setup events for each module
        const container = document.getElementById('canvas-container')!;
        this.zoomPanManager.setupEvents(container);
        this.snapManager.setupEvents();
        this.contextMenuManager.setupContextMenu(container);

        // Canvas events (selection, modification)
        this.canvas.on('object:modified', () => {
            this.objectManager.saveCanvasContent();
            this.undoRedoManager.saveUndoState();
        });

        this.canvas.on('selection:created', (e: any) => {
            if (this.selectionCallback && e.selected && e.selected.length > 0) {
                const activeObj = this.canvas.getActiveObject();
                this.selectionCallback(activeObj || e.selected[0]);

                // Auto-enter element selection for plot images
                if (e.selected.length === 1) {
                    const selected = e.selected[0];
                    if ((selected.type === 'image' || selected.type === 'group') && selected.axisMetadata?.element_bboxes) {
                        this.elementSelectionManager.enterElementSelectionMode(selected, { x: 0, y: 0 });
                    }
                }
            }
        });

        this.canvas.on('selection:cleared', () => {
            if (this.selectionCallback) {
                this.selectionCallback(null);
            }
            this.elementSelectionManager.exitElementSelectionMode();
        });

        // Double-click for group edit
        this.canvas.on('mouse:dblclick', (e: any) => {
            const target = e.target;
            if (target && target.type === 'group') {
                const isPlotImage = target.plotInfo || target.csvData || target.axisMetadata;
                if (isPlotImage) {
                    if (this.statusBarCallback) {
                        this.statusBarCallback('Plot data cannot be edited (scientific integrity)');
                    }
                    return;
                }
                this.groupManager.enterGroupEditMode(target);
            }
        });
    }

    // Public API - delegates to modules
    public toggleGrid(): void {
        this.gridManager.toggleGrid();
    }

    public drawGrid(isDark: boolean): void {
        this.gridManager.drawGrid(isDark);
    }

    public updateCanvasTheme(isDark: boolean): void {
        this.themeManager.updateCanvasTheme(isDark);
        if (this.gridManager.isGridEnabled()) {
            this.gridManager.drawGrid(isDark);
        }
    }

    public zoomIn(): void {
        this.zoomPanManager.zoomIn();
    }

    public zoomOut(): void {
        this.zoomPanManager.zoomOut();
    }

    public addImage(src: string, options: any): Promise<any> {
        return this.objectManager.addImage(src, options);
    }

    // ... (delegate all other public methods)
}
```

### 2. **Event-Based Communication**
For loose coupling between modules:

```typescript
// Example: Theme change notification
class ThemeManager {
    private eventBus: EventTarget = new EventTarget();

    updateCanvasTheme(isDark: boolean): void {
        this.isDarkMode = isDark;
        this.canvas.backgroundColor = isDark ? '#2a2a2a' : '#ffffff';

        // Notify other modules
        this.eventBus.dispatchEvent(new CustomEvent('theme-changed', {
            detail: { isDark }
        }));
    }

    on(event: string, handler: EventListener): void {
        this.eventBus.addEventListener(event, handler);
    }
}

// In CanvasManager
this.themeManager.on('theme-changed', (e: CustomEvent) => {
    if (this.gridManager.isGridEnabled()) {
        this.gridManager.drawGrid(e.detail.isDark);
    }
});
```

### 3. **Shared State Access**
For state that multiple modules need:

```typescript
// Shared interface
interface ICanvasState {
    getCanvas(): any;
    getZoomLevel(): number;
    getPanOffset(): { x: number, y: number };
    isDarkMode(): boolean;
}

// CanvasManager implements interface
class CanvasManager implements ICanvasState {
    getCanvas(): any {
        return this.canvas;
    }

    getZoomLevel(): number {
        return this.zoomPanManager.getZoomLevel();
    }

    getPanOffset(): { x: number, y: number } {
        return this.zoomPanManager.getPanOffset();
    }

    isDarkMode(): boolean {
        return this.themeManager.isDark();
    }
}

// Modules receive state accessor
class AlignmentManager {
    constructor(
        private canvasState: ICanvasState,
        private statusCallback?: (msg: string) => void
    ) {}

    alignObjects(alignment: string): void {
        const canvas = this.canvasState.getCanvas();
        // ... use canvas
    }
}
```

---

## Migration Strategy

### Phase 1: Extract Simple Modules (Day 1)
1. **GridManager** - Self-contained, no dependencies
2. **ExportManager** - Self-contained, uses canvas only
3. **UndoRedoManager** - Minimal dependencies

**Validation**: Run existing tests, verify grid/export/undo work

### Phase 2: Extract State Managers (Day 2)
4. **ThemeManager** - Depends on GridManager
5. **ZoomPanManager** - Moderate complexity
6. **SelectionManager** - Simple clipboard logic

**Validation**: Test theme switching, zoom/pan, copy/paste

### Phase 3: Extract Transform Modules (Day 3)
7. **ObjectManager** - Depends on ThemeManager, UndoRedoManager
8. **TransformManager** - Uses UndoRedoManager
9. **GroupManager** - Uses UndoRedoManager

**Validation**: Test image add, transforms, grouping

### Phase 4: Extract Complex Modules (Day 4)
10. **AlignmentManager** - Complex but isolated
11. **SnapManager** - Moderate complexity
12. **CropManager** - Complex UI interactions

**Validation**: Test alignment, snapping, cropping

### Phase 5: Extract Advanced Modules (Day 5)
13. **ElementSelectionManager** - Most complex, stats integration
14. **ContextMenuManager** - Requires all managers

**Validation**: Test element selection, stats, context menu

### Phase 6: Integration & Testing (Day 6)
15. Update CanvasManager to orchestrate all modules
16. Comprehensive testing of all features
17. Performance testing (ensure no regressions)

---

## File Structure

```
apps/vis_app/static/vis_app/ts/vis/
├── CanvasManager.ts                    (~350 lines) - Main orchestrator
├── types.ts                             (existing)
├── canvas/
│   ├── GridManager.ts                   (~150 lines)
│   ├── ThemeManager.ts                  (~300 lines)
│   ├── UndoRedoManager.ts               (~120 lines)
│   ├── ZoomPanManager.ts                (~400 lines)
│   ├── ObjectManager.ts                 (~350 lines)
│   ├── SelectionManager.ts              (~200 lines)
│   ├── AlignmentManager.ts              (~350 lines)
│   ├── CropManager.ts                   (~400 lines)
│   ├── TransformManager.ts              (~280 lines)
│   ├── GroupManager.ts                  (~180 lines)
│   ├── SnapManager.ts                   (~350 lines)
│   ├── ElementSelectionManager.ts       (~600 lines)
│   ├── ExportManager.ts                 (~150 lines)
│   ├── ContextMenuManager.ts            (~600 lines)
│   └── types.ts                         (shared types/interfaces)
```

**Total Lines**: ~5,180 (reduced from 5,829 via deduplication and cleanup)

---

## Testing Strategy

### Unit Tests (New)
Each module gets isolated unit tests:

```typescript
// Example: GridManager.test.ts
describe('GridManager', () => {
    let canvas: any;
    let gridManager: GridManager;

    beforeEach(() => {
        canvas = createMockCanvas();
        gridManager = new GridManager(canvas);
    });

    test('should draw grid in light mode', () => {
        gridManager.drawGrid(false);
        expect(canvas.setBackgroundImage).toHaveBeenCalledWith(
            expect.objectContaining({ src: expect.stringContaining('grid-light.svg') }),
            expect.any(Function),
            expect.any(Object)
        );
    });

    test('should toggle grid visibility', () => {
        expect(gridManager.isGridEnabled()).toBe(true);
        gridManager.toggleGrid();
        expect(gridManager.isGridEnabled()).toBe(false);
    });
});
```

### Integration Tests
Test module interactions:

```typescript
describe('CanvasManager Integration', () => {
    let canvasManager: CanvasManager;

    beforeEach(() => {
        canvasManager = new CanvasManager();
        canvasManager.initCanvas();
    });

    test('theme change updates grid', () => {
        canvasManager.toggleGrid(); // Enable grid
        canvasManager.updateCanvasTheme(true); // Dark mode
        // Verify grid is dark mode
        expect(/* grid background is dark */).toBe(true);
    });

    test('undo/redo works after object add', async () => {
        await canvasManager.addImage('test.png');
        canvasManager.undo();
        expect(canvasManager.getActiveObject()).toBe(null);
        canvasManager.redo();
        expect(canvasManager.getActiveObject()).not.toBe(null);
    });
});
```

---

## Benefits

### Maintainability
- **File Size**: Max 600 lines per file (vs 5,829)
- **Single Responsibility**: Each module has one clear purpose
- **Isolation**: Bugs are contained to specific modules

### Testability
- **Unit Tests**: Each module can be tested in isolation
- **Mocking**: Easy to mock dependencies
- **Coverage**: Better code coverage visibility

### Performance
- **Code Splitting**: Modules can be lazy-loaded if needed
- **Tree Shaking**: Unused modules can be eliminated by bundlers

### Developer Experience
- **Navigation**: Easy to find relevant code
- **Onboarding**: New developers can understand modules independently
- **Parallel Work**: Multiple developers can work on different modules

---

## Risks & Mitigations

### Risk 1: Breaking Changes
**Mitigation**:
- Comprehensive integration tests before refactoring
- Extract modules one at a time, validate after each
- Keep original file as backup until migration complete

### Risk 2: Performance Regression
**Mitigation**:
- Profile before/after with Chrome DevTools
- Monitor canvas render times, zoom/pan responsiveness
- Ensure module instantiation is lightweight

### Risk 3: Circular Dependencies
**Mitigation**:
- Clear dependency hierarchy (see dependency graph below)
- Use interfaces for shared state access
- Event-based communication for loose coupling

---

## Dependency Graph

```
CanvasManager (orchestrator)
├── Canvas (Fabric.js instance)
│
├── GridManager
│   └── Canvas
│
├── ThemeManager
│   ├── Canvas
│   └── GridManager (optional, for grid redraw)
│
├── UndoRedoManager
│   └── Canvas
│
├── ZoomPanManager
│   └── Canvas
│
├── ObjectManager
│   ├── Canvas
│   ├── ThemeManager (dark mode processing)
│   └── UndoRedoManager (save state before add)
│
├── SelectionManager
│   ├── Canvas
│   └── UndoRedoManager (save state before paste)
│
├── AlignmentManager
│   └── Canvas
│
├── CropManager
│   ├── Canvas
│   └── UndoRedoManager (save state before crop)
│
├── TransformManager
│   ├── Canvas
│   └── UndoRedoManager (save state before transform)
│
├── GroupManager
│   ├── Canvas
│   └── UndoRedoManager (save state before group)
│
├── SnapManager
│   └── Canvas
│
├── ElementSelectionManager
│   └── Canvas
│
├── ExportManager
│   └── Canvas
│
└── ContextMenuManager
    ├── Canvas
    └── All Managers (via action handlers interface)
```

**Hierarchy**:
1. **Core**: Canvas, GridManager, ThemeManager, UndoRedoManager, ZoomPanManager
2. **Objects**: ObjectManager, SelectionManager
3. **Transforms**: AlignmentManager, CropManager, TransformManager, GroupManager
4. **Interaction**: SnapManager, ElementSelectionManager, ExportManager
5. **UI**: ContextMenuManager (depends on all)

---

## Implementation Checklist

### Pre-Refactoring
- [ ] Create backup branch: `git checkout -b backup/canvas-manager-pre-refactor`
- [ ] Document current behavior with integration tests
- [ ] Profile current performance (zoom, pan, render times)
- [ ] Create `canvas/` directory structure
- [ ] Create `canvas/types.ts` with shared interfaces

### Phase 1: Simple Modules
- [ ] Extract GridManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use GridManager
  - [ ] Test grid toggle, dark/light mode
- [ ] Extract ExportManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use ExportManager
  - [ ] Test PNG/SVG/PDF export
- [ ] Extract UndoRedoManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use UndoRedoManager
  - [ ] Test undo/redo after various operations

### Phase 2: State Managers
- [ ] Extract ThemeManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use ThemeManager
  - [ ] Test theme switching, image processing
- [ ] Extract ZoomPanManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use ZoomPanManager
  - [ ] Test zoom in/out/fit, pan, view persistence
- [ ] Extract SelectionManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use SelectionManager
  - [ ] Test select all, copy/paste, duplicate

### Phase 3: Transform Modules
- [ ] Extract ObjectManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use ObjectManager
  - [ ] Test image/SVG add, content persistence
- [ ] Extract TransformManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use TransformManager
  - [ ] Test match size, flip, rotate
- [ ] Extract GroupManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use GroupManager
  - [ ] Test group/ungroup, edit mode

### Phase 4: Complex Modules
- [ ] Extract AlignmentManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use AlignmentManager
  - [ ] Test alignment, distribution, axis align
- [ ] Extract SnapManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use SnapManager
  - [ ] Test snapping, guidelines, Alt key
- [ ] Extract CropManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use CropManager
  - [ ] Test manual crop, multiple crop, copy/paste view

### Phase 5: Advanced Modules
- [ ] Extract ElementSelectionManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use ElementSelectionManager
  - [ ] Test element selection, stats, annotations
- [ ] Extract ContextMenuManager
  - [ ] Create file, implement methods
  - [ ] Update CanvasManager to use ContextMenuManager
  - [ ] Test all context menu actions

### Phase 6: Integration
- [ ] Update CanvasManager to orchestrate all modules
- [ ] Remove duplicate code
- [ ] Add comprehensive integration tests
- [ ] Profile performance (compare with baseline)
- [ ] Update TypeScript imports in dependent files
- [ ] Update documentation

### Post-Refactoring
- [ ] Code review with team
- [ ] Merge to develop branch
- [ ] Monitor for regressions in production
- [ ] Archive backup branch after 2 weeks

---

## Success Metrics

### Quantitative
- **File Size**: All files <600 lines (target: <400)
- **Test Coverage**: >80% for each module
- **Performance**: No regression in zoom/pan/render times
- **Build Size**: Similar or smaller bundle size

### Qualitative
- **Readability**: New developers can understand modules in <30 min
- **Bug Isolation**: Bugs are traceable to specific modules
- **Extensibility**: New features (e.g., new alignment modes) are easy to add

---

## Notes

### TypeScript Best Practices
- Use strict mode: `"strict": true` in tsconfig.json
- Avoid `any` - use proper types/interfaces
- Document public APIs with JSDoc comments
- Use `readonly` for immutable properties

### Performance Considerations
- Throttle/debounce expensive operations (already implemented)
- Use requestAnimationFrame for DOM updates
- Minimize Fabric.js canvas renders (batch updates)

### Scientific Integrity
- **Element selection**: Read-only for plot elements (no edits)
- **Stats extraction**: Preserve original CSV data
- **Metadata**: Maintain axis_bbox_px, element_bboxes integrity

---

## Contact & Questions

For questions about this refactoring plan:
- **Architecture**: Discuss module boundaries, dependencies
- **Implementation**: Clarify method signatures, interfaces
- **Testing**: Add test cases for edge cases

Let's build maintainable, testable code! 🚀
