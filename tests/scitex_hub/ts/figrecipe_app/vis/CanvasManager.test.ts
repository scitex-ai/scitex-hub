/**
 * Tests for apps/figrecipe_app/static/figrecipe_app/ts/vis/CanvasManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/figrecipe_app/static/figrecipe_app/ts/vis/CanvasManager';

describe('CanvasManager', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/figrecipe_app/static/figrecipe_app/ts/vis/CanvasManager.ts
// =============================================================================

// /**
//  * CanvasManager - Handles all Fabric.js canvas operations
//  *
//  * Responsibilities:
//  * - Initialize Fabric.js canvas
//  * - Draw and manage grid lines
//  * - Handle canvas theme (light/dark)
//  * - Handle canvas-specific zoom and pan
//  * - Coordinate with rulers for unified transform
//  *
//  * NOTE: This file is being refactored to use specialized managers.
//  * See: /apps/figrecipe_app/static/figrecipe_app/ts/vis/canvas/REFACTORING_PLAN.md
//  */
//
// import { CANVAS_CONSTANTS } from './types';
// import { GridManager } from './canvas/GridManager';
// import { ExportManager } from './canvas/ExportManager';
// import { UndoRedoManager } from './canvas/UndoRedoManager';
// import { ThemeManager } from './canvas/ThemeManager';
// import { ZoomPanManager } from './canvas/ZoomPanManager';
// import { SelectionManager } from './canvas/SelectionManager';
// import { ObjectManager } from './canvas/ObjectManager';
// import { TransformManager } from './canvas/TransformManager';
// import { GroupManager } from './canvas/GroupManager';
// import { AlignmentManager } from './canvas/AlignmentManager';
// import { SnapManager } from './canvas/SnapManager';
// import { CropManager } from './canvas/CropManager';
// import { ElementSelectionManager } from './canvas/ElementSelectionManager';
// import { ContextMenuManager } from './canvas/ContextMenuManager';
// import { CanvasResizeManager } from './canvas/CanvasResizeManager';
// import { SessionManager } from './canvas/SessionManager';
// import { BundleCanvasManager } from './canvas/BundleCanvasManager';
// import { geometryManager, GeometryData } from './GeometryManager';
// import { serializeWithPrecision, parseWithPrecision, fixZeroScalePathsInJson, getCSRFToken } from './canvas/CanvasSerializationUtils';
//
// export class CanvasManager {
//     public canvas: any | null = null; // Fabric.js canvas instance
//
//     // Specialized managers (Phase 1, 2, 3, 4 & 5 refactoring)
//     private gridManager: GridManager | null = null;
//     private exportManager: ExportManager | null = null;
//     private undoRedoManager: UndoRedoManager | null = null;
//     private themeManager: ThemeManager | null = null;
//     private zoomPanManager: ZoomPanManager | null = null;
//     private selectionManager: SelectionManager | null = null;
//     private objectManager: ObjectManager | null = null;
//     private transformManager: TransformManager | null = null;
//     private groupManager: GroupManager | null = null;
//     private alignmentManager: AlignmentManager | null = null;
//     private snapManager: SnapManager | null = null;
//     private cropManager: CropManager | null = null;
//     private elementSelectionManager: ElementSelectionManager | null = null;
//     private contextMenuManager: ContextMenuManager | null = null;
//     private canvasResizeManager: CanvasResizeManager | null = null;
//     private sessionManager: SessionManager | null = null;
//     private bundleCanvasManager: BundleCanvasManager | null = null;
//
//     // Canvas zoom and pan state
//     private canvasZoomLevel: number = 0.22;
//     private canvasPanOffset: { x: number, y: number } = { x: 0, y: 0 };
//     private canvasIsPanning: boolean = false;
//     private canvasPanStartPoint: { x: number, y: number } | null = null;
//     private canvasIsZoomDragging: boolean = false;
//     private canvasZoomDragStartY: number = 0;
//     private canvasZoomDragStartLevel: number = 1;
//     private canvasDragThrottleFrame: number | null = null;
//     private canvasWheelThrottleFrame: number | null = null;
//     private canvasAccumulatedZoomDelta: number = 0;
//     private canvasAccumulatedPanDelta: { x: number, y: number } = { x: 0, y: 0 };
//     private canvasLastZoomMousePos: { x: number, y: number } = { x: 0, y: 0 };
//     private pendingDragUpdate: boolean = false;
//
//     // Hover tooltip for showing pltz path
//     private hoverTooltip: HTMLDivElement | null = null;
//
//     private panThrottleFrame: number | null = null;
//     private pendingPanUpdate: { x: number, y: number } | null = null;
//
//     // Track right-click pan to suppress context menu after panning
//     private rightClickPanOccurred: boolean = false;
//
//     // Column guides for layout snapping
//     private columnCount: number = 0; // 0 = disabled, 2-4 for multi-column layout
//     private columnGuidePositions: number[] = []; // X positions of column guides in mm
//
//     private selectionCallback?: (obj: any | null) => void;
//     private onObjectResizedCallback?: (obj: any, newWidth: number, newHeight: number) => void;
//
//     // Original image sources for theme switching (shared with ThemeManager via ObjectManager)
//     private originalImageSources: Map<any, string> = new Map();
//
//     // Bundle auto-save state
//     private autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
//     private autoSaveDelay: number = 1000; // Debounce delay in ms
//     private bundleProjectOwner: string = '';
//     private bundleProjectSlug: string = '';
//     private bundleFigureName: string = 'Figure1';
//
//     // Hit region overlay (debug visualization)
//     private hitRegionOverlayVisible: boolean = false;
//     private hitRegionOverlayImage: any = null; // Fabric.js image for hitmap overlay
//
//     constructor(
//         private statusBarCallback?: (message: string) => void,
//         private rulersAreaTransformCallback?: () => void
//     ) {}
//
//     /**
//      * Get current dark mode state from ThemeManager
//      */
//     private get isDarkMode(): boolean {
//         return this.themeManager?.isDark() ?? false;
//     }
//
//     /**
//      * Set callback for canvas selection changes
//      * Used to update properties panel when objects are selected/deselected
//      */
//     public setSelectionCallback(callback: (obj: any | null) => void): void {
//         this.selectionCallback = callback;
//     }
//
//     /**
//      * Set callback for object resize events
//      * Used to re-render plots at new size to maintain font proportions
//      */
//     public setObjectResizedCallback(callback: (obj: any, newWidth: number, newHeight: number) => void): void {
//         this.onObjectResizedCallback = callback;
//     }
//
//     /**
//      * Get canvas zoom level
//      * Delegates to ZoomPanManager as the single source of truth
//      */
//     public getCanvasZoomLevel(): number {
//         if (this.zoomPanManager) {
//             return this.zoomPanManager.getZoomLevel();
//         }
//         return this.canvasZoomLevel;
//     }
//
//     /**
//      * Get canvas pan offset
//      * Delegates to ZoomPanManager as the single source of truth
//      */
//     public getCanvasPanOffset(): { x: number, y: number } {
//         if (this.zoomPanManager) {
//             return this.zoomPanManager.getPanOffset();
//         }
//         return { x: this.canvasPanOffset.x, y: this.canvasPanOffset.y };
//     }
//
//     /**
//      * Set canvas zoom level (used when restoring tab state or ruler sync)
//      */
//     public setCanvasZoomLevel(zoom: number): void {
//         this.canvasZoomLevel = zoom;
//         if (this.zoomPanManager) {
//             this.zoomPanManager.setZoomLevel(zoom);
//         }
//     }
//
//     /**
//      * Set canvas pan offset (used when restoring tab state or ruler sync)
//      */
//     public setCanvasPanOffset(x: number, y: number): void {
//         this.canvasPanOffset.x = x;
//         this.canvasPanOffset.y = y;
//         if (this.zoomPanManager) {
//             this.zoomPanManager.setPanOffset(x, y);
//         }
//     }
//
//     /**
//      * Get canvas document size in mm
//      * DELEGATES to CanvasResizeManager
//      */
//     public getCanvasSizeMm(): { width: number, height: number } {
//         return this.canvasResizeManager?.getCanvasSizeMm() || { width: 180, height: 250 };
//     }
//
//     /**
//      * Set canvas document size in mm
//      * DELEGATES to CanvasResizeManager
//      */
//     public setCanvasSizeMm(widthMm: number, heightMm: number): void {
//         if (this.canvasResizeManager) {
//             this.canvasResizeManager.setCanvasSize(widthMm, heightMm);
//         }
//     }
//
//     /**
//      * Increase canvas document size
//      * DELEGATES to CanvasResizeManager
//      */
//     public increaseCanvasSize(): void {
//         if (this.canvasResizeManager) {
//             this.canvasResizeManager.increaseSize();
//             this.drawGrid(this.themeManager?.isDark() || false);
//         }
//     }
//
//     /**
//      * Decrease canvas document size
//      * DELEGATES to CanvasResizeManager
//      */
//     public decreaseCanvasSize(): void {
//         if (this.canvasResizeManager) {
//             this.canvasResizeManager.decreaseSize();
//             this.drawGrid(this.themeManager?.isDark() || false);
//         }
//     }
//
//     /**
//      * Reset canvas document size to default
//      * DELEGATES to CanvasResizeManager
//      */
//     public resetCanvasSize(): void {
//         if (this.canvasResizeManager) {
//             this.canvasResizeManager.resetSize();
//             this.drawGrid(this.themeManager?.isDark() || false);
//         }
//     }
//
//     /**
//      * Fit canvas document size to content bounds
//      * DELEGATES to CanvasResizeManager
//      */
//     public fitCanvasToContent(): void {
//         if (this.canvasResizeManager) {
//             const success = this.canvasResizeManager.fitToContent();
//             if (success) {
//                 this.drawGrid(this.themeManager?.isDark() || false);
//                 // Zoom view to show the fitted content
//                 this.zoomToContent();
//                 this.saveSessionState();
//                 // Also trigger figz auto-save if bundle manager exists
//                 if (this.bundleCanvasManager) {
//                     this.bundleCanvasManager.debouncedFigzAutoSave();
//                 }
//             }
//         }
//     }
//
//     /**
//      * Initialize Fabric.js canvas
//      */
//     public initCanvas(): void {
//         const startTime = performance.now();
//         console.log('[CanvasManager] Starting canvas initialization...');
//
//         const canvasElement = document.getElementById('vis-canvas') as HTMLCanvasElement;
//         if (!canvasElement) {
//             console.error('[CanvasManager] Canvas element #vis-canvas not found in DOM');
//             return;
//         }
//
//         if (typeof fabric === 'undefined') {
//             console.error('[CanvasManager] Fabric.js is not loaded!');
//             return;
//         }
//
//         const defaultWidth = CANVAS_CONSTANTS.MAX_CANVAS_WIDTH;   // 180mm @ 300dpi
//         const defaultHeight = CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT; // 240mm @ 300dpi
//
//         // Get initial theme from localStorage (canvas has its own theme, defaults to global)
//         const globalTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
//         const savedCanvasTheme = localStorage.getItem('canvas-theme') || globalTheme;
//         const initialIsDark = savedCanvasTheme === 'dark';
//         const initialBgColor = initialIsDark ? '#2a2a2a' : '#ffffff';
//
//         try {
//             // Initialize canvas with correct theme from the start
//             this.canvas = new fabric.Canvas('vis-canvas', {
//                 width: defaultWidth,
//                 height: defaultHeight,
//                 backgroundColor: initialBgColor,
//                 selection: true,
//                 selectionKey: ['ctrlKey', 'shiftKey'],  // Multi-select with Ctrl or Shift
//                 // Selection styling - make more visible
//                 selectionColor: 'rgba(100, 150, 255, 0.15)',
//                 selectionBorderColor: '#4a9eff',
//                 selectionLineWidth: 2,
//             });
//
//             // Set default object selection styling (bolder borders)
//             fabric.Object.prototype.set({
//                 borderColor: '#4a9eff',
//                 borderScaleFactor: 2,
//                 cornerColor: '#4a9eff',
//                 cornerStyle: 'circle',
//                 cornerSize: 10,
//                 cornerStrokeColor: '#fff',
//                 transparentCorners: false,
//                 padding: 4,
//             });
//
//             const canvasCreateTime = performance.now();
//             console.log(`[CanvasManager] Fabric.js canvas created in ${(canvasCreateTime - startTime).toFixed(2)}ms (${defaultWidth}×${defaultHeight}px)`);
//
//             // Initialize specialized managers (Phase 1, 2 & 3 refactoring)
//             this.gridManager = new GridManager(this.canvas, this.statusBarCallback);
//             this.exportManager = new ExportManager(this.canvas, this.statusBarCallback);
//             this.undoRedoManager = new UndoRedoManager(this.canvas, this.statusBarCallback);
//             this.themeManager = new ThemeManager(this.canvas, initialIsDark, this.statusBarCallback);
//             this.zoomPanManager = new ZoomPanManager(this.canvas, this.rulersAreaTransformCallback, this.statusBarCallback);
//             this.selectionManager = new SelectionManager(this.canvas, this.statusBarCallback);
//
//             // Phase 3 managers - object manipulation, transforms, and grouping
//             this.objectManager = new ObjectManager(
//                 this.canvas,
//                 () => this.themeManager?.isDark() || false,
//                 (img) => this.themeManager?.updateImageForTheme(img),
//                 (group) => this.processSvgGroupForDarkMode(group),
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent(),
//                 this.statusBarCallback
//             );
//             this.transformManager = new TransformManager(
//                 this.canvas,
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent(),
//                 this.statusBarCallback
//             );
//             this.groupManager = new GroupManager(
//                 this.canvas,
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent(),
//                 this.statusBarCallback
//             );
//
//             // Phase 4 managers - alignment, snapping, and cropping
//             this.alignmentManager = new AlignmentManager(
//                 this.statusBarCallback,
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent()
//             );
//             this.alignmentManager.initialize(this.canvas);
//
//             this.snapManager = new SnapManager(
//                 this.statusBarCallback,
//                 () => this.getCanvasZoomLevel(),
//                 () => this.getCanvasPanOffset()
//             );
//             this.snapManager.initialize(this.canvas);
//
//             this.cropManager = new CropManager(
//                 this.statusBarCallback,
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent(),
//                 () => this.getCanvasZoomLevel(),
//                 () => this.getCanvasPanOffset()
//             );
//             this.cropManager.initialize(this.canvas);
//
//             // Phase 5 managers - element selection and context menu
//             this.elementSelectionManager = new ElementSelectionManager(
//                 this.canvas,
//                 this.statusBarCallback
//             );
//
//             this.contextMenuManager = new ContextMenuManager(
//                 this.canvas,
//                 () => this.elementSelectionManager?.getSelectedElementNames() || [],
//                 this.statusBarCallback
//             );
//
//             // Phase 6 manager - canvas document resize (Ctrl+drag edges)
//             this.canvasResizeManager = new CanvasResizeManager(
//                 this.canvas,
//                 () => this.getCanvasZoomLevel(),
//                 () => this.getCanvasPanOffset(),
//                 () => {
//                     // Update rulers when canvas size changes
//                     if (this.rulersAreaTransformCallback) {
//                         this.rulersAreaTransformCallback();
//                     }
//                     // Redraw grid if enabled
//                     if (this.gridManager?.isGridEnabled()) {
//                         this.gridManager.drawGrid(this.themeManager?.isDark() || false);
//                     }
//                 },
//                 this.statusBarCallback
//             );
//
//             // Phase 7 managers - session and bundle management
//             this.bundleCanvasManager = new BundleCanvasManager(
//                 this.canvas,
//                 this.statusBarCallback,
//                 (w: number, h: number) => this.setCanvasSizeMm(w, h),
//                 () => this.clearCanvas(),
//                 () => this.saveSessionState(),
//                 (img: any) => this.processNewImageForTheme(img),
//                 (path: string | null) => this.setCurrentFigzPath(path)
//             );
//
//             this.sessionManager = new SessionManager(
//                 this.canvas,
//                 () => this.getCurrentFigzPath(),
//                 () => ({
//                     owner: this.bundleProjectOwner,
//                     slug: this.bundleProjectSlug,
//                     figureName: this.bundleFigureName,
//                 }),
//                 (path: string) => this.loadFigzBundle(path)
//             );
//
//             // Draw initial grid if enabled
//             if (this.gridManager.isGridEnabled()) {
//                 this.gridManager.drawGrid(initialIsDark);
//                 const gridTime = performance.now();
//                 console.log(`[CanvasManager] Grid drawn in ${(gridTime - canvasCreateTime).toFixed(2)}ms`);
//                 console.log(`[CanvasManager] ✅ Total canvas init: ${(gridTime - startTime).toFixed(2)}ms`);
//             } else {
//                 console.log(`[CanvasManager] ✅ Total canvas init: ${(canvasCreateTime - startTime).toFixed(2)}ms`);
//             }
//
//             // Restore saved view state
//             if (this.zoomPanManager) {
//                 this.zoomPanManager.restoreViewState();
//                 // Sync CanvasManager's internal state with ZoomPanManager
//                 // (wheel handler uses these internal variables directly)
//                 this.canvasZoomLevel = this.zoomPanManager.getZoomLevel();
//                 const panOffset = this.zoomPanManager.getPanOffset();
//                 this.canvasPanOffset.x = panOffset.x;
//                 this.canvasPanOffset.y = panOffset.y;
//             }
//
//             // Save canvas when objects are modified (moved, scaled, rotated)
//             this.canvas.on('object:modified', () => {
//                 this.saveCanvasContent();
//             });
//
//             // Also save on selection cleared (in case of deselect after move)
//             this.canvas.on('selection:cleared', () => {
//                 this.saveCanvasContent();
//                 // Notify properties panel of deselection
//                 if (this.selectionCallback) {
//                     this.selectionCallback(null);
//                 }
//             });
//
//             // Notify properties panel when object selected
//             // Also auto-enter element selection mode for plot images with element_bboxes
//             this.canvas.on('selection:created', (e: any) => {
//                 if (this.selectionCallback && e.selected && e.selected.length > 0) {
//                     // For multi-selection, pass the ActiveSelection or first object
//                     const activeObj = this.canvas?.getActiveObject();
//                     this.selectionCallback(activeObj || e.selected[0]);
//
//                     // Only auto-enter element selection for SINGLE selection of plot images/groups
//                     if (e.selected.length === 1) {
//                         const selected = e.selected[0];
//                         // Support both image and group (SVG) types with element_bboxes
//                         if ((selected.type === 'image' || selected.type === 'group') && selected.axisMetadata?.element_bboxes) {
//                             this.elementSelectionManager?.enterElementSelectionMode(selected, { x: 0, y: 0 });
//                         }
//                     } else {
//                         // Exit element selection mode for multi-selection
//                         this.elementSelectionManager?.exitElementSelectionMode();
//                     }
//                 }
//             });
//
//             this.canvas.on('selection:updated', (e: any) => {
//                 if (this.selectionCallback && e.selected && e.selected.length > 0) {
//                     // For multi-selection, pass the ActiveSelection or first object
//                     const activeObj = this.canvas?.getActiveObject();
//                     this.selectionCallback(activeObj || e.selected[0]);
//
//                     // Only auto-enter element selection for SINGLE selection of plot images/groups
//                     if (e.selected.length === 1) {
//                         const selected = e.selected[0];
//                         // Support both image and group (SVG) types with element_bboxes
//                         if ((selected.type === 'image' || selected.type === 'group') && selected.axisMetadata?.element_bboxes) {
//                             this.elementSelectionManager?.enterElementSelectionMode(selected, { x: 0, y: 0 });
//                         } else {
//                             this.elementSelectionManager?.exitElementSelectionMode();
//                         }
//                     } else {
//                         // Exit element selection mode for multi-selection
//                         this.elementSelectionManager?.exitElementSelectionMode();
//                     }
//                 }
//             });
//
//             this.canvas.on('selection:cleared', () => {
//                 if (this.selectionCallback) {
//                     this.selectionCallback(null);
//                 }
//                 // Exit element selection mode when deselecting
//                 this.exitElementSelectionMode();
//             });
//
//             // Double-click to enter group (PowerPoint-style sub-element selection)
//             // SCIENTIFIC INTEGRITY: Plot images should NOT have individual elements editable
//             this.canvas.on('mouse:dblclick', (e: any) => {
//                 const target = e.target;
//                 if (target && target.type === 'group') {
//                     // Check if this is a scientific plot (has data attached)
//                     // Plot images should NOT be editable at element level for scientific integrity
//                     const isPlotImage = target.plotInfo || target.csvData || target.axisMetadata;
//                     if (isPlotImage) {
//                         if (this.statusBarCallback) {
//                             this.statusBarCallback('Plot data cannot be edited (scientific integrity)');
//                         }
//                         console.log('[CanvasManager] Blocked group edit for plot image (scientific integrity)');
//                         return;
//                     }
//                     // Only allow group edit mode for non-plot groups (e.g., imported SVGs, shapes)
//                     this.enterGroupEditMode(target);
//                 }
//                 // Note: Element selection mode is now auto-entered on selection
//             });
//
//             // Snap to other objects while moving (PowerPoint-style)
//             // Throttled using requestAnimationFrame for performance
//             this.canvas.on('object:moving', (e: any) => {
//                 if (this.snapManager?.isSnapEnabled()) {
//                     this.snapManager.handleObjectSnap(e.target);
//                 }
//             });
//
//             // Clear alignment guidelines when object stops moving
//             this.canvas.on('object:modified', (e: any) => {
//                 this.snapManager?.clearAlignmentLines();
//                 this.saveCanvasContent();
//
//                 // Check if object was scaled and needs re-render
//                 const obj = e.target;
//                 if (obj && (obj.scaleX !== 1 || obj.scaleY !== 1)) {
//                     // Notify for re-render if object has plot data
//                     if (obj.csvData && obj.plotInfo && this.onObjectResizedCallback) {
//                         const newWidth = Math.round(obj.width * obj.scaleX);
//                         const newHeight = Math.round(obj.height * obj.scaleY);
//                         this.onObjectResizedCallback(obj, newWidth, newHeight);
//                     }
//                 }
//
//                 // Update properties panel if selection callback exists
//                 if (this.selectionCallback && obj) {
//                     this.selectionCallback(obj);
//                 }
//
//                 // Trigger figz auto-save for bundle panels
//                 if (obj && obj.isBundlePanel) {
//                     this.bundleCanvasManager?.debouncedFigzAutoSave();
//                 }
//             });
//
//             // Clear guidelines on mouse up
//             this.canvas.on('mouse:up', () => {
//                 this.snapManager?.clearAlignmentLines();
//                 // Reset snap state when mouse is released
//                 this.lastSnapX = null;
//                 this.lastSnapY = null;
//             });
//         } catch (error) {
//             console.error('[CanvasManager] Error initializing canvas:', error);
//         }
//     }
//
//     /**
//      * Enter group edit mode - allows selecting elements inside a group
//      * Double-click on group to enter, click outside to exit
//      * DELEGATES to GroupManager
//      */
//     private enterGroupEditMode(group: any): void {
//         if (this.groupManager) {
//             this.groupManager.enterGroupEditMode(group);
//         }
//     }
//
//     /**
//      * Exit group edit mode - regroup the objects
//      * DELEGATES to GroupManager
//      */
//     public exitGroupEditMode(): void {
//         if (this.groupManager) {
//             this.groupManager.exitGroupEditMode();
//         }
//     }
//
//     /**
//      * Draw grid using pre-rendered static SVG files
//      * DELEGATES to GridManager
//      */
//     public drawGrid(isDark: boolean = false): void {
//         if (this.gridManager) {
//             this.gridManager.drawGrid(isDark);
//         }
//     }
//
//     /**
//      * Clear grid background from canvas
//      * DELEGATES to GridManager
//      */
//     public clearGrid(): void {
//         if (this.gridManager) {
//             this.gridManager.clearGrid();
//         }
//     }
//
//     /**
//      * Toggle grid visibility
//      * DELEGATES to GridManager
//      */
//     public toggleGrid(): void {
//         if (this.gridManager) {
//             this.gridManager.toggleGrid();
//         }
//     }
//
//     /**
//      * Update canvas theme
//      */
//     public updateCanvasTheme(isDark: boolean): void {
//         if (!this.themeManager) return;
//
//         // Create callback for grid redraw
//         const gridRedrawCallback = () => {
//             if (this.gridManager && this.gridManager.isGridEnabled()) {
//                 this.gridManager.drawGrid(isDark);
//             }
//         };
//
//         this.themeManager.updateCanvasTheme(isDark, gridRedrawCallback);
//     }
//
//     /**
//      * Process SVG group paths for dark mode display
//      * DELEGATES to ThemeManager
//      */
//     public processSvgGroupForDarkMode(group: any): void {
//         if (this.themeManager) {
//             this.themeManager.processSvgGroupForDarkMode(group);
//         }
//     }
//
//     /**
//      * Restore SVG group paths to original colors (for light mode)
//      * DELEGATES to ThemeManager
//      */
//     public restoreSvgGroupColors(group: any): void {
//         if (this.themeManager) {
//             this.themeManager.restoreSvgGroupColors(group);
//         }
//     }
//
//     /**
//      * Process a newly added image for current theme (dark mode conversion)
//      * DELEGATES to ThemeManager
//      */
//     public processNewImageForTheme(img: any): void {
//         if (this.themeManager) {
//             this.themeManager.processNewImage(img);
//         }
//     }
//
//     /**
//      * Reprocess all SVG groups when theme changes
//      * Uses remove/re-add strategy to force complete re-render
//      */
//     public reprocessAllSvgGroupsForTheme(): void {
//         if (this.themeManager) {
//             this.themeManager.reprocessAllSvgGroupsForTheme();
//         }
//     }
//
//
//     /**
//      * Save undo state
//      * DELEGATES to UndoRedoManager
//      */
//     public saveUndoState(): void {
//         if (this.undoRedoManager) {
//             this.undoRedoManager.saveUndoState();
//         }
//     }
//
//     /**
//      * Undo last action
//      * DELEGATES to UndoRedoManager
//      */
//     public undo(): void {
//         if (this.undoRedoManager) {
//             this.undoRedoManager.undo();
//         }
//     }
//
//     /**
//      * Redo last undone action
//      * DELEGATES to UndoRedoManager
//      */
//     public redo(): void {
//         if (this.undoRedoManager) {
//             this.undoRedoManager.redo();
//         }
//     }
//
//
//     // View clipboard for copy/paste view (axis limits, crop)
//     private viewClipboard: {
//         cropX?: number;
//         cropY?: number;
//         width?: number;
//         height?: number;
//         scaleX?: number;
//         scaleY?: number;
//     } | null = null;
//
//     /**
//      * Copy active object to clipboard
//      * DELEGATES to SelectionManager
//      */
//     public copyActiveObject(): void {
//         if (this.selectionManager) {
//             this.selectionManager.copyActiveObject();
//         }
//     }
//
//     /**
//      * Paste object from clipboard
//      * DELEGATES to SelectionManager
//      */
//     public pasteObject(): void {
//         if (this.selectionManager) {
//             this.selectionManager.pasteObject(
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent()
//             );
//         }
//     }
//
//     // Context menu callbacks
//     private contextMenuCallbacks: {
//         delete?: () => void;
//         duplicate?: () => void;
//         bringToFront?: () => void;
//         sendToBack?: () => void;
//     } = {};
//
//     /**
//      * Set context menu callbacks
//      */
//     public setContextMenuCallbacks(callbacks: typeof this.contextMenuCallbacks): void {
//         this.contextMenuCallbacks = callbacks;
//     }
//
//     /**
//      * Setup canvas zoom/pan events
//      */
//     public setupCanvasEvents(): void {
//         const canvasContainer = document.getElementById("canvas-container");
//         if (!canvasContainer || !this.canvas) {
//             console.warn("[CanvasManager] Canvas container or Fabric.js canvas not found");
//             return;
//         }
//
//         // Delegate to specialized managers
//         if (this.contextMenuManager) {
//             this.contextMenuManager.setupContextMenu(canvasContainer);
//         }
//
//         if (this.canvasResizeManager) {
//             this.canvasResizeManager.setupResizeListeners(canvasContainer);
//         }
//
//         if (this.zoomPanManager) {
//             this.zoomPanManager.setupEvents(canvasContainer);
//         }
//
//         // Listen for canvas theme changes from keyboard shortcut (Alt+T)
//         document.addEventListener("canvas-theme-changed", ((e: CustomEvent) => {
//             this.updateCanvasTheme(e.detail.isDark);
//         }) as EventListener);
//
//         console.log("[CanvasManager] Canvas events initialized (delegated to managers)");
//     }
//
//     public updateCanvasTransform(): void {
//         if (!this.canvas) return;
//
//         // Keep Fabric.js canvas at identity transform
//         // All zoom/pan is handled by CSS transform on .vis-rulers-area parent
//         this.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
//
//         // Update CSS transform on rulers area
//         const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
//         if (rulersArea) {
//             rulersArea.style.transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
//             rulersArea.style.transformOrigin = '0 0';
//         }
//
//         // Save state to localStorage for persistence
//         this.saveViewState();
//     }
//
//     /**
//      * Save view state to localStorage (debounced)
//      */
//     private saveViewStateTimer: ReturnType<typeof setTimeout> | null = null;
//     private saveViewState(): void {
//         if (this.saveViewStateTimer) {
//             clearTimeout(this.saveViewStateTimer);
//         }
//         this.saveViewStateTimer = setTimeout(() => {
//             const state = {
//                 zoom: this.canvasZoomLevel,
//                 panX: this.canvasPanOffset.x,
//                 panY: this.canvasPanOffset.y,
//             };
//             localStorage.setItem('scitex-vis-viewstate', JSON.stringify(state));
//             console.log('[CanvasManager] 💾 Saved view state:', state);
//         }, 200); // Debounce 200ms
//     }
//
//     /**
//      * Restore view state from localStorage
//      */
//     public restoreViewState(): void {
//         try {
//             const saved = localStorage.getItem('scitex-vis-viewstate');
//             console.log('[CanvasManager] 📂 Raw localStorage value:', saved);
//             if (saved) {
//                 const state = JSON.parse(saved);
//                 console.log('[CanvasManager] 📂 Parsed state:', state);
//                 if (state.zoom !== undefined) this.canvasZoomLevel = state.zoom;
//                 if (state.panX !== undefined) this.canvasPanOffset.x = state.panX;
//                 if (state.panY !== undefined) this.canvasPanOffset.y = state.panY;
//                 console.log('[CanvasManager] 📂 Applied to internal state - zoom:', this.canvasZoomLevel, 'panX:', this.canvasPanOffset.x, 'panY:', this.canvasPanOffset.y);
//                 // Apply the restored transform to DOM elements (without triggering save)
//                 this.applyTransformWithoutSave();
//             } else {
//                 console.log('[CanvasManager] 📂 No saved state found in localStorage');
//             }
//         } catch (err) {
//             console.warn('[CanvasManager] Failed to restore view state:', err);
//         }
//     }
//
//     /**
//      * Apply CSS transform without triggering save (used during restore)
//      */
//     private applyTransformWithoutSave(): void {
//         if (!this.canvas) {
//             console.warn('[CanvasManager] ⚠️ applyTransformWithoutSave: canvas not available');
//             return;
//         }
//
//         // Keep Fabric.js canvas at identity transform
//         this.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
//
//         // Update CSS transform on rulers area
//         const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
//         if (rulersArea) {
//             const transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
//             rulersArea.style.transform = transform;
//             rulersArea.style.transformOrigin = '0 0';
//             console.log('[CanvasManager] ✅ Applied CSS transform:', transform);
//         } else {
//             console.warn('[CanvasManager] ⚠️ .vis-rulers-area not found in DOM');
//         }
//
//         // Update rulers callback if set
//         if (this.rulersAreaTransformCallback) {
//             this.rulersAreaTransformCallback();
//         }
//     }
//
//     /**
//      * Save canvas content to localStorage (debounced)
//      */
//     private saveContentDebounceTimer: ReturnType<typeof setTimeout> | null = null;
//     public saveCanvasContent(): void {
//         if (this.saveContentDebounceTimer) {
//             clearTimeout(this.saveContentDebounceTimer);
//         }
//         this.saveContentDebounceTimer = setTimeout(() => {
//             this.saveCanvasContentImmediate();
//         }, 1000); // Save after 1 second of no changes
//     }
//
//     private saveCanvasContentImmediate(): void {
//         if (!this.canvas) return;
//         try {
//             const json = this.canvas.toJSON(['name', 'id', 'axisMetadata', 'plotInfo', 'originalWidth', 'originalHeight']);
//             const jsonString = serializeWithPrecision(json);
//             localStorage.setItem('scitex-vis-canvas', jsonString);
//             console.log('[CanvasManager] Saved canvas content to localStorage');
//         } catch (err) {
//             console.warn('[CanvasManager] Failed to save canvas:', err);
//         }
//     }
//
//
//     /**
//      * Restore canvas content from localStorage
//      * Returns the restored objects so metadata can be loaded if needed
//      */
//     public restoreCanvasContent(): Promise<any[]> {
//         return new Promise((resolve) => {
//             if (!this.canvas) {
//                 resolve([]);
//                 return;
//             }
//             try {
//                 const saved = localStorage.getItem('scitex-vis-canvas');
//                 if (saved) {
//                     // Parse with custom reviver to restore tiny numbers
//                     const json = parseWithPrecision(saved);
//
//                     // Fallback: fix any remaining zero-scale paths (from old saves)
//                     fixZeroScalePathsInJson(json);
//
//                     this.canvas.loadFromJSON(json, () => {
//                         // Apply dark mode color transformation to restored SVG groups
//                         if (this.isDarkMode) {
//                             this.reprocessAllSvgGroupsForTheme();
//                         }
//                         this.canvas!.renderAll();
//                         const objects = this.canvas!.getObjects();
//                         console.log(`[CanvasManager] Restored canvas content (${objects.length} objects)`);
//                         resolve(objects);
//                     });
//                 } else {
//                     resolve([]);
//                 }
//             } catch (err) {
//                 console.warn('[CanvasManager] Failed to restore canvas:', err);
//                 resolve([]);
//             }
//         });
//     }
//
//     /**
//      * Parse JSON with restoration of tiny numbers preserved by serializeWithPrecision
//      */
//
//     // ========================================
//     // SESSION STATE PERSISTENCE (Page Refresh)
//     // ========================================
//
//     private static SESSION_STORAGE_KEY = 'scitex-vis-session';
//
//     /**
//      * Save session state to localStorage for page refresh recovery
//      * Includes: figz path, project context, panels info
//      */
//     public saveSessionState(): void {
//         try {
//             const sessionState = {
//                 timestamp: Date.now(),
//                 figzPath: this.currentFigzPath,
//                 projectOwner: this.bundleProjectOwner,
//                 projectSlug: this.bundleProjectSlug,
//                 figureName: this.bundleFigureName,
//                 canvasSize: this.canvas ? {
//                     width: this.canvas.getWidth(),
//                     height: this.canvas.getHeight(),
//                 } : null,
//                 panels: this.getBundlePanelsForSession(),
//             };
//
//             localStorage.setItem(CanvasManager.SESSION_STORAGE_KEY, JSON.stringify(sessionState));
//             console.log('[CanvasManager] Session state saved');
//         } catch (err) {
//             console.warn('[CanvasManager] Failed to save session state:', err);
//         }
//     }
//
//     /**
//      * Get panel info for session storage (lightweight version of getBundlePanels)
//      */
//     private getBundlePanelsForSession(): any[] {
//         if (!this.canvas) return [];
//
//         const panels: any[] = [];
//         const objects = this.canvas.getObjects();
//
//         for (const obj of objects) {
//             const plotInfo = (obj as any).plotInfo;
//             if (plotInfo?.bundlePath) {
//                 panels.push({
//                     label: plotInfo.panelLabel || 'A',
//                     pltzPath: plotInfo.bundlePath,
//                     position: {
//                         left: obj.left,
//                         top: obj.top,
//                     },
//                     size: {
//                         width: obj.getScaledWidth(),
//                         height: obj.getScaledHeight(),
//                     },
//                 });
//             }
//         }
//
//         return panels;
//     }
//
//     /**
//      * Restore session state from localStorage
//      * Returns the session state if found and valid, null otherwise
//      */
//     public getSessionState(): {
//         figzPath: string | null;
//         projectOwner: string;
//         projectSlug: string;
//         figureName: string;
//         canvasSize: { width: number; height: number } | null;
//         panels: any[];
//         timestamp: number;
//     } | null {
//         try {
//             const saved = localStorage.getItem(CanvasManager.SESSION_STORAGE_KEY);
//             if (!saved) return null;
//
//             const state = JSON.parse(saved);
//
//             // Check if session is recent (within 24 hours)
//             const maxAge = 24 * 60 * 60 * 1000; // 24 hours
//             if (Date.now() - state.timestamp > maxAge) {
//                 console.log('[CanvasManager] Session state expired, clearing');
//                 this.clearSessionState();
//                 return null;
//             }
//
//             return state;
//         } catch (err) {
//             console.warn('[CanvasManager] Failed to restore session state:', err);
//             return null;
//         }
//     }
//
//     /**
//      * Clear session state from localStorage
//      */
//     public clearSessionState(): void {
//         localStorage.removeItem(CanvasManager.SESSION_STORAGE_KEY);
//         console.log('[CanvasManager] Session state cleared');
//     }
//
//     /**
//      * Restore session - load figz bundle from saved state
//      * Returns true if session was restored, false otherwise
//      */
//     public async restoreSession(): Promise<boolean> {
//         const session = this.getSessionState();
//         if (!session) {
//             console.log('[CanvasManager] No valid session to restore');
//             return false;
//         }
//
//         console.log('[CanvasManager] Restoring session:', session);
//
//         // Restore project context
//         if (session.projectOwner && session.projectSlug) {
//             this.bundleProjectOwner = session.projectOwner;
//             this.bundleProjectSlug = session.projectSlug;
//         }
//         if (session.figureName) {
//             this.bundleFigureName = session.figureName;
//         }
//
//         // If we have a figz path, reload it
//         if (session.figzPath) {
//             try {
//                 await this.loadFigzBundle(session.figzPath);
//                 console.log('[CanvasManager] Session restored from figz:', session.figzPath);
//                 return true;
//             } catch (err) {
//                 console.warn('[CanvasManager] Failed to load figz from session:', err);
//             }
//         }
//
//         // Fallback: restore canvas content from localStorage (panels without figz)
//         if (session.panels && session.panels.length > 0) {
//             console.log('[CanvasManager] Restoring panels from session...');
//             // Canvas content is restored via restoreCanvasContent() in VisEditor
//             return true;
//         }
//
//         return false;
//     }
//
//     /**
//      * Setup beforeunload handler to save state before page close/refresh
//      */
//     public setupBeforeUnloadHandler(): void {
//         window.addEventListener('beforeunload', () => {
//             // Save session state synchronously
//             this.saveSessionStateSync();
//         });
//
//         // Also save periodically (every 30 seconds)
//         setInterval(() => {
//             this.saveSessionState();
//         }, 30000);
//
//         console.log('[CanvasManager] Page refresh handler installed');
//     }
//
//     /**
//      * Synchronous version of saveSessionState for beforeunload
//      * Uses localStorage.setItem which is synchronous
//      */
//     private saveSessionStateSync(): void {
//         try {
//             const sessionState = {
//                 timestamp: Date.now(),
//                 figzPath: this.currentFigzPath,
//                 projectOwner: this.bundleProjectOwner,
//                 projectSlug: this.bundleProjectSlug,
//                 figureName: this.bundleFigureName,
//                 canvasSize: this.canvas ? {
//                     width: this.canvas.getWidth(),
//                     height: this.canvas.getHeight(),
//                 } : null,
//                 panels: this.getBundlePanelsForSession(),
//             };
//
//             localStorage.setItem(CanvasManager.SESSION_STORAGE_KEY, JSON.stringify(sessionState));
//         } catch (err) {
//             // Silent fail for beforeunload
//         }
//     }
//
//     /**
//      * Update canvas zoom display
//      */
//     private updateCanvasZoomDisplay(): void {
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`Canvas Zoom: ${Math.round(this.canvasZoomLevel * 100)}%`);
//         }
//         console.log(`[CanvasManager] Canvas zoom level: ${Math.round(this.canvasZoomLevel * 100)}%`);
//     }
//
//     /**
//      * Zoom in
//      */
//     public zoomIn(): void {
//         if (this.zoomPanManager) {
//             this.zoomPanManager.zoomIn();
//         }
//     }
//
//     public zoomOut(): void {
//         if (this.zoomPanManager) {
//             this.zoomPanManager.zoomOut();
//         }
//     }
//
//     public zoomToFit(): void {
//         if (this.zoomPanManager) {
//             this.zoomPanManager.zoomToFit();
//         }
//     }
//
//
//     /**
//      * Zoom to fit content - calculates bounding box of all objects and fits view
//      * DELEGATES to ZoomPanManager
//      */
//     public zoomToContent(): void {
//         if (this.zoomPanManager) {
//             this.zoomPanManager.zoomToContent();
//         } else {
//             // Fallback: use local implementation
//             this.zoomToFit();
//         }
//     }
//
//     /**
//      * Apply zoom
//      */
//     private applyZoom(): void {
//         this.updateCanvasTransform();
//         if (this.rulersAreaTransformCallback) {
//             this.rulersAreaTransformCallback();
//         }
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`Canvas: ${Math.round(this.canvasZoomLevel * 100)}%`);
//         }
//     }
//
//     /**
//      * Add image to canvas from URL or data URL
//      * Automatically extracts embedded scitex metadata for axis snap/align
//      */
//     public addImage(src: string, options: any = {}): Promise<any> {
//         if (this.objectManager) {
//             return this.objectManager.addImage(src, options);
//         }
//         return Promise.reject("ObjectManager not initialized");
//     }
//
//
//     /**
//      * Add image from base64 data
//      */
//     public async addImageFromBase64(base64Data: string, options: Parameters<typeof this.addImage>[1] = {}): Promise<any> {
//         // Ensure it's a valid data URL
//         const dataUrl = base64Data.startsWith('data:')
//             ? base64Data
//             : `data:image/png;base64,${base64Data}`;
//
//         return this.addImage(dataUrl, options);
//     }
//
//     /**
//      * Add SVG to canvas with selectable sub-elements
//      * This allows selecting individual parts of a figure (axes, legend, title, etc.)
//      */
//     public addSvg(svgString: string, options: any = {}): Promise<any> {
//         if (this.objectManager) {
//             return this.objectManager.addSvg(svgString, options);
//         }
//         return Promise.reject("ObjectManager not initialized");
//     }
//
//     /**
//      * Add SVG from URL with selectable sub-elements
//      */
//     public addSvgFromUrl(url: string, options: Parameters<typeof this.addSvg>[1] = {}): Promise<any> {
//         return new Promise((resolve, reject) => {
//             fetch(url)
//                 .then(response => response.text())
//                 .then(svgString => {
//                     this.addSvg(svgString, options).then(resolve).catch(reject);
//                 })
//                 .catch(reject);
//         });
//     }
//
//     /**
//      * Clear all objects from canvas (except grid)
//      */
//     public clearCanvas(): void {
//         if (!this.canvas) return;
//
//         const objects = this.canvas.getObjects();
//         objects.forEach((obj: any) => {
//             // Don't remove grid-related objects
//             if (obj.id !== 'grid-line' && obj.id !== 'column-guide') {
//                 this.canvas!.remove(obj);
//             }
//         });
//
//         this.canvas.renderAll();
//
//         if (this.statusBarCallback) {
//             this.statusBarCallback('Canvas cleared');
//         }
//         console.log('[CanvasManager] Canvas cleared');
//     }
//
//     // =========================================================================
//     // Bundle Integration (pltz/figz) - Canvas backed by SciTeX bundles
//     // =========================================================================
//
//     // Current figz bundle path (if loaded)
//     private currentFigzPath: string | null = null;
//
//     // DPI for mm-to-pixel conversion
//     private bundleRenderDpi: number = 150;
//
//     /**
//      * Load a figz bundle onto the canvas.
//      * Clears existing content and loads figure with all panels.
//      *
//      * @param figzPath - Filesystem path to .figz bundle (zipped format)
//      */
//     public async loadFigzBundle(figzPath: string): Promise<void> {
//         if (this.bundleCanvasManager) {
//             return this.bundleCanvasManager.loadFigzBundle(figzPath);
//         }
//     }
//
//
//     /**
//      * Load a single pltz panel onto the canvas.
//      *
//      * @param panel - Panel spec with position, size, and plot reference
//      * @param figzPath - Parent figz bundle path
//      */
//     public async loadPltzPanel(panel: any, figzPath: string): Promise<void> {
//         if (this.bundleCanvasManager) {
//             await this.bundleCanvasManager.loadPltzPanel(panel, figzPath);
//         }
//     }
//
//
//     /**
//      * Refresh a panel image after property changes.
//      *
//      * @param pltzPath - Path to the pltz bundle
//      */
//     public async refreshPanelImage(pltzPath: string): Promise<void> {
//         if (this.bundleCanvasManager) {
//             return this.bundleCanvasManager.refreshPanelImage(pltzPath);
//         }
//     }
//
//
//     /**
//      * Get the current figz bundle path.
//      */
//     public getCurrentFigzPath(): string | null {
//         return this.currentFigzPath;
//     }
//
//     /**
//      * Set the current figz bundle path.
//      * Used when switching tabs to reset or restore figz context.
//      */
//     public setCurrentFigzPath(path: string | null): void {
//         this.currentFigzPath = path;
//         console.log(`[CanvasManager] Set currentFigzPath to: ${path}`);
//     }
//
//     /**
//      * Check if an object is a bundle panel.
//      */
//     public isBundlePanel(obj: any): boolean {
//         return obj && obj.isBundlePanel === true;
//     }
//
//     /**
//      * Get all bundle panels on canvas.
//      */
//     public getBundlePanels(): any[] {
//         if (!this.canvas) return [];
//         return this.canvas.getObjects().filter((obj: any) => obj.isBundlePanel === true);
//     }
//
//     /**
//      * Add a panel to the canvas from gallery selection.
//      *
//      * Creates a pltz bundle from the plot type and data, then adds it to the canvas.
//      *
//      * @param plotType - The plot type (line, scatter, bar, etc.)
//      * @param dataCsv - Optional CSV data string
//      * @param projectOwner - Project owner for saving bundle
//      * @param projectSlug - Project slug for saving bundle
//      * @param figureName - Figure name (optional, defaults to 'Figure1')
//      * @returns The created panel info
//      */
//     public async addPanelFromGallery(
//         plotType: string,
//         dataCsv?: string,
//         projectOwner?: string,
//         projectSlug?: string,
//         figureName?: string,
//         galleryCategory?: string,
//         galleryPlotName?: string
//     ): Promise<{ panelLabel: string; bundlePath: string } | null> {
//         if (this.bundleCanvasManager) {
//             // Project context is already set via setProjectContext(), pass gallery params
//             return this.bundleCanvasManager.addPanelFromGallery(plotType, dataCsv, galleryCategory, galleryPlotName);
//         }
//         return null;
//     }
//
//     public async triggerFigzAutoSave(
//         projectOwner?: string,
//         projectSlug?: string,
//         figureName?: string
//     ): Promise<void> {
//         if (this.bundleCanvasManager) {
//             await this.bundleCanvasManager.triggerFigzAutoSave();
//         }
//     }
//
//     /**
//      * Set bundle project context for auto-save.
//      *
//      * @param owner - Project owner username
//      * @param slug - Project slug
//      * @param figureName - Optional figure name
//      */
//     public setBundleProjectContext(owner: string, slug: string, figureName?: string): void {
//         this.bundleProjectOwner = owner;
//         this.bundleProjectSlug = slug;
//         if (figureName) {
//             this.bundleFigureName = figureName;
//         }
//         // Forward to BundleCanvasManager
//         if (this.bundleCanvasManager) {
//             this.bundleCanvasManager.setProjectContext(owner, slug, figureName || this.bundleFigureName);
//         }
//         console.log(`[CanvasManager] Bundle project context set: ${owner}/${slug}/${this.bundleFigureName}`);
//     }
//
//     /**
//      * Get active object
//      */
//     public getActiveObject(): any {
//         return this.canvas?.getActiveObject() || null;
//     }
//
//     /**
//      * Remove active object(s) - handles both single and multiple selection
//      */
//     public removeActiveObject(): void {
//         if (this.objectManager) {
//             this.objectManager.removeActiveObject();
//         }
//     }
//
//
//     /**
//      * Select all objects on canvas
//      */
//     public selectAll(): void {
//         if (this.selectionManager) {
//             this.selectionManager.selectAll();
//         }
//     }
//
//
//     /**
//      * Duplicate active object
//      */
//     public duplicateActiveObject(): void {
//         if (this.selectionManager) {
//             this.selectionManager.duplicateActiveObject(
//                 () => this.saveUndoState(),
//                 () => this.saveCanvasContent()
//             );
//         }
//     }
//
//
//     /**
//      * Bring active object to front
//      * DELEGATES to AlignmentManager
//      */
//     public bringToFront(): void {
//         this.alignmentManager?.bringToFront();
//     }
//
//     /**
//      * Send active object to back
//      * DELEGATES to AlignmentManager
//      */
//     public sendToBack(): void {
//         this.alignmentManager?.sendToBack();
//     }
//
//     /**
//      * Arrange object (bring to front or send to back)
//      * Used by keyboard shortcuts (Alt+G → F/B)
//      * DELEGATES to AlignmentManager
//      */
//     public arrangeObject(action: 'front' | 'back'): void {
//         this.alignmentManager?.arrangeObject(action);
//     }
//
//     /**
//      * Align selected objects
//      * - Single object: Aligns to canvas (like PowerPoint aligns to slide)
//      * - Multiple objects: Aligns objects relative to each other
//      * DELEGATES to AlignmentManager
//      */
//     public alignObjects(alignment: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v'): void {
//         this.alignmentManager?.alignObjects(alignment);
//     }
//
//     /**
//      * Distribute selected objects evenly
//      */
//     public distributeObjects(direction: "horizontal" | "vertical"): void {
//         if (this.alignmentManager) {
//             this.alignmentManager.distributeObjects(direction);
//         }
//     }
//
//
//     /**
//      * Apply crop from first selected object to all selected objects (Multiple Crop)
//      * PowerPoint-style: First object's crop values applied to all
//      */
//     public multipleCrop(): void {
//         // Delegate to CropManager
//         if (this.cropManager) {
//             this.cropManager.multipleCrop();
//         }
//     }
//
//
//     /**
//      * Reset crop on selected image(s)
//      */
//     public resetCrop(): void {
//         // Delegate to CropManager
//         if (this.cropManager) {
//             this.cropManager.resetCrop();
//         }
//     }
//
//     /**
//      * Auto crop margin using Python backend
//      * Detects and removes white/transparent margins from images
//      */
//     public async autoCropMargin(): Promise<void> {
//         // Delegate to CropManager
//         if (this.cropManager) {
//             await this.cropManager.autoCropMargin();
//         }
//     }
//
//     /**
//      * Match size of selected objects to first object
//      * PowerPoint-style: First object's size applied to all
//      */
//     public matchSize(): void {
//         if (this.transformManager) {
//             this.transformManager.matchSize();
//         }
//     }
//
//     public matchWidth(): void {
//         if (this.transformManager) {
//             this.transformManager.matchWidth();
//         }
//     }
//
//     public matchHeight(): void {
//         if (this.transformManager) {
//             this.transformManager.matchHeight();
//         }
//     }
//
//     public resetSize(): void {
//         if (this.transformManager) {
//             this.transformManager.resetSize();
//         }
//     }
//
//     public flipHorizontal(): void {
//         if (this.transformManager) {
//             this.transformManager.flipHorizontal();
//         }
//     }
//
//     public flipVertical(): void {
//         if (this.transformManager) {
//             this.transformManager.flipVertical();
//         }
//     }
//
//     public rotateObjects(degrees: number): void {
//         if (this.transformManager) {
//             this.transformManager.rotateObjects(degrees);
//         }
//     }
//
//
//     /**
//      * Group selected objects
//      */
//     public groupObjects(): void {
//         if (this.groupManager) {
//             this.groupManager.groupObjects();
//         }
//     }
//
//     public ungroupObjects(): void {
//         if (this.groupManager) {
//             this.groupManager.ungroupObjects();
//         }
//     }
//
//     /**
//      * Align by axis with direction support (like regular alignment)
//      * @param direction - L=left(Y-axis), C=center-H, R=right, T=top, M=middle-V, B=bottom(X-axis)
//      */
//     public alignByAxis(direction: "L" | "C" | "R" | "T" | "M" | "B" = "L"): void {
//         if (this.alignmentManager) {
//             this.alignmentManager.alignByAxis(direction);
//         }
//     }
//
//
//     /**
//      * Stack selected plots vertically with Y-axis alignment.
//      * First aligns Y-axes (left edges), then stacks plots so each plot's
//      * top edge touches the previous plot's X-axis (bottom edge).
//      * Order is determined by current vertical position (top to bottom).
//      */
//     public stackVertically(): void {
//         if (this.alignmentManager) {
//             this.alignmentManager.stackVertically();
//         }
//     }
//
//     public showAxisDebugLines(objects?: any[]): void {
//         if (!this.canvas) return;
//
//         // Clear existing debug lines
//         this.clearAxisDebugLines();
//
//         // Get objects to show debug for
//         const targetObjects = objects || this.canvas.getObjects().filter(
//             (obj: any) => obj.type === 'image' && obj.axisMetadata?.axes_bbox_px
//         );
//
//         if (targetObjects.length === 0) {
//             console.log('[CanvasManager] No objects with axis metadata to show debug lines');
//             return;
//         }
//
//         console.log(`[CanvasManager] Showing axis debug lines for ${targetObjects.length} objects`);
//
//         targetObjects.forEach((obj: any, idx: number) => {
//             const meta = obj.axisMetadata?.axes_bbox_px;
//             if (!meta) return;
//
//             const scaleX = obj.scaleX || 1;
//             const scaleY = obj.scaleY || 1;
//             const left = obj.left || 0;
//             const top = obj.top || 0;
//
//             // Calculate axis positions in canvas coordinates
//             const yAxisX = left + meta.x0 * scaleX;  // Y-axis (left edge of plot)
//             const xAxisY = top + meta.y1 * scaleY;   // X-axis (bottom edge of plot)
//             const rightX = left + meta.x1 * scaleX;  // Right edge of plot
//             const topY = top + meta.y0 * scaleY;     // Top edge of plot
//
//             console.log(`  [${idx}] ${obj.name}: left=${left.toFixed(1)}, top=${top.toFixed(1)}, ` +
//                 `scaleX=${scaleX.toFixed(3)}, scaleY=${scaleY.toFixed(3)}`);
//             console.log(`       meta: x0=${meta.x0}, y0=${meta.y0}, x1=${meta.x1}, y1=${meta.y1}`);
//             console.log(`       canvas: yAxisX=${yAxisX.toFixed(1)}, xAxisY=${xAxisY.toFixed(1)}`);
//
//             // Y-axis line (red, vertical) - from top of plot to bottom
//             const yAxisLine = new (window as any).fabric.Line(
//                 [yAxisX, topY, yAxisX, xAxisY],
//                 {
//                     stroke: '#ff0000',
//                     strokeWidth: 2,
//                     selectable: false,
//                     evented: false,
//                     strokeDashArray: [5, 3],
//                     name: `debug-y-axis-${idx}`
//                 }
//             );
//
//             // X-axis line (blue, horizontal) - from Y-axis to right edge
//             const xAxisLine = new (window as any).fabric.Line(
//                 [yAxisX, xAxisY, rightX, xAxisY],
//                 {
//                     stroke: '#0066ff',
//                     strokeWidth: 2,
//                     selectable: false,
//                     evented: false,
//                     strokeDashArray: [5, 3],
//                     name: `debug-x-axis-${idx}`
//                 }
//             );
//
//             // Add to canvas and store references
//             this.canvas!.add(yAxisLine, xAxisLine);
//             this.axisDebugLines.push(yAxisLine, xAxisLine);
//         });
//
//         this.canvas.renderAll();
//
//         // Auto-clear after 5 seconds
//         setTimeout(() => this.clearAxisDebugLines(), 5000);
//
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`Showing axis debug lines (auto-clear in 5s)`);
//         }
//     }
//
//     /**
//      * Clear axis debug lines from canvas
//      */
//     public clearAxisDebugLines(): void {
//         if (!this.canvas) return;
//
//         this.axisDebugLines.forEach(line => {
//             this.canvas!.remove(line);
//         });
//         this.axisDebugLines = [];
//         this.canvas.renderAll();
//     }
//
//     /**
//      * Nudge selected objects (move or resize)
//      * Arrow keys = move by 1px (or 10px with Alt)
//      * Shift+Arrow = resize by 1px (or 10px with Alt)
//      */
//     public nudgeObjects(direction: 'up' | 'down' | 'left' | 'right', resize: boolean): void {
//         if (!this.canvas) return;
//
//         const active = this.canvas.getActiveObject();
//         if (!active) return;
//
//         // Determine step size (could be made configurable)
//         const step = 1; // 1px per arrow press
//
//         // Get objects to modify
//         const objects = active.type === 'activeSelection'
//             ? (active as any).getObjects()
//             : [active];
//
//         if (resize) {
//             // Shift+Arrow = Resize
//             objects.forEach((obj: any) => {
//                 const currentScaleX = obj.scaleX || 1;
//                 const currentScaleY = obj.scaleY || 1;
//                 const width = obj.width * currentScaleX;
//                 const height = obj.height * currentScaleY;
//
//                 switch (direction) {
//                     case 'up': // Decrease height
//                         obj.scaleY = Math.max(0.01, (height - step) / obj.height);
//                         break;
//                     case 'down': // Increase height
//                         obj.scaleY = (height + step) / obj.height;
//                         break;
//                     case 'left': // Decrease width
//                         obj.scaleX = Math.max(0.01, (width - step) / obj.width);
//                         break;
//                     case 'right': // Increase width
//                         obj.scaleX = (width + step) / obj.width;
//                         break;
//                 }
//                 obj.setCoords();
//             });
//         } else {
//             // Arrow = Move
//             objects.forEach((obj: any) => {
//                 switch (direction) {
//                     case 'up':
//                         obj.top = (obj.top || 0) - step;
//                         break;
//                     case 'down':
//                         obj.top = (obj.top || 0) + step;
//                         break;
//                     case 'left':
//                         obj.left = (obj.left || 0) - step;
//                         break;
//                     case 'right':
//                         obj.left = (obj.left || 0) + step;
//                         break;
//                 }
//                 obj.setCoords();
//             });
//         }
//
//         this.canvas.renderAll();
//
//         // Debounced save to avoid saving on every keypress
//         if (!this.nudgeSaveTimer) {
//             this.nudgeSaveTimer = setTimeout(() => {
//                 this.saveCanvasContent();
//                 this.nudgeSaveTimer = null;
//             }, 500);
//         }
//     }
//
//     private nudgeSaveTimer: ReturnType<typeof setTimeout> | null = null;
//
//     /**
//      * Copy view settings (crop, size, scale) from selected object
//      * For scientific plots: copy axis limits / ROI to apply to other panels
//      */
//     public copyView(): void {
//         if (this.cropManager) {
//             this.cropManager.copyView();
//         }
//     }
//
//     public pasteView(): void {
//         if (this.cropManager) {
//             this.cropManager.pasteView();
//         }
//     }
//
//     // ========================================
//     // SNAP AND ALIGNMENT GUIDELINES (OPTIMIZED)
//     // ========================================
//
//     /**
//      * Toggle snap functionality
//      */
//     public toggleSnap(): void {
//         if (this.snapManager) {
//             this.snapManager.toggleSnap();
//         }
//     }
//
//     public isSnapEnabled(): boolean {
//         return this.snapManager?.isSnapEnabled() || false;
//     }
//
//
//     /**
//      * Initialize guideline overlay (CSS-based for performance)
//      */
//     private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void;
//
//     public setElementSelectionCallback(callback: (elementNames: string[], elementInfos: any[]) => void): void {
//         this.elementSelectionCallback = callback;
//         if (this.elementSelectionManager) {
//             this.elementSelectionManager.setElementSelectionCallback(callback);
//         }
//     }
//
//     public exitElementSelectionMode(): void {
//         if (this.elementSelectionManager) {
//             this.elementSelectionManager.exitElementSelectionMode();
//         }
//     }
//
//     public isInElementSelectionMode(): boolean {
//         return this.elementSelectionManager?.isInElementSelectionMode() || false;
//     }
//
//     public clearElementSelection(): void {
//         if (this.elementSelectionManager) {
//             this.elementSelectionManager.clearElementSelection();
//         }
//     }
//     public downloadFigzDBundle(): void {
//         if (this.exportManager) {
//             if (this.currentFigzPath) {
//                 this.exportManager.setFigzPath(this.currentFigzPath);
//             }
//             this.exportManager.downloadFigzDBundle();
//         }
//     }
//
//     /**
//      * Download a pltz bundle as .pltz ZIP file
//      * Downloads the selected panel's bundle
//      */
//     public downloadPltzBundle(): void {
//         if (!this.exportManager) return;
//
//         // Get selected object
//         const activeObj = this.canvas?.getActiveObject();
//         if (!activeObj) {
//             this.updateStatusBar?.('No panel selected for download');
//             return;
//         }
//
//         // Get pltz path from the selected object
//         const pltzPath = (activeObj as any).pltzPath;
//         if (!pltzPath) {
//             this.updateStatusBar?.('Selected object is not a pltz panel');
//             return;
//         }
//
//         this.exportManager.downloadPltzBundle(pltzPath);
//     }
//
//     /**
//      * Toggle canvas theme between light and dark
//      */
//     public toggleCanvasTheme(): void {
//         if (this.themeManager) {
//             this.themeManager.toggleTheme(() => this.drawGrid(this.themeManager?.isDark() || false));
//         }
//     }
//
//     /**
//      * Reset view to default zoom and pan
//      */
//     public resetView(): void {
//         this.canvasZoomLevel = 1.0;
//         this.canvasPanOffset = { x: 0, y: 0 };
//
//         // Update rulers area transform
//         const rulersArea = document.getElementById('canvas-rulers-area');
//         if (rulersArea) {
//             rulersArea.style.transform = 'translate(0px, 0px) scale(1)';
//         }
//
//         // Update zoom display
//         const zoomDisplay = document.getElementById('zoom-level-display');
//         if (zoomDisplay) {
//             zoomDisplay.textContent = '100%';
//         }
//
//         if (this.statusBarCallback) {
//             this.statusBarCallback('View reset to 100%');
//         }
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
