/**
 * CanvasManager - Handles all Fabric.js canvas operations
 *
 * Responsibilities:
 * - Initialize Fabric.js canvas
 * - Draw and manage grid lines
 * - Handle canvas theme (light/dark)
 * - Handle canvas-specific zoom and pan
 * - Coordinate with rulers for unified transform
 *
 * NOTE: This file is being refactored to use specialized managers.
 * See: /apps/vis_app/static/vis_app/ts/vis/canvas/REFACTORING_PLAN.md
 */

import { CANVAS_CONSTANTS } from './types.ts';
import { GridManager } from './canvas/GridManager.ts';
import { ExportManager } from './canvas/ExportManager.ts';
import { UndoRedoManager } from './canvas/UndoRedoManager.ts';
import { ThemeManager } from './canvas/ThemeManager.ts';
import { ZoomPanManager } from './canvas/ZoomPanManager.ts';
import { SelectionManager } from './canvas/SelectionManager.ts';
import { ObjectManager } from './canvas/ObjectManager.ts';
import { TransformManager } from './canvas/TransformManager.ts';
import { GroupManager } from './canvas/GroupManager.ts';
import { AlignmentManager } from './canvas/AlignmentManager.ts';
import { SnapManager } from './canvas/SnapManager.ts';
import { CropManager } from './canvas/CropManager.ts';
import { ElementSelectionManager } from './canvas/ElementSelectionManager.ts';
import { ContextMenuManager } from './canvas/ContextMenuManager.ts';
import { CanvasResizeManager } from './canvas/CanvasResizeManager.ts';
import { SessionManager } from './canvas/SessionManager.ts';
import { BundleCanvasManager } from './canvas/BundleCanvasManager.ts';
import { geometryManager, GeometryData } from './GeometryManager.ts';

export class CanvasManager {
    public canvas: any | null = null; // Fabric.js canvas instance

    // Specialized managers (Phase 1, 2, 3, 4 & 5 refactoring)
    private gridManager: GridManager | null = null;
    private exportManager: ExportManager | null = null;
    private undoRedoManager: UndoRedoManager | null = null;
    private themeManager: ThemeManager | null = null;
    private zoomPanManager: ZoomPanManager | null = null;
    private selectionManager: SelectionManager | null = null;
    private objectManager: ObjectManager | null = null;
    private transformManager: TransformManager | null = null;
    private groupManager: GroupManager | null = null;
    private alignmentManager: AlignmentManager | null = null;
    private snapManager: SnapManager | null = null;
    private cropManager: CropManager | null = null;
    private elementSelectionManager: ElementSelectionManager | null = null;
    private contextMenuManager: ContextMenuManager | null = null;
    private canvasResizeManager: CanvasResizeManager | null = null;
    private sessionManager: SessionManager | null = null;
    private bundleCanvasManager: BundleCanvasManager | null = null;

    // Canvas zoom and pan state
    private canvasZoomLevel: number = 0.22;
    private canvasPanOffset: { x: number, y: number } = { x: 0, y: 0 };
    private canvasIsPanning: boolean = false;
    private canvasPanStartPoint: { x: number, y: number } | null = null;
    private canvasIsZoomDragging: boolean = false;
    private canvasZoomDragStartY: number = 0;
    private canvasZoomDragStartLevel: number = 1;
    private canvasDragThrottleFrame: number | null = null;
    private canvasWheelThrottleFrame: number | null = null;
    private canvasAccumulatedZoomDelta: number = 0;
    private canvasAccumulatedPanDelta: { x: number, y: number } = { x: 0, y: 0 };
    private canvasLastZoomMousePos: { x: number, y: number } = { x: 0, y: 0 };
    private pendingDragUpdate: boolean = false;

    // Snap and alignment guidelines
    private snapEnabled: boolean = true;
    private snapThreshold: number = 10; // pixels for snap detection
    private guidelineOverlay: HTMLDivElement | null = null; // CSS overlay for guidelines (faster than Fabric.js)

    // Hover tooltip for showing pltz path
    private hoverTooltip: HTMLDivElement | null = null;

    // Throttling for object moving (performance optimization)
    private objectMovingThrottleFrame: number | null = null;
    private pendingMovingTarget: any = null;
    private panThrottleFrame: number | null = null;
    private pendingPanUpdate: { x: number, y: number } | null = null;

    // Track right-click pan to suppress context menu after panning
    private rightClickPanOccurred: boolean = false;

    // Column guides for layout snapping
    private columnCount: number = 0; // 0 = disabled, 2-4 for multi-column layout
    private columnGuidePositions: number[] = []; // X positions of column guides in mm

    private selectionCallback?: (obj: any | null) => void;
    private onObjectResizedCallback?: (obj: any, newWidth: number, newHeight: number) => void;

    // Original image sources for theme switching (shared with ThemeManager via ObjectManager)
    private originalImageSources: Map<any, string> = new Map();

    // Bundle auto-save state
    private autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
    private autoSaveDelay: number = 1000; // Debounce delay in ms
    private bundleProjectOwner: string = '';
    private bundleProjectSlug: string = '';
    private bundleFigureName: string = 'Figure1';

    // Hit region overlay (debug visualization)
    private hitRegionOverlayVisible: boolean = false;
    private hitRegionOverlayImage: any = null; // Fabric.js image for hitmap overlay

    constructor(
        private statusBarCallback?: (message: string) => void,
        private rulersAreaTransformCallback?: () => void
    ) {}

    /**
     * Get current dark mode state from ThemeManager
     */
    private get isDarkMode(): boolean {
        return this.themeManager?.isDark() ?? false;
    }

    /**
     * Set callback for canvas selection changes
     * Used to update properties panel when objects are selected/deselected
     */
    public setSelectionCallback(callback: (obj: any | null) => void): void {
        this.selectionCallback = callback;
    }

    /**
     * Set callback for object resize events
     * Used to re-render plots at new size to maintain font proportions
     */
    public setObjectResizedCallback(callback: (obj: any, newWidth: number, newHeight: number) => void): void {
        this.onObjectResizedCallback = callback;
    }

    /**
     * Get canvas zoom level
     * Returns CanvasManager's internal state (used by wheel handlers)
     */
    public getCanvasZoomLevel(): number {
        return this.canvasZoomLevel;
    }

    /**
     * Get canvas pan offset
     * Returns CanvasManager's internal state (used by wheel handlers)
     */
    public getCanvasPanOffset(): { x: number, y: number } {
        return { x: this.canvasPanOffset.x, y: this.canvasPanOffset.y };
    }

    /**
     * Set canvas zoom level (used when restoring tab state or ruler sync)
     */
    public setCanvasZoomLevel(zoom: number): void {
        this.canvasZoomLevel = zoom;
        if (this.zoomPanManager) {
            this.zoomPanManager.setZoomLevel(zoom);
        }
    }

    /**
     * Set canvas pan offset (used when restoring tab state or ruler sync)
     */
    public setCanvasPanOffset(x: number, y: number): void {
        this.canvasPanOffset.x = x;
        this.canvasPanOffset.y = y;
        if (this.zoomPanManager) {
            this.zoomPanManager.setPanOffset(x, y);
        }
    }

    /**
     * Get canvas document size in mm
     * DELEGATES to CanvasResizeManager
     */
    public getCanvasSizeMm(): { width: number, height: number } {
        return this.canvasResizeManager?.getCanvasSizeMm() || { width: 180, height: 250 };
    }

    /**
     * Set canvas document size in mm
     * DELEGATES to CanvasResizeManager
     */
    public setCanvasSizeMm(widthMm: number, heightMm: number): void {
        if (this.canvasResizeManager) {
            this.canvasResizeManager.setCanvasSize(widthMm, heightMm);
        }
    }

    /**
     * Increase canvas document size
     * DELEGATES to CanvasResizeManager
     */
    public increaseCanvasSize(): void {
        if (this.canvasResizeManager) {
            this.canvasResizeManager.increaseSize();
            this.drawGrid(this.themeManager?.isDark() || false);
        }
    }

    /**
     * Decrease canvas document size
     * DELEGATES to CanvasResizeManager
     */
    public decreaseCanvasSize(): void {
        if (this.canvasResizeManager) {
            this.canvasResizeManager.decreaseSize();
            this.drawGrid(this.themeManager?.isDark() || false);
        }
    }

    /**
     * Reset canvas document size to default
     * DELEGATES to CanvasResizeManager
     */
    public resetCanvasSize(): void {
        if (this.canvasResizeManager) {
            this.canvasResizeManager.resetSize();
            this.drawGrid(this.themeManager?.isDark() || false);
        }
    }

    /**
     * Fit canvas document size to content bounds
     * DELEGATES to CanvasResizeManager
     */
    public fitCanvasToContent(): void {
        if (this.canvasResizeManager) {
            const success = this.canvasResizeManager.fitToContent();
            if (success) {
                this.drawGrid(this.themeManager?.isDark() || false);
                // Zoom view to show the fitted content
                this.zoomToContent();
                this.saveSessionState();
                // Also trigger figz auto-save if bundle manager exists
                if (this.bundleCanvasManager) {
                    this.bundleCanvasManager.debouncedFigzAutoSave();
                }
            }
        }
    }

    /**
     * Initialize Fabric.js canvas
     */
    public initCanvas(): void {
        const startTime = performance.now();
        console.log('[CanvasManager] Starting canvas initialization...');

        const canvasElement = document.getElementById('vis-canvas') as HTMLCanvasElement;
        if (!canvasElement) {
            console.error('[CanvasManager] Canvas element #vis-canvas not found in DOM');
            return;
        }

        if (typeof fabric === 'undefined') {
            console.error('[CanvasManager] Fabric.js is not loaded!');
            return;
        }

        const defaultWidth = CANVAS_CONSTANTS.MAX_CANVAS_WIDTH;   // 180mm @ 300dpi
        const defaultHeight = CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT; // 240mm @ 300dpi

        // Get initial theme from localStorage (canvas has its own theme, defaults to global)
        const globalTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
        const savedCanvasTheme = localStorage.getItem('canvas-theme') || globalTheme;
        const initialIsDark = savedCanvasTheme === 'dark';
        const initialBgColor = initialIsDark ? '#2a2a2a' : '#ffffff';

        try {
            // Initialize canvas with correct theme from the start
            this.canvas = new fabric.Canvas('vis-canvas', {
                width: defaultWidth,
                height: defaultHeight,
                backgroundColor: initialBgColor,
                selection: true,
                selectionKey: ['ctrlKey', 'shiftKey'],  // Multi-select with Ctrl or Shift
                // Selection styling - make more visible
                selectionColor: 'rgba(100, 150, 255, 0.15)',
                selectionBorderColor: '#4a9eff',
                selectionLineWidth: 2,
            });

            // Set default object selection styling (bolder borders)
            fabric.Object.prototype.set({
                borderColor: '#4a9eff',
                borderScaleFactor: 2,
                cornerColor: '#4a9eff',
                cornerStyle: 'circle',
                cornerSize: 10,
                cornerStrokeColor: '#fff',
                transparentCorners: false,
                padding: 4,
            });

            const canvasCreateTime = performance.now();
            console.log(`[CanvasManager] Fabric.js canvas created in ${(canvasCreateTime - startTime).toFixed(2)}ms (${defaultWidth}×${defaultHeight}px)`);

            // Initialize specialized managers (Phase 1, 2 & 3 refactoring)
            this.gridManager = new GridManager(this.canvas, this.statusBarCallback);
            this.exportManager = new ExportManager(this.canvas, this.statusBarCallback);
            this.undoRedoManager = new UndoRedoManager(this.canvas, this.statusBarCallback);
            this.themeManager = new ThemeManager(this.canvas, initialIsDark, this.statusBarCallback);
            this.zoomPanManager = new ZoomPanManager(this.canvas, this.rulersAreaTransformCallback, this.statusBarCallback);
            this.selectionManager = new SelectionManager(this.canvas, this.statusBarCallback);

            // Phase 3 managers - object manipulation, transforms, and grouping
            this.objectManager = new ObjectManager(
                this.canvas,
                () => this.themeManager?.isDark() || false,
                (img) => this.themeManager?.updateImageForTheme(img),
                (group) => this.processSvgGroupForDarkMode(group),
                () => this.saveUndoState(),
                () => this.saveCanvasContent(),
                this.statusBarCallback
            );
            this.transformManager = new TransformManager(
                this.canvas,
                () => this.saveUndoState(),
                () => this.saveCanvasContent(),
                this.statusBarCallback
            );
            this.groupManager = new GroupManager(
                this.canvas,
                () => this.saveUndoState(),
                () => this.saveCanvasContent(),
                this.statusBarCallback
            );

            // Phase 4 managers - alignment, snapping, and cropping
            this.alignmentManager = new AlignmentManager(
                this.statusBarCallback,
                () => this.saveUndoState(),
                () => this.saveCanvasContent()
            );
            this.alignmentManager.initialize(this.canvas);

            this.snapManager = new SnapManager(
                this.statusBarCallback,
                () => this.getCanvasZoomLevel(),
                () => this.getCanvasPanOffset()
            );
            this.snapManager.initialize(this.canvas);

            this.cropManager = new CropManager(
                this.statusBarCallback,
                () => this.saveUndoState(),
                () => this.saveCanvasContent(),
                () => this.getCanvasZoomLevel(),
                () => this.getCanvasPanOffset()
            );
            this.cropManager.initialize(this.canvas);

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

            // Phase 6 manager - canvas document resize (Ctrl+drag edges)
            this.canvasResizeManager = new CanvasResizeManager(
                this.canvas,
                () => this.getCanvasZoomLevel(),
                () => this.getCanvasPanOffset(),
                () => {
                    // Update rulers when canvas size changes
                    if (this.rulersAreaTransformCallback) {
                        this.rulersAreaTransformCallback();
                    }
                    // Redraw grid if enabled
                    if (this.gridManager?.isGridEnabled()) {
                        this.gridManager.drawGrid(this.themeManager?.isDark() || false);
                    }
                },
                this.statusBarCallback
            );

            // Phase 7 managers - session and bundle management
            this.bundleCanvasManager = new BundleCanvasManager(
                this.canvas,
                this.statusBarCallback,
                (w: number, h: number) => this.setCanvasSizeMm(w, h),
                () => this.clearCanvas(),
                () => this.saveSessionState(),
                (img: any) => this.processNewImageForTheme(img)
            );

            this.sessionManager = new SessionManager(
                this.canvas,
                () => this.getCurrentFigzPath(),
                () => ({
                    owner: this.bundleProjectOwner,
                    slug: this.bundleProjectSlug,
                    figureName: this.bundleFigureName,
                }),
                (path: string) => this.loadFigzBundle(path)
            );

            // Draw initial grid if enabled
            if (this.gridManager.isGridEnabled()) {
                this.gridManager.drawGrid(initialIsDark);
                const gridTime = performance.now();
                console.log(`[CanvasManager] Grid drawn in ${(gridTime - canvasCreateTime).toFixed(2)}ms`);
                console.log(`[CanvasManager] ✅ Total canvas init: ${(gridTime - startTime).toFixed(2)}ms`);
            } else {
                console.log(`[CanvasManager] ✅ Total canvas init: ${(canvasCreateTime - startTime).toFixed(2)}ms`);
            }

            // Restore saved view state
            if (this.zoomPanManager) {
                this.zoomPanManager.restoreViewState();
                // Sync CanvasManager's internal state with ZoomPanManager
                // (wheel handler uses these internal variables directly)
                this.canvasZoomLevel = this.zoomPanManager.getZoomLevel();
                const panOffset = this.zoomPanManager.getPanOffset();
                this.canvasPanOffset.x = panOffset.x;
                this.canvasPanOffset.y = panOffset.y;
            }

            // Save canvas when objects are modified (moved, scaled, rotated)
            this.canvas.on('object:modified', () => {
                this.saveCanvasContent();
            });

            // Also save on selection cleared (in case of deselect after move)
            this.canvas.on('selection:cleared', () => {
                this.saveCanvasContent();
                // Notify properties panel of deselection
                if (this.selectionCallback) {
                    this.selectionCallback(null);
                }
            });

            // Notify properties panel when object selected
            // Also auto-enter element selection mode for plot images with element_bboxes
            this.canvas.on('selection:created', (e: any) => {
                if (this.selectionCallback && e.selected && e.selected.length > 0) {
                    // For multi-selection, pass the ActiveSelection or first object
                    const activeObj = this.canvas?.getActiveObject();
                    this.selectionCallback(activeObj || e.selected[0]);

                    // Only auto-enter element selection for SINGLE selection of plot images/groups
                    if (e.selected.length === 1) {
                        const selected = e.selected[0];
                        // Support both image and group (SVG) types with element_bboxes
                        if ((selected.type === 'image' || selected.type === 'group') && selected.axisMetadata?.element_bboxes) {
                            this.elementSelectionManager?.enterElementSelectionMode(selected, { x: 0, y: 0 });
                        }
                    } else {
                        // Exit element selection mode for multi-selection
                        this.elementSelectionManager?.exitElementSelectionMode();
                    }
                }
            });

            this.canvas.on('selection:updated', (e: any) => {
                if (this.selectionCallback && e.selected && e.selected.length > 0) {
                    // For multi-selection, pass the ActiveSelection or first object
                    const activeObj = this.canvas?.getActiveObject();
                    this.selectionCallback(activeObj || e.selected[0]);

                    // Only auto-enter element selection for SINGLE selection of plot images/groups
                    if (e.selected.length === 1) {
                        const selected = e.selected[0];
                        // Support both image and group (SVG) types with element_bboxes
                        if ((selected.type === 'image' || selected.type === 'group') && selected.axisMetadata?.element_bboxes) {
                            this.elementSelectionManager?.enterElementSelectionMode(selected, { x: 0, y: 0 });
                        } else {
                            this.elementSelectionManager?.exitElementSelectionMode();
                        }
                    } else {
                        // Exit element selection mode for multi-selection
                        this.elementSelectionManager?.exitElementSelectionMode();
                    }
                }
            });

            this.canvas.on('selection:cleared', () => {
                if (this.selectionCallback) {
                    this.selectionCallback(null);
                }
                // Exit element selection mode when deselecting
                this.exitElementSelectionMode();
            });

            // Double-click to enter group (PowerPoint-style sub-element selection)
            // SCIENTIFIC INTEGRITY: Plot images should NOT have individual elements editable
            this.canvas.on('mouse:dblclick', (e: any) => {
                const target = e.target;
                if (target && target.type === 'group') {
                    // Check if this is a scientific plot (has data attached)
                    // Plot images should NOT be editable at element level for scientific integrity
                    const isPlotImage = target.plotInfo || target.csvData || target.axisMetadata;
                    if (isPlotImage) {
                        if (this.statusBarCallback) {
                            this.statusBarCallback('Plot data cannot be edited (scientific integrity)');
                        }
                        console.log('[CanvasManager] Blocked group edit for plot image (scientific integrity)');
                        return;
                    }
                    // Only allow group edit mode for non-plot groups (e.g., imported SVGs, shapes)
                    this.enterGroupEditMode(target);
                }
                // Note: Element selection mode is now auto-entered on selection
            });

            // Snap to other objects while moving (PowerPoint-style)
            // Throttled using requestAnimationFrame for performance
            this.canvas.on('object:moving', (e: any) => {
                if (this.snapEnabled) {
                    this.pendingMovingTarget = e.target;
                    if (!this.objectMovingThrottleFrame) {
                        this.objectMovingThrottleFrame = requestAnimationFrame(() => {
                            if (this.pendingMovingTarget) {
                                this.handleObjectSnap(this.pendingMovingTarget);
                            }
                            this.objectMovingThrottleFrame = null;
                        });
                    }
                }
            });

            // Clear alignment guidelines when object stops moving
            this.canvas.on('object:modified', (e: any) => {
                this.clearAlignmentLines();
                this.saveCanvasContent();

                // Check if object was scaled and needs re-render
                const obj = e.target;
                if (obj && (obj.scaleX !== 1 || obj.scaleY !== 1)) {
                    // Notify for re-render if object has plot data
                    if (obj.csvData && obj.plotInfo && this.onObjectResizedCallback) {
                        const newWidth = Math.round(obj.width * obj.scaleX);
                        const newHeight = Math.round(obj.height * obj.scaleY);
                        this.onObjectResizedCallback(obj, newWidth, newHeight);
                    }
                }

                // Update properties panel if selection callback exists
                if (this.selectionCallback && obj) {
                    this.selectionCallback(obj);
                }

                // Trigger figz auto-save for bundle panels
                if (obj && obj.isBundlePanel) {
                    this.debouncedFigzAutoSave();
                }
            });

            // Clear guidelines on mouse up
            this.canvas.on('mouse:up', () => {
                this.clearAlignmentLines();
                // Reset snap state when mouse is released
                this.lastSnapX = null;
                this.lastSnapY = null;
            });

            // Setup hover tooltip for pltz bundles
            this.setupHoverTooltip();

            // Setup Alt key tracking for fine adjustment mode
            this.setupAltKeyTracking();
        } catch (error) {
            console.error('[CanvasManager] Error initializing canvas:', error);
        }
    }

    /**
     * Enter group edit mode - allows selecting elements inside a group
     * Double-click on group to enter, click outside to exit
     * DELEGATES to GroupManager
     */
    private enterGroupEditMode(group: any): void {
        if (this.groupManager) {
            this.groupManager.enterGroupEditMode(group);
        }
    }

    /**
     * Exit group edit mode - regroup the objects
     * DELEGATES to GroupManager
     */
    public exitGroupEditMode(): void {
        if (this.groupManager) {
            this.groupManager.exitGroupEditMode();
        }
    }

    /**
     * Draw grid using pre-rendered static SVG files
     * DELEGATES to GridManager
     */
    public drawGrid(isDark: boolean = false): void {
        if (this.gridManager) {
            this.gridManager.drawGrid(isDark);
        }
    }

    /**
     * Clear grid background from canvas
     * DELEGATES to GridManager
     */
    public clearGrid(): void {
        if (this.gridManager) {
            this.gridManager.clearGrid();
        }
    }

    /**
     * Toggle grid visibility
     * DELEGATES to GridManager
     */
    public toggleGrid(): void {
        if (this.gridManager) {
            this.gridManager.toggleGrid();
        }
    }

    /**
     * Update canvas theme
     */
    public updateCanvasTheme(isDark: boolean): void {
        if (!this.themeManager) return;

        // Create callback for grid redraw
        const gridRedrawCallback = () => {
            if (this.gridManager && this.gridManager.isGridEnabled()) {
                this.gridManager.drawGrid(isDark);
            }
        };

        this.themeManager.updateCanvasTheme(isDark, gridRedrawCallback);
    }

    /**
     * Process SVG group paths for dark mode display
     * DELEGATES to ThemeManager
     */
    public processSvgGroupForDarkMode(group: any): void {
        if (this.themeManager) {
            this.themeManager.processSvgGroupForDarkMode(group);
        }
    }

    /**
     * Restore SVG group paths to original colors (for light mode)
     * DELEGATES to ThemeManager
     */
    public restoreSvgGroupColors(group: any): void {
        if (this.themeManager) {
            this.themeManager.restoreSvgGroupColors(group);
        }
    }

    /**
     * Process a newly added image for current theme (dark mode conversion)
     * DELEGATES to ThemeManager
     */
    public processNewImageForTheme(img: any): void {
        if (this.themeManager) {
            this.themeManager.processNewImage(img);
        }
    }

    /**
     * Reprocess all SVG groups when theme changes
     * Uses remove/re-add strategy to force complete re-render
     */
    public reprocessAllSvgGroupsForTheme(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        const groupsToProcess: any[] = [];

        // Collect all groups first (avoid modifying while iterating)
        objects.forEach((obj: any) => {
            if (obj.type === 'group') {
                groupsToProcess.push(obj);
            }
        });

        if (groupsToProcess.length === 0) return;

        // Process each group by removing and re-adding to force re-render
        groupsToProcess.forEach((group: any) => {
            // Store position and other properties
            const index = this.canvas!.getObjects().indexOf(group);

            // Modify colors on the children
            if (this.isDarkMode) {
                this.processSvgGroupForDarkMode(group);
            } else {
                this.restoreSvgGroupColors(group);
            }

            // Remove and re-add the group to force complete re-render
            this.canvas!.remove(group);

            // Disable object caching for SVG groups to ensure child updates are visible
            group.objectCaching = false;

            // Re-add at the same position
            if (index >= 0 && index < this.canvas!.getObjects().length) {
                this.canvas!.insertAt(index, group);
            } else {
                this.canvas!.add(group);
            }
        });

        this.canvas.renderAll();
        console.log(`[CanvasManager] Reprocessed ${groupsToProcess.length} SVG groups for ${this.isDarkMode ? 'dark' : 'light'} mode`);
    }

    /**
     * Save undo state
     * DELEGATES to UndoRedoManager
     */
    public saveUndoState(): void {
        if (this.undoRedoManager) {
            this.undoRedoManager.saveUndoState();
        }
    }

    /**
     * Undo last action
     * DELEGATES to UndoRedoManager
     */
    public undo(): void {
        if (this.undoRedoManager) {
            this.undoRedoManager.undo();
        }
    }

    /**
     * Redo last undone action
     * DELEGATES to UndoRedoManager
     */
    public redo(): void {
        if (this.undoRedoManager) {
            this.undoRedoManager.redo();
        }
    }


    // View clipboard for copy/paste view (axis limits, crop)
    private viewClipboard: {
        cropX?: number;
        cropY?: number;
        width?: number;
        height?: number;
        scaleX?: number;
        scaleY?: number;
    } | null = null;

    /**
     * Copy active object to clipboard
     * DELEGATES to SelectionManager
     */
    public copyActiveObject(): void {
        if (this.selectionManager) {
            this.selectionManager.copyActiveObject();
        }
    }

    /**
     * Paste object from clipboard
     * DELEGATES to SelectionManager
     */
    public pasteObject(): void {
        if (this.selectionManager) {
            this.selectionManager.pasteObject(
                () => this.saveUndoState(),
                () => this.saveCanvasContent()
            );
        }
    }

    // Context menu callbacks
    private contextMenuCallbacks: {
        delete?: () => void;
        duplicate?: () => void;
        bringToFront?: () => void;
        sendToBack?: () => void;
    } = {};

    /**
     * Set context menu callbacks
     */
    public setContextMenuCallbacks(callbacks: typeof this.contextMenuCallbacks): void {
        this.contextMenuCallbacks = callbacks;
    }

    /**
     * Setup canvas zoom/pan events
     */
    public setupCanvasEvents(): void {
        const canvasContainer = document.getElementById('canvas-container');
        if (!canvasContainer || !this.canvas) {
            console.warn('[CanvasManager] Canvas container or Fabric.js canvas not found');
            return;
        }

        // Setup context menu (delegate to ContextMenuManager)
        if (this.contextMenuManager) {
            this.contextMenuManager.setupContextMenu(canvasContainer);
        }

        // Setup canvas resize (Ctrl+drag from edges)
        if (this.canvasResizeManager) {
            this.canvasResizeManager.setupResizeListeners(canvasContainer);
        }

        // Listen for canvas theme changes from keyboard shortcut (Alt+T)
        document.addEventListener('canvas-theme-changed', ((e: CustomEvent) => {
            this.updateCanvasTheme(e.detail.isDark);
        }) as EventListener);

        // Track right-click pan to distinguish from context menu
        let rightClickPanStartPoint: { x: number; y: number } | null = null;

        // Track right-click double-click for canvas reset
        let lastRightClickTime = 0;
        const DOUBLE_CLICK_THRESHOLD = 300; // ms

        // Mouse down - Check for panning or zoom dragging
        canvasContainer.addEventListener('mousedown', (e: MouseEvent) => {
            console.log(`[CanvasManager] mousedown: button=${e.button}, ctrlKey=${e.ctrlKey}, metaKey=${e.metaKey}`);
            if (e.button === 1 || (e as any).spaceKey) {
                if (e.ctrlKey || e.metaKey) {
                    // Ctrl + middle mouse = zoom drag mode
                    this.canvasIsZoomDragging = true;
                    this.canvasZoomDragStartY = e.clientY;
                    this.canvasZoomDragStartLevel = this.canvasZoomLevel;
                    canvasContainer.style.cursor = 'ns-resize';
                    e.preventDefault();
                    console.log(`[CanvasManager] Canvas zoom drag mode started, startLevel=${this.canvasZoomLevel}`);
                } else {
                    // Middle mouse without Ctrl = pan mode
                    this.canvasIsPanning = true;
                    this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
                    canvasContainer.style.cursor = 'grabbing';
                    e.preventDefault();
                    console.log('[CanvasManager] Canvas pan mode started');
                }
            } else if (e.button === 2) {
                // Right-click - check for double-click to reset canvas position
                const now = Date.now();
                if (now - lastRightClickTime < DOUBLE_CLICK_THRESHOLD) {
                    // Double right-click - reset canvas position to origin
                    this.canvasPanOffset.x = 0;
                    this.canvasPanOffset.y = 0;
                    this.updateCanvasTransform();
                    if (this.rulersAreaTransformCallback) {
                        this.rulersAreaTransformCallback();
                    }
                    this.saveViewState();
                    this.rightClickPanOccurred = true; // Suppress context menu
                    console.log('[CanvasManager] Canvas position reset to origin (right double-click)');
                    lastRightClickTime = 0; // Reset to prevent triple-click
                } else {
                    // Single right-click - prepare for potential pan
                    rightClickPanStartPoint = { x: e.clientX, y: e.clientY };
                    this.rightClickPanOccurred = false;
                    lastRightClickTime = now;
                }
            }
        });

        // Mouse move - Handle panning or zoom dragging
        canvasContainer.addEventListener('mousemove', (e: MouseEvent) => {
            // Handle right-click pan initiation (detect movement threshold)
            if (rightClickPanStartPoint && !this.canvasIsPanning) {
                const dx = e.clientX - rightClickPanStartPoint.x;
                const dy = e.clientY - rightClickPanStartPoint.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                // Start panning if moved more than 3 pixels
                if (distance > 3) {
                    this.rightClickPanOccurred = true;
                    this.canvasIsPanning = true;
                    this.canvasPanStartPoint = rightClickPanStartPoint;
                    canvasContainer.style.cursor = 'grabbing';
                    console.log('[CanvasManager] Canvas pan mode started (right-click)');
                }
            }

            if (this.canvasIsZoomDragging) {
                // Ctrl+drag zoom: vertical movement changes zoom
                const deltaY = e.clientY - this.canvasZoomDragStartY;
                const zoomFactor = 1 - (deltaY * 0.005); // Drag up = zoom in, drag down = zoom out
                let newZoom = this.canvasZoomDragStartLevel * zoomFactor;

                // Clamp zoom level
                if (newZoom > 5) newZoom = 5;
                if (newZoom < 0.1) newZoom = 0.1;

                this.canvasZoomLevel = newZoom;

                // Throttle updates using requestAnimationFrame
                if (!this.pendingDragUpdate) {
                    this.pendingDragUpdate = true;
                    this.canvasDragThrottleFrame = requestAnimationFrame(() => {
                        this.updateCanvasTransform();
                        if (this.rulersAreaTransformCallback) {
                            this.rulersAreaTransformCallback();
                        }
                        this.updateCanvasZoomDisplay();
                        this.pendingDragUpdate = false;
                    });
                }
            } else if (this.canvasIsPanning && this.canvasPanStartPoint) {
                let deltaX = e.clientX - this.canvasPanStartPoint.x;
                let deltaY = e.clientY - this.canvasPanStartPoint.y;

                if (e.altKey) {
                    deltaX *= 0.1;
                    deltaY *= 0.1;
                }

                // Accumulate pan delta for throttled update
                if (!this.pendingPanUpdate) {
                    this.pendingPanUpdate = { x: deltaX, y: deltaY };
                } else {
                    this.pendingPanUpdate.x += deltaX;
                    this.pendingPanUpdate.y += deltaY;
                }

                // Throttle pan updates using requestAnimationFrame
                if (!this.panThrottleFrame) {
                    this.panThrottleFrame = requestAnimationFrame(() => {
                        if (this.pendingPanUpdate) {
                            this.canvasPanOffset.x += this.pendingPanUpdate.x;
                            this.canvasPanOffset.y += this.pendingPanUpdate.y;

                            this.updateCanvasTransform();

                            if (this.rulersAreaTransformCallback) {
                                this.rulersAreaTransformCallback();
                            }

                            this.pendingPanUpdate = null;
                        }
                        this.panThrottleFrame = null;
                    });
                }

                this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
            }
        });

        // Mouse up - Reset panning or zoom dragging
        canvasContainer.addEventListener('mouseup', (e: MouseEvent) => {
            // Reset right-click pan tracking
            if (e.button === 2) {
                rightClickPanStartPoint = null;
            }

            if (this.canvasIsZoomDragging) {
                this.canvasIsZoomDragging = false;
                canvasContainer.style.cursor = 'default';
                this.saveViewState(); // Save after zoom drag ends
                console.log('[CanvasManager] Canvas zoom drag mode ended');
            }
            if (this.canvasIsPanning) {
                this.canvasIsPanning = false;
                this.canvasPanStartPoint = null;
                canvasContainer.style.cursor = 'default';
                this.saveViewState(); // Save after pan ends
                console.log('[CanvasManager] Canvas pan mode ended');
            }

            // Cancel any pending throttled updates
            if (this.canvasDragThrottleFrame !== null) {
                cancelAnimationFrame(this.canvasDragThrottleFrame);
                this.canvasDragThrottleFrame = null;
                this.pendingDragUpdate = false;
            }
            if (this.panThrottleFrame !== null) {
                cancelAnimationFrame(this.panThrottleFrame);
                this.panThrottleFrame = null;
                this.pendingPanUpdate = null;
            }
            if (this.objectMovingThrottleFrame !== null) {
                cancelAnimationFrame(this.objectMovingThrottleFrame);
                this.objectMovingThrottleFrame = null;
                this.pendingMovingTarget = null;
            }
        });

        // Prevent browser's native Ctrl+wheel zoom on canvas area
        // Must be at document level with capture to intercept before browser
        document.addEventListener('wheel', (e: WheelEvent) => {
            if ((e.ctrlKey || e.metaKey) && canvasContainer.contains(e.target as Node)) {
                e.preventDefault();
            }
        }, { passive: false, capture: true });

        // Wheel event - Zoom with Ctrl, Pan without Ctrl
        canvasContainer.addEventListener('wheel', (e: WheelEvent) => {
            e.preventDefault();
            e.stopPropagation();

            if (e.ctrlKey || e.metaKey) {
                // Ctrl+Wheel = Zoom
                this.canvasAccumulatedZoomDelta += e.deltaY;

                const rect = canvasContainer.getBoundingClientRect();
                this.canvasLastZoomMousePos.x = e.clientX - rect.left;
                this.canvasLastZoomMousePos.y = e.clientY - rect.top;

                if (!this.canvasWheelThrottleFrame) {
                    this.canvasWheelThrottleFrame = requestAnimationFrame(() => {
                        const oldZoom = this.canvasZoomLevel;
                        let newZoom = oldZoom * (0.999 ** this.canvasAccumulatedZoomDelta);

                        if (newZoom > 5) newZoom = 5;
                        if (newZoom < 0.1) newZoom = 0.1;

                        this.canvasZoomLevel = newZoom;

                        const zoomRatio = newZoom / oldZoom;
                        const mouseX = this.canvasLastZoomMousePos.x;
                        const mouseY = this.canvasLastZoomMousePos.y;
                        this.canvasPanOffset.x = mouseX - (mouseX - this.canvasPanOffset.x) * zoomRatio;
                        this.canvasPanOffset.y = mouseY - (mouseY - this.canvasPanOffset.y) * zoomRatio;

                        this.updateCanvasTransform();
                        if (this.rulersAreaTransformCallback) {
                            this.rulersAreaTransformCallback();
                        }
                        this.updateCanvasZoomDisplay();

                        this.canvasAccumulatedZoomDelta = 0;
                        this.canvasWheelThrottleFrame = null;
                    });
                }
            } else {
                // Regular wheel = Pan
                this.canvasAccumulatedPanDelta.x += e.deltaX;
                this.canvasAccumulatedPanDelta.y += e.deltaY;

                if (!this.canvasWheelThrottleFrame) {
                    this.canvasWheelThrottleFrame = requestAnimationFrame(() => {
                        this.canvasPanOffset.x -= this.canvasAccumulatedPanDelta.x;
                        this.canvasPanOffset.y -= this.canvasAccumulatedPanDelta.y;

                        this.updateCanvasTransform();
                        if (this.rulersAreaTransformCallback) {
                            this.rulersAreaTransformCallback();
                        }

                        this.canvasAccumulatedPanDelta.x = 0;
                        this.canvasAccumulatedPanDelta.y = 0;
                        this.canvasWheelThrottleFrame = null;
                    });
                }
            }
        }, { passive: false });

        console.log('[CanvasManager] Canvas events (zoom/pan) initialized');
    }

    /**
     * Update canvas transform (keep at identity, all zoom/pan via CSS)
     */
    public updateCanvasTransform(): void {
        if (!this.canvas) return;

        // Keep Fabric.js canvas at identity transform
        // All zoom/pan is handled by CSS transform on .vis-rulers-area parent
        this.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);

        // Update CSS transform on rulers area
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (rulersArea) {
            rulersArea.style.transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
            rulersArea.style.transformOrigin = '0 0';
        }

        // Save state to localStorage for persistence
        this.saveViewState();
    }

    /**
     * Save view state to localStorage (debounced)
     */
    private saveViewStateTimer: ReturnType<typeof setTimeout> | null = null;
    private saveViewState(): void {
        if (this.saveViewStateTimer) {
            clearTimeout(this.saveViewStateTimer);
        }
        this.saveViewStateTimer = setTimeout(() => {
            const state = {
                zoom: this.canvasZoomLevel,
                panX: this.canvasPanOffset.x,
                panY: this.canvasPanOffset.y,
            };
            localStorage.setItem('scitex-vis-viewstate', JSON.stringify(state));
            console.log('[CanvasManager] 💾 Saved view state:', state);
        }, 200); // Debounce 200ms
    }

    /**
     * Restore view state from localStorage
     */
    public restoreViewState(): void {
        try {
            const saved = localStorage.getItem('scitex-vis-viewstate');
            console.log('[CanvasManager] 📂 Raw localStorage value:', saved);
            if (saved) {
                const state = JSON.parse(saved);
                console.log('[CanvasManager] 📂 Parsed state:', state);
                if (state.zoom !== undefined) this.canvasZoomLevel = state.zoom;
                if (state.panX !== undefined) this.canvasPanOffset.x = state.panX;
                if (state.panY !== undefined) this.canvasPanOffset.y = state.panY;
                console.log('[CanvasManager] 📂 Applied to internal state - zoom:', this.canvasZoomLevel, 'panX:', this.canvasPanOffset.x, 'panY:', this.canvasPanOffset.y);
                // Apply the restored transform to DOM elements (without triggering save)
                this.applyTransformWithoutSave();
            } else {
                console.log('[CanvasManager] 📂 No saved state found in localStorage');
            }
        } catch (err) {
            console.warn('[CanvasManager] Failed to restore view state:', err);
        }
    }

    /**
     * Apply CSS transform without triggering save (used during restore)
     */
    private applyTransformWithoutSave(): void {
        if (!this.canvas) {
            console.warn('[CanvasManager] ⚠️ applyTransformWithoutSave: canvas not available');
            return;
        }

        // Keep Fabric.js canvas at identity transform
        this.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);

        // Update CSS transform on rulers area
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (rulersArea) {
            const transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
            rulersArea.style.transform = transform;
            rulersArea.style.transformOrigin = '0 0';
            console.log('[CanvasManager] ✅ Applied CSS transform:', transform);
        } else {
            console.warn('[CanvasManager] ⚠️ .vis-rulers-area not found in DOM');
        }

        // Update rulers callback if set
        if (this.rulersAreaTransformCallback) {
            this.rulersAreaTransformCallback();
        }
    }

    /**
     * Save canvas content to localStorage (debounced)
     */
    private saveContentDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    public saveCanvasContent(): void {
        if (this.saveContentDebounceTimer) {
            clearTimeout(this.saveContentDebounceTimer);
        }
        this.saveContentDebounceTimer = setTimeout(() => {
            this.saveCanvasContentImmediate();
        }, 1000); // Save after 1 second of no changes
    }

    private saveCanvasContentImmediate(): void {
        if (!this.canvas) return;
        try {
            const json = this.canvas.toJSON(['name', 'id', 'axisMetadata', 'plotInfo', 'originalWidth', 'originalHeight']);
            // Use custom serializer to preserve tiny scale values (prevent 0.0001 from becoming 0)
            const jsonString = this.serializeWithPrecision(json);
            localStorage.setItem('scitex-vis-canvas', jsonString);
            console.log('[CanvasManager] Saved canvas content to localStorage');
        } catch (err) {
            console.warn('[CanvasManager] Failed to save canvas:', err);
        }
    }

    /**
     * Serialize JSON with high precision for small numbers
     * JSON.stringify rounds 0.0001 to 0, losing text glyph scale data
     */
    private serializeWithPrecision(obj: any): string {
        return JSON.stringify(obj, (key, value) => {
            // Preserve precision for scale values and other small numbers
            if (typeof value === 'number' && value !== 0) {
                // If it's a very small number, convert to string with high precision
                // Then parse it back to ensure valid number representation
                if (Math.abs(value) < 0.001 && Math.abs(value) > 0) {
                    // Store as scientific notation string wrapped in special marker
                    return { __tinyNum__: value.toExponential(10) };
                }
            }
            return value;
        });
    }

    /**
     * Restore canvas content from localStorage
     * Returns the restored objects so metadata can be loaded if needed
     */
    public restoreCanvasContent(): Promise<any[]> {
        return new Promise((resolve) => {
            if (!this.canvas) {
                resolve([]);
                return;
            }
            try {
                const saved = localStorage.getItem('scitex-vis-canvas');
                if (saved) {
                    // Parse with custom reviver to restore tiny numbers
                    const json = this.parseWithPrecision(saved);

                    // Fallback: fix any remaining zero-scale paths (from old saves)
                    this.fixZeroScalePathsInJson(json);

                    this.canvas.loadFromJSON(json, () => {
                        // Apply dark mode color transformation to restored SVG groups
                        if (this.isDarkMode) {
                            this.reprocessAllSvgGroupsForTheme();
                        }
                        this.canvas!.renderAll();
                        const objects = this.canvas!.getObjects();
                        console.log(`[CanvasManager] Restored canvas content (${objects.length} objects)`);
                        resolve(objects);
                    });
                } else {
                    resolve([]);
                }
            } catch (err) {
                console.warn('[CanvasManager] Failed to restore canvas:', err);
                resolve([]);
            }
        });
    }

    /**
     * Parse JSON with restoration of tiny numbers preserved by serializeWithPrecision
     */
    private parseWithPrecision(jsonString: string): any {
        const parsed = JSON.parse(jsonString);

        // Recursively restore __tinyNum__ markers
        const restoreTinyNumbers = (obj: any): any => {
            if (obj === null || typeof obj !== 'object') {
                return obj;
            }

            // Check if this is a tiny number marker
            if (obj.__tinyNum__ !== undefined) {
                return parseFloat(obj.__tinyNum__);
            }

            // Handle arrays
            if (Array.isArray(obj)) {
                return obj.map(restoreTinyNumbers);
            }

            // Handle objects
            const result: any = {};
            for (const key in obj) {
                if (Object.prototype.hasOwnProperty.call(obj, key)) {
                    result[key] = restoreTinyNumbers(obj[key]);
                }
            }
            return result;
        };

        return restoreTinyNumbers(parsed);
    }

    /**
     * Fix paths with zero scale in JSON before loading
     * Matplotlib SVG text glyphs have tiny scale values (e.g., 0.00146) that get rounded to 0
     * These paths have large width/height (glyph definition space ~3000x4000)
     *
     * The standard matplotlib glyph scale is approximately 0.00145833 (1/685.71)
     * This renders glyphs at their intended size (~7px for typical 4600-height glyphs)
     */
    private fixZeroScalePathsInJson(json: any): void {
        if (!json?.objects) return;

        let fixedCount = 0;

        // Standard matplotlib glyph scale factor
        // This is the typical scale used by matplotlib SVG text rendering
        // Calculated as: intended_font_size_px / glyph_coordinate_space
        // Typical: ~7px / 4800 ≈ 0.00145833
        const MATPLOTLIB_GLYPH_SCALE = 0.0014583333333333334;

        const fixPathsInObject = (obj: any) => {
            if (obj.type === 'path') {
                // Check if this is a zero-scale path with large dimensions (text glyph)
                const hasZeroScale = (obj.scaleX === 0 || obj.scaleY === 0);
                const hasLargeDimensions = (obj.width > 500 || obj.height > 500);

                if (hasZeroScale && hasLargeDimensions) {
                    // Use the standard matplotlib scale for both axes
                    // This maintains the correct aspect ratio and text size
                    if (obj.scaleX === 0) obj.scaleX = MATPLOTLIB_GLYPH_SCALE;
                    if (obj.scaleY === 0) obj.scaleY = MATPLOTLIB_GLYPH_SCALE;
                    fixedCount++;
                }
            }

            // Recursively process group children
            if (obj.type === 'group' && obj.objects) {
                obj.objects.forEach(fixPathsInObject);
            }
        };

        json.objects.forEach(fixPathsInObject);

        if (fixedCount > 0) {
            console.log(`[CanvasManager] Fixed ${fixedCount} zero-scale paths (text glyphs)`);
        }
    }

    // ========================================
    // SESSION STATE PERSISTENCE (Page Refresh)
    // ========================================

    private static SESSION_STORAGE_KEY = 'scitex-vis-session';

    /**
     * Save session state to localStorage for page refresh recovery
     * Includes: figz path, project context, panels info
     */
    public saveSessionState(): void {
        try {
            const sessionState = {
                timestamp: Date.now(),
                figzPath: this.currentFigzPath,
                projectOwner: this.bundleProjectOwner,
                projectSlug: this.bundleProjectSlug,
                figureName: this.bundleFigureName,
                canvasSize: this.canvas ? {
                    width: this.canvas.getWidth(),
                    height: this.canvas.getHeight(),
                } : null,
                panels: this.getBundlePanelsForSession(),
            };

            localStorage.setItem(CanvasManager.SESSION_STORAGE_KEY, JSON.stringify(sessionState));
            console.log('[CanvasManager] Session state saved');
        } catch (err) {
            console.warn('[CanvasManager] Failed to save session state:', err);
        }
    }

    /**
     * Get panel info for session storage (lightweight version of getBundlePanels)
     */
    private getBundlePanelsForSession(): any[] {
        if (!this.canvas) return [];

        const panels: any[] = [];
        const objects = this.canvas.getObjects();

        for (const obj of objects) {
            const plotInfo = (obj as any).plotInfo;
            if (plotInfo?.bundlePath) {
                panels.push({
                    label: plotInfo.panelLabel || 'A',
                    pltzPath: plotInfo.bundlePath,
                    position: {
                        left: obj.left,
                        top: obj.top,
                    },
                    size: {
                        width: obj.getScaledWidth(),
                        height: obj.getScaledHeight(),
                    },
                });
            }
        }

        return panels;
    }

    /**
     * Restore session state from localStorage
     * Returns the session state if found and valid, null otherwise
     */
    public getSessionState(): {
        figzPath: string | null;
        projectOwner: string;
        projectSlug: string;
        figureName: string;
        canvasSize: { width: number; height: number } | null;
        panels: any[];
        timestamp: number;
    } | null {
        try {
            const saved = localStorage.getItem(CanvasManager.SESSION_STORAGE_KEY);
            if (!saved) return null;

            const state = JSON.parse(saved);

            // Check if session is recent (within 24 hours)
            const maxAge = 24 * 60 * 60 * 1000; // 24 hours
            if (Date.now() - state.timestamp > maxAge) {
                console.log('[CanvasManager] Session state expired, clearing');
                this.clearSessionState();
                return null;
            }

            return state;
        } catch (err) {
            console.warn('[CanvasManager] Failed to restore session state:', err);
            return null;
        }
    }

    /**
     * Clear session state from localStorage
     */
    public clearSessionState(): void {
        localStorage.removeItem(CanvasManager.SESSION_STORAGE_KEY);
        console.log('[CanvasManager] Session state cleared');
    }

    /**
     * Restore session - load figz bundle from saved state
     * Returns true if session was restored, false otherwise
     */
    public async restoreSession(): Promise<boolean> {
        const session = this.getSessionState();
        if (!session) {
            console.log('[CanvasManager] No valid session to restore');
            return false;
        }

        console.log('[CanvasManager] Restoring session:', session);

        // Restore project context
        if (session.projectOwner && session.projectSlug) {
            this.bundleProjectOwner = session.projectOwner;
            this.bundleProjectSlug = session.projectSlug;
        }
        if (session.figureName) {
            this.bundleFigureName = session.figureName;
        }

        // If we have a figz path, reload it
        if (session.figzPath) {
            try {
                await this.loadFigzBundle(session.figzPath);
                console.log('[CanvasManager] Session restored from figz:', session.figzPath);
                return true;
            } catch (err) {
                console.warn('[CanvasManager] Failed to load figz from session:', err);
            }
        }

        // Fallback: restore canvas content from localStorage (panels without figz)
        if (session.panels && session.panels.length > 0) {
            console.log('[CanvasManager] Restoring panels from session...');
            // Canvas content is restored via restoreCanvasContent() in SigmaEditor
            return true;
        }

        return false;
    }

    /**
     * Setup beforeunload handler to save state before page close/refresh
     */
    public setupBeforeUnloadHandler(): void {
        window.addEventListener('beforeunload', () => {
            // Save session state synchronously
            this.saveSessionStateSync();
        });

        // Also save periodically (every 30 seconds)
        setInterval(() => {
            this.saveSessionState();
        }, 30000);

        console.log('[CanvasManager] Page refresh handler installed');
    }

    /**
     * Synchronous version of saveSessionState for beforeunload
     * Uses localStorage.setItem which is synchronous
     */
    private saveSessionStateSync(): void {
        try {
            const sessionState = {
                timestamp: Date.now(),
                figzPath: this.currentFigzPath,
                projectOwner: this.bundleProjectOwner,
                projectSlug: this.bundleProjectSlug,
                figureName: this.bundleFigureName,
                canvasSize: this.canvas ? {
                    width: this.canvas.getWidth(),
                    height: this.canvas.getHeight(),
                } : null,
                panels: this.getBundlePanelsForSession(),
            };

            localStorage.setItem(CanvasManager.SESSION_STORAGE_KEY, JSON.stringify(sessionState));
        } catch (err) {
            // Silent fail for beforeunload
        }
    }

    /**
     * Update canvas zoom display
     */
    private updateCanvasZoomDisplay(): void {
        if (this.statusBarCallback) {
            this.statusBarCallback(`Canvas Zoom: ${Math.round(this.canvasZoomLevel * 100)}%`);
        }
        console.log(`[CanvasManager] Canvas zoom level: ${Math.round(this.canvasZoomLevel * 100)}%`);
    }

    /**
     * Zoom in
     */
    public zoomIn(): void {
        this.canvasZoomLevel = Math.min(this.canvasZoomLevel * 1.2, 5.0);
        this.applyZoom();
        console.log('[CanvasManager] Zoomed in - Canvas:', Math.round(this.canvasZoomLevel * 100) + '%');
    }

    /**
     * Zoom out
     */
    public zoomOut(): void {
        this.canvasZoomLevel = Math.max(this.canvasZoomLevel / 1.2, 0.1);
        this.applyZoom();
        console.log('[CanvasManager] Zoomed out - Canvas:', Math.round(this.canvasZoomLevel * 100) + '%');
    }

    /**
     * Zoom to fit - fits full canvas (180mm × 240mm) within viewport
     */
    public zoomToFit(): void {
        const canvasContainer = document.getElementById('canvas-container');
        if (!canvasContainer) {
            console.warn('[CanvasManager] canvas-container not found, using default zoom');
            this.canvasZoomLevel = 0.22;  // Default to 22% to fit full canvas
            this.canvasPanOffset = { x: 0, y: 0 };
            this.applyZoom();
            return;
        }

        // Get container dimensions (with padding for rulers)
        const containerWidth = canvasContainer.clientWidth - 40;  // Account for rulers
        const containerHeight = canvasContainer.clientHeight - 40;

        console.log(`[CanvasManager] Container dimensions: ${containerWidth}×${containerHeight}px`);

        // Full canvas: 180mm width × 240mm height at 300dpi
        const canvasWidth = CANVAS_CONSTANTS.MAX_CANVAS_WIDTH;   // 2126px (180mm)
        const canvasHeight = CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT; // 2835px (240mm)

        console.log(`[CanvasManager] Canvas dimensions: ${canvasWidth}×${canvasHeight}px`);

        // Calculate zoom to fit entire canvas
        const zoomX = containerWidth / canvasWidth;
        const zoomY = containerHeight / canvasHeight;

        // Use minimum zoom to fit, but ensure at least 10% minimum
        this.canvasZoomLevel = Math.max(Math.min(zoomX, zoomY, 1.0), 0.1);

        console.log(`[CanvasManager] Calculated zoom: zoomX=${zoomX.toFixed(3)}, zoomY=${zoomY.toFixed(3)}, final=${this.canvasZoomLevel.toFixed(3)}`);

        // Reset pan offset
        this.canvasPanOffset = { x: 0, y: 0 };

        this.applyZoom();
        console.log(`[CanvasManager] Canvas zoomed to fit: ${Math.round(this.canvasZoomLevel * 100)}% (container: ${containerWidth}×${containerHeight}px)`);
    }

    /**
     * Zoom to fit content - calculates bounding box of all objects and fits view
     * DELEGATES to ZoomPanManager
     */
    public zoomToContent(): void {
        if (this.zoomPanManager) {
            this.zoomPanManager.zoomToContent();
        } else {
            // Fallback: use local implementation
            this.zoomToFit();
        }
    }

    /**
     * Apply zoom
     */
    private applyZoom(): void {
        this.updateCanvasTransform();
        if (this.rulersAreaTransformCallback) {
            this.rulersAreaTransformCallback();
        }
        if (this.statusBarCallback) {
            this.statusBarCallback(`Canvas: ${Math.round(this.canvasZoomLevel * 100)}%`);
        }
    }

    /**
     * Add image to canvas from URL or data URL
     * Automatically extracts embedded scitex metadata for axis snap/align
     */
    public addImage(src: string, options: any = {}): Promise<any> {
        if (this.objectManager) {
            return this.objectManager.addImage(src, options);
        }
        return Promise.reject("ObjectManager not initialized");
    }


    /**
     * Add image from base64 data
     */
    public async addImageFromBase64(base64Data: string, options: Parameters<typeof this.addImage>[1] = {}): Promise<any> {
        // Ensure it's a valid data URL
        const dataUrl = base64Data.startsWith('data:')
            ? base64Data
            : `data:image/png;base64,${base64Data}`;

        return this.addImage(dataUrl, options);
    }

    /**
     * Add SVG to canvas with selectable sub-elements
     * This allows selecting individual parts of a figure (axes, legend, title, etc.)
     */
    public addSvg(svgString: string, options: any = {}): Promise<any> {
        if (this.objectManager) {
            return this.objectManager.addSvg(svgString, options);
        }
        return Promise.reject("ObjectManager not initialized");
    }

    /**
     * Add SVG from URL with selectable sub-elements
     */
    public addSvgFromUrl(url: string, options: Parameters<typeof this.addSvg>[1] = {}): Promise<any> {
        return new Promise((resolve, reject) => {
            fetch(url)
                .then(response => response.text())
                .then(svgString => {
                    this.addSvg(svgString, options).then(resolve).catch(reject);
                })
                .catch(reject);
        });
    }

    /**
     * Clear all objects from canvas (except grid)
     */
    public clearCanvas(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            // Don't remove grid-related objects
            if (obj.id !== 'grid-line' && obj.id !== 'column-guide') {
                this.canvas!.remove(obj);
            }
        });

        this.canvas.renderAll();

        if (this.statusBarCallback) {
            this.statusBarCallback('Canvas cleared');
        }
        console.log('[CanvasManager] Canvas cleared');
    }

    // =========================================================================
    // Bundle Integration (pltz/figz) - Canvas backed by SciTeX bundles
    // =========================================================================

    // Current figz bundle path (if loaded)
    private currentFigzPath: string | null = null;

    // DPI for mm-to-pixel conversion
    private bundleRenderDpi: number = 150;

    /**
     * Load a figz bundle onto the canvas.
     * Clears existing content and loads figure with all panels.
     *
     * @param figzPath - Filesystem path to .figz.d directory or .figz file
     */
    public async loadFigzBundle(figzPath: string): Promise<void> {
        if (this.bundleCanvasManager) {
            return this.bundleCanvasManager.loadFigzBundle(figzPath);
        }
    }


    /**
     * Load a single pltz panel onto the canvas.
     *
     * @param panel - Panel spec with position, size, and plot reference
     * @param figzPath - Parent figz bundle path
     */
    public async loadPltzPanel(
        panel: {
            id: string;
            label: string;
            plot: string;
            position: { x_mm?: number; y_mm?: number };
            size: { width_mm?: number; height_mm?: number };
        },
        figzPath: string
    ): Promise<void> {
        if (!this.canvas) {
            console.error('[CanvasManager] Canvas not initialized');
            return;
        }

        // Construct pltz bundle path
        const pltzPath = `${figzPath}/${panel.plot}`;

        console.log(`[CanvasManager] Loading panel ${panel.label}: ${pltzPath}`);

        // Try SVG first for vector graphics quality, fallback to PNG
        const svgUrl = `/vis/api/bundles/pltz/preview/?path=${encodeURIComponent(pltzPath)}&type=svg&t=${Date.now()}`;
        const pngUrl = `/vis/api/bundles/pltz/preview/?path=${encodeURIComponent(pltzPath)}&type=png&t=${Date.now()}`;
        const geometryUrl = `/vis/api/bundles/pltz/geometry/?path=${encodeURIComponent(pltzPath)}`;
        console.log(`[CanvasManager] Loading panel ${panel.label} preview from: ${pltzPath}`);

        // Convert mm position to pixels
        const dpi = this.bundleRenderDpi;
        const mmToPx = dpi / 25.4;
        const x = (panel.position.x_mm || 0) * mmToPx;
        const y = (panel.position.y_mm || 0) * mmToPx;
        const w = (panel.size.width_mm || 80) * mmToPx;
        const h = (panel.size.height_mm || 60) * mmToPx;

        try {
            // Fetch geometry_px.json for JSON-based hit detection
            let geometryData: GeometryData | null = null;
            try {
                const geometryResponse = await fetch(geometryUrl);
                if (geometryResponse.ok) {
                    geometryData = await geometryResponse.json();
                    console.log(`[CanvasManager] Loaded geometry_px.json for panel ${panel.label}:`,
                        'artists=', geometryData?.artists?.length || 0,
                        'axes=', geometryData?.axes?.length || 0);
                }
            } catch (err) {
                console.log(`[CanvasManager] No geometry_px.json for panel ${panel.label}`);
            }

            // Load image using Fabric.js - try SVG first for vector quality
            const fabric = (window as any).fabric;
            let img: any = null;
            let usedSvg = false;

            // Try SVG first
            try {
                const svgResponse = await fetch(svgUrl);
                if (svgResponse.ok) {
                    const svgText = await svgResponse.text();
                    img = await new Promise<any>((resolve, reject) => {
                        fabric.loadSVGFromString(svgText, (objects: any[], options: any) => {
                            if (objects && objects.length > 0) {
                                const group = fabric.util.groupSVGElements(objects, options);
                                usedSvg = true;
                                console.log(`[CanvasManager] Loaded SVG for panel ${panel.label}`);
                                resolve(group);
                            } else {
                                reject(new Error('SVG has no objects'));
                            }
                        });
                    });
                }
            } catch (svgErr) {
                console.log(`[CanvasManager] SVG not available for panel ${panel.label}, falling back to PNG`);
            }

            // Fallback to PNG if SVG failed
            if (!img) {
                img = await new Promise<any>((resolve, reject) => {
                    fabric.Image.fromURL(pngUrl, (loadedImg: any) => {
                        if (loadedImg) {
                            console.log(`[CanvasManager] Loaded PNG for panel ${panel.label}`);
                            resolve(loadedImg);
                        } else {
                            reject(new Error('Failed to load image'));
                        }
                    }, { crossOrigin: 'anonymous' });
                });
            }

            // Calculate scale to fit target size
            const scaleX = w / img.width;
            const scaleY = h / img.height;

            // Set image properties
            img.set({
                left: x,
                top: y,
                scaleX: scaleX,
                scaleY: scaleY,
                selectable: true,
                lockRotation: true,
                // Store bundle info for property editing
                panelId: panel.id,
                panelLabel: panel.label,
                pltzPath: pltzPath,
                figzPath: figzPath,
                // Custom properties for panel identification
                isBundlePanel: true,
            });

            // Attach geometry data for JSON-based element selection / hit testing
            if (geometryData) {
                img.geometryData = geometryData;
            }

            this.canvas.add(img);

            // Process image for current theme (dark mode conversion)
            this.processNewImageForTheme(img);

            console.log(`[CanvasManager] Panel ${panel.label} added at (${x.toFixed(0)}, ${y.toFixed(0)}), size ${w.toFixed(0)}x${h.toFixed(0)}px`);

        } catch (error) {
            console.error(`[CanvasManager] Failed to load panel ${panel.label}:`, error);
        }
    }

    /**
     * Refresh a panel image after property changes.
     *
     * @param pltzPath - Path to the pltz bundle
     */
    public async refreshPanelImage(pltzPath: string): Promise<void> {
        if (this.bundleCanvasManager) {
            return this.bundleCanvasManager.refreshPanelImage(pltzPath);
        }
    }


    /**
     * Get the current figz bundle path.
     */
    public getCurrentFigzPath(): string | null {
        return this.currentFigzPath;
    }

    /**
     * Set the current figz bundle path.
     * Used when switching tabs to reset or restore figz context.
     */
    public setCurrentFigzPath(path: string | null): void {
        this.currentFigzPath = path;
        console.log(`[CanvasManager] Set currentFigzPath to: ${path}`);
    }

    /**
     * Check if an object is a bundle panel.
     */
    public isBundlePanel(obj: any): boolean {
        return obj && obj.isBundlePanel === true;
    }

    /**
     * Get all bundle panels on canvas.
     */
    public getBundlePanels(): any[] {
        if (!this.canvas) return [];
        return this.canvas.getObjects().filter((obj: any) => obj.isBundlePanel === true);
    }

    /**
     * Add a panel to the canvas from gallery selection.
     *
     * Creates a pltz bundle from the plot type and data, then adds it to the canvas.
     *
     * @param plotType - The plot type (line, scatter, bar, etc.)
     * @param dataCsv - Optional CSV data string
     * @param projectOwner - Project owner for saving bundle
     * @param projectSlug - Project slug for saving bundle
     * @param figureName - Figure name (optional, defaults to 'Figure1')
     * @returns The created panel info
     */
    public async addPanelFromGallery(
        plotType: string,
        dataCsv?: string,
        projectOwner?: string,
        projectSlug?: string,
        figureName?: string,
        galleryCategory?: string,
        galleryPlotName?: string
    ): Promise<{ panelLabel: string; bundlePath: string } | null> {
        if (!this.canvas) {
            console.error('[CanvasManager] Canvas not initialized');
            return null;
        }

        // Determine next panel label
        const existingPanels = this.getBundlePanels();
        const usedLabels = new Set(existingPanels.map((p: any) => p.panelLabel || 'A'));
        const labels = 'ABCDEFGH'.split('');
        const nextLabel = labels.find(l => !usedLabels.has(l)) || 'A';

        // Calculate position for new panel
        const existingCount = existingPanels.length;
        const dpi = this.bundleRenderDpi;
        const mmToPx = dpi / 25.4;

        // Default panel size
        const panelWidthMm = 80;
        const panelHeightMm = 68;
        const paddingMm = 5;

        // Simple grid layout
        const col = existingCount % 2;
        const row = Math.floor(existingCount / 2);
        const xMm = paddingMm + col * (panelWidthMm + paddingMm);
        const yMm = paddingMm + row * (panelHeightMm + paddingMm);

        console.log(`[CanvasManager] Creating pltz bundle for panel ${nextLabel} at (${xMm}mm, ${yMm}mm)`);

        try {
            // Create pltz bundle via API
            const response = await fetch('/vis/api/bundles/pltz/create-from-plot/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    plot_type: plotType,
                    data_csv: dataCsv,
                    project_owner: projectOwner,
                    project_slug: projectSlug,
                    figure_name: figureName || 'Figure1',
                    panel_label: nextLabel,
                    gallery_category: galleryCategory,
                    gallery_plot_name: galleryPlotName,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const result = await response.json();
            const bundlePath = result.bundle_path;

            console.log(`[CanvasManager] Created pltz bundle: ${bundlePath}`);

            // Load the panel onto canvas
            await this.loadPltzPanel(
                {
                    id: nextLabel,
                    label: nextLabel,
                    plot: bundlePath.split('/').pop() || `${nextLabel}.pltz.d`,
                    position: { x_mm: xMm, y_mm: yMm },
                    size: { width_mm: panelWidthMm, height_mm: panelHeightMm },
                },
                bundlePath.replace(/\/[^/]+\.pltz\.d$/, '')  // Parent directory as figz path
            );

            // Update the pltzPath on the loaded panel to use full path
            const newPanel = this.canvas.getObjects().find((obj: any) =>
                obj.panelLabel === nextLabel && obj.isBundlePanel
            );
            if (newPanel) {
                newPanel.set('pltzPath', bundlePath);
            }

            this.canvas.renderAll();

            if (this.statusBarCallback) {
                this.statusBarCallback(`Panel ${nextLabel} added: ${plotType}`);
            }

            // Trigger auto-save of figz bundle
            this.triggerFigzAutoSave(projectOwner, projectSlug, figureName);

            return { panelLabel: nextLabel, bundlePath };

        } catch (error) {
            console.error('[CanvasManager] Failed to create panel from gallery:', error);
            if (this.statusBarCallback) {
                this.statusBarCallback(`Error: ${error}`);
            }
            return null;
        }
    }

    /**
     * Trigger auto-save of the current canvas state as a figz bundle.
     */
    public async triggerFigzAutoSave(
        projectOwner?: string,
        projectSlug?: string,
        figureName?: string
    ): Promise<void> {
        const panels = this.getBundlePanels();
        if (panels.length === 0) {
            console.log('[CanvasManager] Auto-save skipped: no panels');
            return;
        }

        // Project context is optional - backend will use user's bundle directory as fallback
        if (!projectOwner || !projectSlug) {
            console.log('[CanvasManager] Auto-save: using user bundle directory (no project context)');
        }

        const dpi = this.bundleRenderDpi;
        const pxToMm = 25.4 / dpi;

        // Build panel data for save
        const panelData = panels.map((panel: any) => ({
            label: panel.panelLabel || 'A',
            pltz_path: panel.pltzPath,
            position: {
                x_mm: Math.round((panel.left || 0) * pxToMm * 10) / 10,
                y_mm: Math.round((panel.top || 0) * pxToMm * 10) / 10,
            },
            size: {
                width_mm: Math.round((panel.width || 80) * (panel.scaleX || 1) * pxToMm * 10) / 10,
                height_mm: Math.round((panel.height || 68) * (panel.scaleY || 1) * pxToMm * 10) / 10,
            },
        }));

        // Get canvas size
        const canvasSize = {
            width_mm: Math.round((this.canvas?.width || 1000) * pxToMm * 10) / 10,
            height_mm: Math.round((this.canvas?.height || 800) * pxToMm * 10) / 10,
        };

        try {
            const response = await fetch('/vis/api/bundles/figz/save-canvas/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    project_owner: projectOwner,
                    project_slug: projectSlug,
                    figure_name: figureName || 'Figure1',
                    panels: panelData,
                    canvas_size: canvasSize,
                    theme: document.body.classList.contains('dark-mode') ? 'dark' : 'light',
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.warn('[CanvasManager] Auto-save warning:', errorData.error);
            } else {
                const result = await response.json();
                const isNewBundle = !this.currentFigzPath;

                // Update current figz path from save result
                if (result.bundle_path) {
                    this.currentFigzPath = result.bundle_path;
                }
                console.log('[CanvasManager] Figz bundle auto-saved');

                // Refresh file tree if this was a new bundle
                if (isNewBundle && result.bundle_path) {
                    const filesTree = (window as any).filesTree;
                    if (filesTree && typeof filesTree.refresh === 'function') {
                        await filesTree.refresh();
                        console.log('[CanvasManager] File tree refreshed after new figz save');
                    }
                }
            }

            // Also save session state to localStorage for page refresh recovery
            this.saveSessionState();
        } catch (error) {
            console.warn('[CanvasManager] Auto-save failed:', error);
        }
    }

    /**
     * Get CSRF token from cookie.
     */
    private getCSRFToken(): string {
        const name = 'csrftoken';
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith(name + '='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    /**
     * Debounced figz auto-save to prevent excessive saves during rapid changes.
     *
     * Uses the stored project context if available, otherwise tries window globals.
     */
    private debouncedFigzAutoSave(): void {
        // Clear existing timer
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
        }

        // Schedule new auto-save
        this.autoSaveTimer = setTimeout(() => {
            const projectOwner = this.bundleProjectOwner || (window as any).projectOwner;
            const projectSlug = this.bundleProjectSlug || (window as any).projectSlug;

            if (projectOwner && projectSlug) {
                this.triggerFigzAutoSave(projectOwner, projectSlug, this.bundleFigureName);
            }
        }, this.autoSaveDelay);
    }

    /**
     * Set bundle project context for auto-save.
     *
     * @param owner - Project owner username
     * @param slug - Project slug
     * @param figureName - Optional figure name
     */
    public setBundleProjectContext(owner: string, slug: string, figureName?: string): void {
        this.bundleProjectOwner = owner;
        this.bundleProjectSlug = slug;
        if (figureName) {
            this.bundleFigureName = figureName;
        }
        console.log(`[CanvasManager] Bundle project context set: ${owner}/${slug}/${this.bundleFigureName}`);
    }

    /**
     * Get active object
     */
    public getActiveObject(): any {
        return this.canvas?.getActiveObject() || null;
    }

    /**
     * Remove active object(s) - handles both single and multiple selection
     */
    public removeActiveObject(): void {
        if (this.objectManager) {
            this.objectManager.removeActiveObject();
        }
    }


    /**
     * Select all objects on canvas
     */
    public selectAll(): void {
        if (this.selectionManager) {
            this.selectionManager.selectAll();
        }
    }


    /**
     * Duplicate active object
     */
    public duplicateActiveObject(): void {
        if (this.selectionManager) {
            this.selectionManager.duplicateActiveObject(
                () => this.saveUndoState(),
                () => this.saveCanvasContent()
            );
        }
    }


    /**
     * Bring active object to front
     * DELEGATES to AlignmentManager
     */
    public bringToFront(): void {
        this.alignmentManager?.bringToFront();
    }

    /**
     * Send active object to back
     * DELEGATES to AlignmentManager
     */
    public sendToBack(): void {
        this.alignmentManager?.sendToBack();
    }

    /**
     * Arrange object (bring to front or send to back)
     * Used by keyboard shortcuts (Alt+G → F/B)
     * DELEGATES to AlignmentManager
     */
    public arrangeObject(action: 'front' | 'back'): void {
        this.alignmentManager?.arrangeObject(action);
    }

    /**
     * Align selected objects
     * - Single object: Aligns to canvas (like PowerPoint aligns to slide)
     * - Multiple objects: Aligns objects relative to each other
     * DELEGATES to AlignmentManager
     */
    public alignObjects(alignment: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v'): void {
        this.alignmentManager?.alignObjects(alignment);
    }

    /**
     * Distribute selected objects evenly
     */
    public distributeObjects(direction: "horizontal" | "vertical"): void {
        if (this.alignmentManager) {
            this.alignmentManager.distributeObjects(direction);
        }
    }


    /**
     * Apply crop from first selected object to all selected objects (Multiple Crop)
     * PowerPoint-style: First object's crop values applied to all
     */
    public multipleCrop(): void {
        // Delegate to CropManager
        if (this.cropManager) {
            this.cropManager.multipleCrop();
        }
    }


    /**
     * Reset crop on selected image(s)
     */
    public resetCrop(): void {
        // Delegate to CropManager
        if (this.cropManager) {
            this.cropManager.resetCrop();
        }
    }

    /**
     * Auto crop margin using Python backend
     * Detects and removes white/transparent margins from images
     */
    public async autoCropMargin(): Promise<void> {
        // Delegate to CropManager
        if (this.cropManager) {
            await this.cropManager.autoCropMargin();
        }
    }

    /**
     * Match size of selected objects to first object
     * PowerPoint-style: First object's size applied to all
     */
    public matchSize(): void {
        if (this.transformManager) {
            this.transformManager.matchSize();
        }
    }

    public matchWidth(): void {
        if (this.transformManager) {
            this.transformManager.matchWidth();
        }
    }

    public matchHeight(): void {
        if (this.transformManager) {
            this.transformManager.matchHeight();
        }
    }

    public resetSize(): void {
        if (this.transformManager) {
            this.transformManager.resetSize();
        }
    }

    public flipHorizontal(): void {
        if (this.transformManager) {
            this.transformManager.flipHorizontal();
        }
    }

    public flipVertical(): void {
        if (this.transformManager) {
            this.transformManager.flipVertical();
        }
    }

    public rotateObjects(degrees: number): void {
        if (this.transformManager) {
            this.transformManager.rotateObjects(degrees);
        }
    }


    /**
     * Group selected objects
     */
    public groupObjects(): void {
        if (this.groupManager) {
            this.groupManager.groupObjects();
        }
    }

    public ungroupObjects(): void {
        if (this.groupManager) {
            this.groupManager.ungroupObjects();
        }
    }

    /**
     * Align by axis with direction support (like regular alignment)
     * @param direction - L=left(Y-axis), C=center-H, R=right, T=top, M=middle-V, B=bottom(X-axis)
     */
    public alignByAxis(direction: "L" | "C" | "R" | "T" | "M" | "B" = "L"): void {
        if (this.alignmentManager) {
            this.alignmentManager.alignByAxis(direction);
        }
    }


    /**
     * Stack selected plots vertically with Y-axis alignment.
     * First aligns Y-axes (left edges), then stacks plots so each plot's
     * top edge touches the previous plot's X-axis (bottom edge).
     * Order is determined by current vertical position (top to bottom).
     */
    public stackVertically(): void {
        if (this.alignmentManager) {
            this.alignmentManager.stackVertically();
        }
    }

    public showAxisDebugLines(objects?: any[]): void {
        if (!this.canvas) return;

        // Clear existing debug lines
        this.clearAxisDebugLines();

        // Get objects to show debug for
        const targetObjects = objects || this.canvas.getObjects().filter(
            (obj: any) => obj.type === 'image' && obj.axisMetadata?.axes_bbox_px
        );

        if (targetObjects.length === 0) {
            console.log('[CanvasManager] No objects with axis metadata to show debug lines');
            return;
        }

        console.log(`[CanvasManager] Showing axis debug lines for ${targetObjects.length} objects`);

        targetObjects.forEach((obj: any, idx: number) => {
            const meta = obj.axisMetadata?.axes_bbox_px;
            if (!meta) return;

            const scaleX = obj.scaleX || 1;
            const scaleY = obj.scaleY || 1;
            const left = obj.left || 0;
            const top = obj.top || 0;

            // Calculate axis positions in canvas coordinates
            const yAxisX = left + meta.x0 * scaleX;  // Y-axis (left edge of plot)
            const xAxisY = top + meta.y1 * scaleY;   // X-axis (bottom edge of plot)
            const rightX = left + meta.x1 * scaleX;  // Right edge of plot
            const topY = top + meta.y0 * scaleY;     // Top edge of plot

            console.log(`  [${idx}] ${obj.name}: left=${left.toFixed(1)}, top=${top.toFixed(1)}, ` +
                `scaleX=${scaleX.toFixed(3)}, scaleY=${scaleY.toFixed(3)}`);
            console.log(`       meta: x0=${meta.x0}, y0=${meta.y0}, x1=${meta.x1}, y1=${meta.y1}`);
            console.log(`       canvas: yAxisX=${yAxisX.toFixed(1)}, xAxisY=${xAxisY.toFixed(1)}`);

            // Y-axis line (red, vertical) - from top of plot to bottom
            const yAxisLine = new (window as any).fabric.Line(
                [yAxisX, topY, yAxisX, xAxisY],
                {
                    stroke: '#ff0000',
                    strokeWidth: 2,
                    selectable: false,
                    evented: false,
                    strokeDashArray: [5, 3],
                    name: `debug-y-axis-${idx}`
                }
            );

            // X-axis line (blue, horizontal) - from Y-axis to right edge
            const xAxisLine = new (window as any).fabric.Line(
                [yAxisX, xAxisY, rightX, xAxisY],
                {
                    stroke: '#0066ff',
                    strokeWidth: 2,
                    selectable: false,
                    evented: false,
                    strokeDashArray: [5, 3],
                    name: `debug-x-axis-${idx}`
                }
            );

            // Add to canvas and store references
            this.canvas!.add(yAxisLine, xAxisLine);
            this.axisDebugLines.push(yAxisLine, xAxisLine);
        });

        this.canvas.renderAll();

        // Auto-clear after 5 seconds
        setTimeout(() => this.clearAxisDebugLines(), 5000);

        if (this.statusBarCallback) {
            this.statusBarCallback(`Showing axis debug lines (auto-clear in 5s)`);
        }
    }

    /**
     * Clear axis debug lines from canvas
     */
    public clearAxisDebugLines(): void {
        if (!this.canvas) return;

        this.axisDebugLines.forEach(line => {
            this.canvas!.remove(line);
        });
        this.axisDebugLines = [];
        this.canvas.renderAll();
    }

    /**
     * Nudge selected objects (move or resize)
     * Arrow keys = move by 1px (or 10px with Alt)
     * Shift+Arrow = resize by 1px (or 10px with Alt)
     */
    public nudgeObjects(direction: 'up' | 'down' | 'left' | 'right', resize: boolean): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        // Determine step size (could be made configurable)
        const step = 1; // 1px per arrow press

        // Get objects to modify
        const objects = active.type === 'activeSelection'
            ? (active as any).getObjects()
            : [active];

        if (resize) {
            // Shift+Arrow = Resize
            objects.forEach((obj: any) => {
                const currentScaleX = obj.scaleX || 1;
                const currentScaleY = obj.scaleY || 1;
                const width = obj.width * currentScaleX;
                const height = obj.height * currentScaleY;

                switch (direction) {
                    case 'up': // Decrease height
                        obj.scaleY = Math.max(0.01, (height - step) / obj.height);
                        break;
                    case 'down': // Increase height
                        obj.scaleY = (height + step) / obj.height;
                        break;
                    case 'left': // Decrease width
                        obj.scaleX = Math.max(0.01, (width - step) / obj.width);
                        break;
                    case 'right': // Increase width
                        obj.scaleX = (width + step) / obj.width;
                        break;
                }
                obj.setCoords();
            });
        } else {
            // Arrow = Move
            objects.forEach((obj: any) => {
                switch (direction) {
                    case 'up':
                        obj.top = (obj.top || 0) - step;
                        break;
                    case 'down':
                        obj.top = (obj.top || 0) + step;
                        break;
                    case 'left':
                        obj.left = (obj.left || 0) - step;
                        break;
                    case 'right':
                        obj.left = (obj.left || 0) + step;
                        break;
                }
                obj.setCoords();
            });
        }

        this.canvas.renderAll();

        // Debounced save to avoid saving on every keypress
        if (!this.nudgeSaveTimer) {
            this.nudgeSaveTimer = setTimeout(() => {
                this.saveCanvasContent();
                this.nudgeSaveTimer = null;
            }, 500);
        }
    }

    private nudgeSaveTimer: ReturnType<typeof setTimeout> | null = null;

    /**
     * Copy view settings (crop, size, scale) from selected object
     * For scientific plots: copy axis limits / ROI to apply to other panels
     */
    public copyView(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No object selected to copy view from');
            }
            return;
        }

        // For multi-selection, use the first object
        const sourceObj = active.type === 'activeSelection'
            ? (active as any).getObjects()[0]
            : active;

        if (!sourceObj) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No valid object to copy view from');
            }
            return;
        }

        // Store view properties (crop, dimensions, scale)
        this.viewClipboard = {
            cropX: sourceObj.cropX || 0,
            cropY: sourceObj.cropY || 0,
            width: sourceObj.width,
            height: sourceObj.height,
            scaleX: sourceObj.scaleX || 1,
            scaleY: sourceObj.scaleY || 1,
        };

        if (this.statusBarCallback) {
            this.statusBarCallback('View copied (crop & scale settings)');
        }
        console.log('[CanvasManager] View copied:', this.viewClipboard);
    }

    /**
     * Paste view settings (crop, size, scale) to selected objects
     * For scientific plots: apply axis limits / ROI to multiple panels
     */
    public pasteView(): void {
        if (!this.canvas) return;

        if (!this.viewClipboard) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No view to paste. Use Ctrl+Shift+C first.');
            }
            return;
        }

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No objects selected to paste view to');
            }
            return;
        }

        this.saveUndoState();

        // Get objects to apply view to
        const objects = active.type === 'activeSelection'
            ? (active as any).getObjects()
            : [active];

        let appliedCount = 0;
        objects.forEach((obj: any) => {
            // Apply view settings
            if (obj.type === 'image') {
                // For images: apply crop and scale
                obj.set({
                    cropX: this.viewClipboard!.cropX,
                    cropY: this.viewClipboard!.cropY,
                    width: this.viewClipboard!.width,
                    height: this.viewClipboard!.height,
                });
            }

            // Apply scale to all object types
            obj.set({
                scaleX: this.viewClipboard!.scaleX,
                scaleY: this.viewClipboard!.scaleY,
            });

            obj.setCoords();
            appliedCount++;
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`View pasted to ${appliedCount} object(s)`);
        }
        console.log(`[CanvasManager] View pasted to ${appliedCount} objects`);
    }

    // ========================================
    // SNAP AND ALIGNMENT GUIDELINES (OPTIMIZED)
    // ========================================

    /**
     * Toggle snap functionality
     */
    public toggleSnap(): void {
        this.snapEnabled = !this.snapEnabled;
        if (this.statusBarCallback) {
            this.statusBarCallback(`Snap ${this.snapEnabled ? 'enabled' : 'disabled'}`);
        }
        console.log(`[CanvasManager] Snap ${this.snapEnabled ? 'enabled' : 'disabled'}`);
    }

    /**
     * Check if snap is enabled
     */
    public isSnapEnabled(): boolean {
        return this.snapEnabled;
    }

    /**
     * Initialize guideline overlay (CSS-based for performance)
     */
    private initGuidelineOverlay(): void {
        if (this.guidelineOverlay) return;

        const canvasContainer = document.getElementById('canvas-container');
        if (!canvasContainer) return;

        this.guidelineOverlay = document.createElement('div');
        this.guidelineOverlay.id = 'snap-guideline-overlay';
        this.guidelineOverlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1000;
            overflow: hidden;
        `;
        canvasContainer.appendChild(this.guidelineOverlay);
    }

    // Track last snap state to prevent oscillation
    private lastSnapX: { guide: number; type: string } | null = null;
    private lastSnapY: { guide: number; type: string } | null = null;
    // Track if Alt key is pressed (for fine adjustment mode - disables snap)
    private altKeyPressed: boolean = false;

    /**
     * Setup Alt key tracking for fine adjustment mode
     */
    public setupAltKeyTracking(): void {
        document.addEventListener('keydown', (e: KeyboardEvent) => {
            if (e.altKey && !this.altKeyPressed) {
                this.altKeyPressed = true;
                // Clear any existing guidelines when entering fine mode
                this.clearAlignmentLines();
            }
        });
        document.addEventListener('keyup', (e: KeyboardEvent) => {
            if (!e.altKey && this.altKeyPressed) {
                this.altKeyPressed = false;
            }
        });
        // Also clear on blur (window loses focus)
        window.addEventListener('blur', () => {
            this.altKeyPressed = false;
        });
    }

    /**
     * Setup hover tooltip to show pltz/figz path when hovering over canvas objects.
     * Shows the bundle path for panels so users know which file they're working with.
     */
    private setupHoverTooltip(): void {
        if (!this.canvas) return;

        // Create tooltip element
        this.hoverTooltip = document.createElement('div');
        this.hoverTooltip.className = 'canvas-hover-tooltip';
        this.hoverTooltip.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            pointer-events: none;
            z-index: 10000;
            display: none;
            max-width: 400px;
            word-break: break-all;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        document.body.appendChild(this.hoverTooltip);

        // Track currently hovered object to avoid redundant updates
        let currentHoveredObj: any = null;

        // Show tooltip on mouse:over
        this.canvas.on('mouse:over', (e: any) => {
            const target = e.target;
            if (!target || !this.hoverTooltip) return;

            // Check if object has pltzPath (bundle panel)
            const pltzPath = target.pltzPath;
            const bundlePath = target.bundlePath;
            const displayPath = pltzPath || bundlePath;

            if (displayPath && target !== currentHoveredObj) {
                currentHoveredObj = target;
                // Extract just the filename for cleaner display
                const filename = displayPath.split('/').pop() || displayPath;
                const label = target.panelLabel || '';

                this.hoverTooltip.innerHTML = label
                    ? `<strong>${label}</strong>: ${filename}`
                    : filename;
                this.hoverTooltip.style.display = 'block';
            }
        });

        // Update tooltip position on mouse move
        this.canvas.on('mouse:move', (e: any) => {
            if (!this.hoverTooltip || this.hoverTooltip.style.display === 'none') return;

            const pointer = e.e as MouseEvent;
            this.hoverTooltip.style.left = `${pointer.clientX + 15}px`;
            this.hoverTooltip.style.top = `${pointer.clientY + 15}px`;
        });

        // Hide tooltip on mouse:out
        this.canvas.on('mouse:out', (e: any) => {
            if (!this.hoverTooltip) return;

            // Only hide if we're leaving an object with a path
            const target = e.target;
            if (target && (target.pltzPath || target.bundlePath)) {
                currentHoveredObj = null;
                this.hoverTooltip.style.display = 'none';
            }
        });
    }

    /**
     * Handle object snapping while moving (OPTIMIZED)
     * Uses CSS overlay instead of Fabric.js lines for better performance
     * Includes hysteresis to prevent snap oscillation/fluctuation
     * Hold Alt to temporarily disable snap for fine adjustment
     */
    private handleObjectSnap(target: any): void {
        if (!this.canvas || !target) return;

        // Alt key disables snapping for fine adjustment (like PowerPoint)
        if (this.altKeyPressed) {
            this.clearAlignmentLines();
            this.lastSnapX = null;
            this.lastSnapY = null;
            return;
        }

        // Initialize overlay on first use
        if (!this.guidelineOverlay) {
            this.initGuidelineOverlay();
        }

        const bound = target.getBoundingRect(true);
        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();
        const threshold = this.snapThreshold;

        // Get zoom and pan for coordinate conversion
        const zoom = this.canvasZoomLevel;
        const panX = this.canvasPanOffset.x;
        const panY = this.canvasPanOffset.y;

        // Calculate snap points for the moving object
        const movingLeft = bound.left;
        const movingRight = bound.left + bound.width;
        const movingCenterX = bound.left + bound.width / 2;
        const movingTop = bound.top;
        const movingBottom = bound.top + bound.height;
        const movingCenterY = bound.top + bound.height / 2;

        let snapX: number | null = null;
        let snapY: number | null = null;
        let guideX: number | null = null;
        let guideY: number | null = null;
        // Track snap type: L=left, R=right, C=center, T=top, B=bottom, Y=y-axis, X=x-axis
        let snapTypeX: string | null = null;
        let snapTypeY: string | null = null;

        // === SNAP TO CANVAS EDGES AND CENTER ===
        if (Math.abs(movingLeft) < threshold) {
            snapX = target.left! - movingLeft;
            guideX = 0;
            snapTypeX = 'L';
        } else if (Math.abs(movingRight - canvasWidth) < threshold) {
            snapX = target.left! + (canvasWidth - movingRight);
            guideX = canvasWidth;
            snapTypeX = 'R';
        } else if (Math.abs(movingCenterX - canvasWidth / 2) < threshold) {
            snapX = target.left! + (canvasWidth / 2 - movingCenterX);
            guideX = canvasWidth / 2;
            snapTypeX = 'C';
        }

        if (Math.abs(movingTop) < threshold) {
            snapY = target.top! - movingTop;
            guideY = 0;
            snapTypeY = 'T';
        } else if (Math.abs(movingBottom - canvasHeight) < threshold) {
            snapY = target.top! + (canvasHeight - movingBottom);
            guideY = canvasHeight;
            snapTypeY = 'B';
        } else if (Math.abs(movingCenterY - canvasHeight / 2) < threshold) {
            snapY = target.top! + (canvasHeight / 2 - movingCenterY);
            guideY = canvasHeight / 2;
            snapTypeY = 'C';
        }

        // === SNAP TO OTHER OBJECTS (only if not already snapped) ===
        if (snapX === null || snapY === null) {
            const objects = this.canvas.getObjects();
            for (let i = 0; i < objects.length; i++) {
                const obj = objects[i];
                if (obj === target || obj.isAlignmentLine || obj.id === 'grid-line' || obj.id === 'column-guide') continue;

                const objBound = obj.getBoundingRect(true);
                const objLeft = objBound.left;
                const objRight = objBound.left + objBound.width;
                const objCenterX = objBound.left + objBound.width / 2;
                const objTop = objBound.top;
                const objBottom = objBound.top + objBound.height;
                const objCenterY = objBound.top + objBound.height / 2;

                // X axis snaps (vertical alignment)
                if (snapX === null) {
                    if (Math.abs(movingLeft - objLeft) < threshold) {
                        snapX = target.left! + (objLeft - movingLeft);
                        guideX = objLeft;
                        snapTypeX = 'L';  // Left edges aligned
                    } else if (Math.abs(movingRight - objRight) < threshold) {
                        snapX = target.left! + (objRight - movingRight);
                        guideX = objRight;
                        snapTypeX = 'R';  // Right edges aligned
                    } else if (Math.abs(movingLeft - objRight) < threshold) {
                        snapX = target.left! + (objRight - movingLeft);
                        guideX = objRight;
                        snapTypeX = 'R';  // My left to their right
                    } else if (Math.abs(movingRight - objLeft) < threshold) {
                        snapX = target.left! + (objLeft - movingRight);
                        guideX = objLeft;
                        snapTypeX = 'L';  // My right to their left
                    } else if (Math.abs(movingCenterX - objCenterX) < threshold) {
                        snapX = target.left! + (objCenterX - movingCenterX);
                        guideX = objCenterX;
                        snapTypeX = 'C';  // Centers aligned
                    }
                }

                // Y axis snaps (horizontal alignment)
                if (snapY === null) {
                    if (Math.abs(movingTop - objTop) < threshold) {
                        snapY = target.top! + (objTop - movingTop);
                        guideY = objTop;
                        snapTypeY = 'T';  // Top edges aligned
                    } else if (Math.abs(movingBottom - objBottom) < threshold) {
                        snapY = target.top! + (objBottom - movingBottom);
                        guideY = objBottom;
                        snapTypeY = 'B';  // Bottom edges aligned
                    } else if (Math.abs(movingTop - objBottom) < threshold) {
                        snapY = target.top! + (objBottom - movingTop);
                        guideY = objBottom;
                        snapTypeY = 'B';  // My top to their bottom
                    } else if (Math.abs(movingBottom - objTop) < threshold) {
                        snapY = target.top! + (objTop - movingBottom);
                        guideY = objTop;
                        snapTypeY = 'T';  // My bottom to their top
                    } else if (Math.abs(movingCenterY - objCenterY) < threshold) {
                        snapY = target.top! + (objCenterY - movingCenterY);
                        guideY = objCenterY;
                        snapTypeY = 'C';  // Centers aligned
                    }
                }

                // Early exit if both snaps found
                if (snapX !== null && snapY !== null) break;
            }
        }

        // === SNAP TO AXIS POSITIONS (for SciTeX plots with metadata) ===
        if (snapX === null || snapY === null) {
            const axisSnapResult = this.snapToAxisPositions(target, bound, threshold);
            if (axisSnapResult.snapX !== null && snapX === null) {
                snapX = axisSnapResult.snapX;
                guideX = axisSnapResult.guideX;
                snapTypeX = axisSnapResult.typeX || 'Y';  // Y-axis alignment
            }
            if (axisSnapResult.snapY !== null && snapY === null) {
                snapY = axisSnapResult.snapY;
                guideY = axisSnapResult.guideY;
                snapTypeY = axisSnapResult.typeY || 'X';  // X-axis alignment
            }
        }

        // Apply snap positions
        if (snapX !== null) target.set('left', snapX);
        if (snapY !== null) target.set('top', snapY);

        // Draw guidelines using CSS (much faster than Fabric.js)
        // Pass snap type info and object bounds for label positioning near cursor
        this.drawGuidelinesCSS(guideX, guideY, canvasWidth, canvasHeight, zoom, panX, panY, snapTypeX, snapTypeY, bound);
    }

    /**
     * Draw guidelines using CSS (optimized - no Fabric.js overhead)
     * Shows snap type indicators: L/R/C for edges, T/B/C for top/bottom, X/Y for axis
     * Labels positioned at the object location (near cursor)
     */
    private drawGuidelinesCSS(
        guideX: number | null,
        guideY: number | null,
        canvasWidth: number,
        canvasHeight: number,
        zoom: number,
        panX: number,
        panY: number,
        snapTypeX: string | null = null,
        snapTypeY: string | null = null,
        objectBound: any = null
    ): void {
        if (!this.guidelineOverlay) return;

        // Colors: red for object/edge snap, cyan for axis snap
        const edgeColor = '#ff6b6b';
        const axisColor = '#00bcd4';  // Cyan - visually distinct

        // Calculate object center in screen coordinates for label positioning
        const objCenterY = objectBound ? (objectBound.top + objectBound.height / 2) * zoom + panY : 50;
        const objCenterX = objectBound ? (objectBound.left + objectBound.width / 2) * zoom + panX : 50;

        // Build HTML for guidelines (reuse single innerHTML assignment)
        let html = '';

        if (guideX !== null && snapTypeX) {
            const screenX = guideX * zoom + panX;
            const isAxisSnap = snapTypeX === 'Y';
            const color = isAxisSnap ? axisColor : edgeColor;
            const width = isAxisSnap ? 2 : 1;  // Thicker line for axis snap

            // Vertical guideline
            html += `<div style="position:absolute;left:${screenX}px;top:0;width:${width}px;height:100%;background:${color};opacity:0.9;"></div>`;

            // Label with snap type - positioned at object's vertical center
            const labelStyle = `position:absolute;left:${screenX + 4}px;top:${objCenterY}px;color:${color};font-size:11px;font-weight:bold;text-shadow:0 0 3px #000,0 0 3px #000;padding:2px 4px;border-radius:2px;`;
            html += `<div style="${labelStyle}">${snapTypeX}</div>`;
        }

        if (guideY !== null && snapTypeY) {
            const screenY = guideY * zoom + panY;
            const isAxisSnap = snapTypeY === 'X';
            const color = isAxisSnap ? axisColor : edgeColor;
            const width = isAxisSnap ? 2 : 1;  // Thicker line for axis snap

            // Horizontal guideline
            html += `<div style="position:absolute;left:0;top:${screenY}px;width:100%;height:${width}px;background:${color};opacity:0.9;"></div>`;

            // Label with snap type - positioned at object's horizontal center
            const labelStyle = `position:absolute;left:${objCenterX}px;top:${screenY + 4}px;color:${color};font-size:11px;font-weight:bold;text-shadow:0 0 3px #000,0 0 3px #000;padding:2px 4px;border-radius:2px;`;
            html += `<div style="${labelStyle}">${snapTypeY}</div>`;
        }

        this.guidelineOverlay.innerHTML = html;
    }

    /**
     * Clear alignment guidelines
     */
    private clearAlignmentLines(): void {
        if (this.guidelineOverlay) {
            this.guidelineOverlay.innerHTML = '';
        }
    }

    /**
     * Snap to axis positions of other plots (for aligning Y-axes, X-axes, etc.)
     * This uses axisMetadata stored on plot images (axes_bbox_px from backend)
     *
     * axes_bbox_px contains:
     * - x0: Left edge of axes (Y-axis position)
     * - x1: Right edge of axes
     * - y0: Top edge of axes
     * - y1: Bottom edge of axes (X-axis position)
     */
    private snapToAxisPositions(
        target: any,
        targetBound: any,
        threshold: number
    ): { snapX: number | null; snapY: number | null; guideX: number | null; guideY: number | null; typeX: string | null; typeY: string | null } {
        const result = { snapX: null as number | null, snapY: null as number | null, guideX: null as number | null, guideY: null as number | null, typeX: null as string | null, typeY: null as string | null };

        if (!this.canvas) return result;

        // Get target's axis positions if it has metadata
        const targetMeta = target.axisMetadata;

        // Check for axes_bbox_px (new format from API)
        if (!targetMeta?.axes_bbox_px) {
            return result;
        }

        console.log('[AxisSnap] Target has axes_bbox_px:', targetMeta.axes_bbox_px);

        // Target's scale (may be different from original size due to canvas scaling)
        const targetScaleX = target.scaleX || 1;
        const targetScaleY = target.scaleY || 1;
        const targetLeft = target.left || 0;
        const targetTop = target.top || 0;

        // Get target's axes bounding box
        const targetAxes = targetMeta.axes_bbox_px;

        // Calculate target Y-axis (left edge of axes) in canvas coordinates
        // Y-axis X position = image left + (axes.x0 * scale)
        const targetYAxisX = targetLeft + targetAxes.x0 * targetScaleX;

        // Calculate target X-axis (bottom edge of axes) in canvas coordinates
        // X-axis Y position = image top + (axes.y1 * scale)
        const targetXAxisY = targetTop + targetAxes.y1 * targetScaleY;

        console.log('[AxisSnap] Target Y-axis at X:', targetYAxisX, 'X-axis at Y:', targetXAxisY);

        // Check against other objects with axis metadata
        const objects = this.canvas.getObjects();

        for (const obj of objects) {
            if (obj === target) continue;

            // Check for axes_bbox_px
            if (!obj.axisMetadata?.axes_bbox_px) continue;

            console.log('[AxisSnap] Found other plot with axes:', obj.name);

            const objMeta = obj.axisMetadata;
            const objScaleX = obj.scaleX || 1;
            const objScaleY = obj.scaleY || 1;
            const objLeft = obj.left || 0;
            const objTop = obj.top || 0;
            const objAxes = objMeta.axes_bbox_px;

            // Calculate other object's axis positions
            const objYAxisX = objLeft + objAxes.x0 * objScaleX;
            const objXAxisY = objTop + objAxes.y1 * objScaleY;

            // Snap Y-axis to Y-axis (vertical alignment of axes left edges)
            if (result.snapX === null) {
                const diff = targetYAxisX - objYAxisX;
                console.log('[AxisSnap] Y-axis diff:', diff.toFixed(1), 'threshold:', threshold);

                if (Math.abs(diff) < threshold) {
                    // Snap: move target so its Y-axis aligns with other's Y-axis
                    result.snapX = targetLeft - diff;
                    result.guideX = objYAxisX;
                    result.typeX = 'Y';  // Y-axis snap
                    console.log('[AxisSnap] SNAP Y-AXIS! X =', objYAxisX.toFixed(1));
                }
            }

            // Snap X-axis to X-axis (horizontal alignment of axes bottom edges)
            if (result.snapY === null) {
                const diff = targetXAxisY - objXAxisY;
                console.log('[AxisSnap] X-axis diff:', diff.toFixed(1), 'threshold:', threshold);

                if (Math.abs(diff) < threshold) {
                    // Snap: move target so its X-axis aligns with other's X-axis
                    result.snapY = targetTop - diff;
                    result.guideY = objXAxisY;
                    result.typeY = 'X';  // X-axis snap
                    console.log('[AxisSnap] SNAP X-AXIS! Y =', objXAxisY.toFixed(1));
                }
            }

            // Early exit if both found
            if (result.snapX !== null && result.snapY !== null) break;
        }

        return result;
    }

    // ============================================================
    // Element-level Selection Mode
    // ============================================================

    // Element selection - all delegated to ElementSelectionManager
    private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void;

    public setElementSelectionCallback(callback: (elementNames: string[], elementInfos: any[]) => void): void {
        this.elementSelectionCallback = callback;
        if (this.elementSelectionManager) {
            this.elementSelectionManager.setElementSelectionCallback(callback);
        }
    }

    public exitElementSelectionMode(): void {
        if (this.elementSelectionManager) {
            this.elementSelectionManager.exitElementSelectionMode();
        }
    }

    public isInElementSelectionMode(): boolean {
        return this.elementSelectionManager?.isInElementSelectionMode() || false;
    }

    public clearElementSelection(): void {
        if (this.elementSelectionManager) {
            this.elementSelectionManager.clearElementSelection();
        }
    }
    public downloadFigzDBundle(): void {
        if (this.exportManager) {
            if (this.currentFigzPath) {
                this.exportManager.setFigzPath(this.currentFigzPath);
            }
            this.exportManager.downloadFigzDBundle();
        }
    }

    /**
     * Download a pltz bundle as .pltz ZIP file
     * Downloads the selected panel's bundle
     */
    public downloadPltzBundle(): void {
        if (!this.exportManager) return;

        // Get selected object
        const activeObj = this.canvas?.getActiveObject();
        if (!activeObj) {
            this.updateStatusBar?.('No panel selected for download');
            return;
        }

        // Get pltz path from the selected object
        const pltzPath = (activeObj as any).pltzPath;
        if (!pltzPath) {
            this.updateStatusBar?.('Selected object is not a pltz panel');
            return;
        }

        this.exportManager.downloadPltzBundle(pltzPath);
    }

    /**
     * Toggle canvas theme between light and dark
     */
    public toggleCanvasTheme(): void {
        if (!this.canvas) return;

        const currentBg = this.canvas.backgroundColor;
        const isDark = currentBg === '#1e1e1e' || currentBg === 'rgb(30, 30, 30)';

        if (isDark) {
            // Switch to light theme
            this.canvas.setBackgroundColor('#ffffff', () => {
                this.canvas!.renderAll();
            });
        } else {
            // Switch to dark theme
            this.canvas.setBackgroundColor('#1e1e1e', () => {
                this.canvas!.renderAll();
            });
        }

        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Canvas theme: ${isDark ? 'light' : 'dark'}`);
        }
    }

    /**
     * Reset view to default zoom and pan
     */
    public resetView(): void {
        this.canvasZoomLevel = 1.0;
        this.canvasPanOffset = { x: 0, y: 0 };

        // Update rulers area transform
        const rulersArea = document.getElementById('canvas-rulers-area');
        if (rulersArea) {
            rulersArea.style.transform = 'translate(0px, 0px) scale(1)';
        }

        // Update zoom display
        const zoomDisplay = document.getElementById('zoom-level-display');
        if (zoomDisplay) {
            zoomDisplay.textContent = '100%';
        }

        if (this.statusBarCallback) {
            this.statusBarCallback('View reset to 100%');
        }
    }
}
