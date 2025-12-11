/**
 * CanvasManager - Handles all Fabric.js canvas operations
 *
 * Responsibilities:
 * - Initialize Fabric.js canvas
 * - Draw and manage grid lines
 * - Handle canvas theme (light/dark)
 * - Handle canvas-specific zoom and pan
 * - Coordinate with rulers for unified transform
 */

import { CANVAS_CONSTANTS } from './types.ts';

export class CanvasManager {
    public canvas: any | null = null; // Fabric.js canvas instance
    private gridEnabled: boolean = true;
    private canvasZoomLevel: number = 0.22; // Start at 22% to fit full canvas (180mm × 240mm)
    private canvasPanOffset: { x: number, y: number } = { x: 0, y: 0 };
    private canvasIsPanning: boolean = false;
    private canvasIsZoomDragging: boolean = false;  // Ctrl+drag zoom mode
    private canvasPanStartPoint: { x: number, y: number } | null = null;
    private canvasZoomDragStartY: number = 0;
    private canvasZoomDragStartLevel: number = 1;
    private canvasWheelThrottleFrame: number | null = null;
    private canvasAccumulatedZoomDelta: number = 0;
    private canvasLastZoomMousePos: { x: number, y: number } = { x: 0, y: 0 };
    private canvasAccumulatedPanDelta: { x: number, y: number } = { x: 0, y: 0 };
    private canvasDragThrottleFrame: number | null = null;
    private pendingDragUpdate: boolean = false;

    // Undo/Redo state management
    private undoStack: string[] = [];
    private redoStack: string[] = [];
    private maxUndoSteps: number = 50;
    private isUndoRedoing: boolean = false;

    // Snap and alignment guidelines
    private snapEnabled: boolean = true;
    private snapThreshold: number = 10; // pixels for snap detection
    private guidelineOverlay: HTMLDivElement | null = null; // CSS overlay for guidelines (faster than Fabric.js)

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

    // Dark mode state for plot image processing
    private isDarkMode: boolean = false;
    // Store original image sources for theme switching
    private originalImageSources: Map<any, string> = new Map();

    private selectionCallback?: (obj: any | null) => void;
    private onObjectResizedCallback?: (obj: any, newWidth: number, newHeight: number) => void;

    constructor(
        private statusBarCallback?: (message: string) => void,
        private rulersAreaTransformCallback?: () => void
    ) {}

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
     */
    public getCanvasZoomLevel(): number {
        return this.canvasZoomLevel;
    }

    /**
     * Get canvas pan offset
     */
    public getCanvasPanOffset(): { x: number, y: number } {
        return this.canvasPanOffset;
    }

    /**
     * Set canvas zoom level (used when restoring tab state)
     */
    public setCanvasZoomLevel(zoom: number): void {
        if (!this.canvas) return;
        this.canvasZoomLevel = zoom;
        this.canvas.setZoom(zoom);
    }

    /**
     * Set canvas pan offset (used when restoring tab state)
     */
    public setCanvasPanOffset(x: number, y: number): void {
        if (!this.canvas) return;
        this.canvasPanOffset = { x, y };
        this.canvas.absolutePan(new fabric.Point(-x, -y));
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

        // Initialize dark mode state for image processing
        this.isDarkMode = initialIsDark;

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

            if (this.gridEnabled) {
                this.drawGrid(initialIsDark);  // Use initial theme for grid
                const gridTime = performance.now();
                console.log(`[CanvasManager] Grid drawn in ${(gridTime - canvasCreateTime).toFixed(2)}ms`);
                console.log(`[CanvasManager] ✅ Total canvas init: ${(gridTime - startTime).toFixed(2)}ms`);
            } else {
                console.log(`[CanvasManager] ✅ Total canvas init: ${(canvasCreateTime - startTime).toFixed(2)}ms`);
            }

            // Restore saved view state
            this.restoreViewState();

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
                            this.enterElementSelectionMode(selected, { x: 0, y: 0 });
                        }
                    } else {
                        // Exit element selection mode for multi-selection
                        this.exitElementSelectionMode();
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
                            this.enterElementSelectionMode(selected, { x: 0, y: 0 });
                        } else {
                            this.exitElementSelectionMode();
                        }
                    } else {
                        // Exit element selection mode for multi-selection
                        this.exitElementSelectionMode();
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
            });

            // Clear guidelines on mouse up
            this.canvas.on('mouse:up', () => {
                this.clearAlignmentLines();
                // Reset snap state when mouse is released
                this.lastSnapX = null;
                this.lastSnapY = null;
            });

            // Setup Alt key tracking for fine adjustment mode
            this.setupAltKeyTracking();
        } catch (error) {
            console.error('[CanvasManager] Error initializing canvas:', error);
        }
    }

    /**
     * Track if we're in group edit mode
     */
    private groupEditMode: boolean = false;
    private editingGroup: any = null;
    private editingGroupOriginalObjects: any[] = [];

    /**
     * Enter group edit mode - allows selecting elements inside a group
     * Double-click on group to enter, click outside to exit
     */
    private enterGroupEditMode(group: any): void {
        if (!this.canvas || this.groupEditMode) return;

        this.groupEditMode = true;
        this.editingGroup = group;

        // Store original state
        const groupLeft = group.left || 0;
        const groupTop = group.top || 0;
        const groupScaleX = group.scaleX || 1;
        const groupScaleY = group.scaleY || 1;
        const groupAngle = group.angle || 0;

        // Convert group to active selection (ungroup but keep tracking)
        const objects = group.getObjects();
        this.editingGroupOriginalObjects = objects.map((obj: any) => ({
            obj,
            originalLeft: obj.left,
            originalTop: obj.top,
        }));

        // Remove group and add individual objects
        this.canvas.remove(group);

        objects.forEach((obj: any) => {
            // Transform object coordinates from group space to canvas space
            const point = fabric.util.transformPoint(
                { x: obj.left || 0, y: obj.top || 0 },
                group.calcTransformMatrix()
            );
            obj.set({
                left: point.x,
                top: point.y,
                scaleX: (obj.scaleX || 1) * groupScaleX,
                scaleY: (obj.scaleY || 1) * groupScaleY,
                angle: (obj.angle || 0) + groupAngle,
                selectable: true,
            });
            obj.setCoords();
            this.canvas!.add(obj);
        });

        this.canvas.renderAll();

        if (this.statusBarCallback) {
            this.statusBarCallback('Editing group - click outside to exit');
        }
        console.log('[CanvasManager] Entered group edit mode');

        // Add one-time click handler to exit group edit mode
        const exitHandler = (e: any) => {
            // If clicking on empty space or different object, exit edit mode
            if (!e.target || !objects.includes(e.target)) {
                this.exitGroupEditMode();
                this.canvas?.off('mouse:down', exitHandler);
            }
        };

        // Delay adding handler to avoid immediate trigger
        setTimeout(() => {
            this.canvas?.on('mouse:down', exitHandler);
        }, 100);
    }

    /**
     * Exit group edit mode - regroup the objects
     */
    public exitGroupEditMode(): void {
        if (!this.canvas || !this.groupEditMode) return;

        const objects = this.editingGroupOriginalObjects.map(item => item.obj);

        // Remove individual objects from canvas
        objects.forEach((obj: any) => {
            this.canvas!.remove(obj);
        });

        // Create new group from objects
        const newGroup = new fabric.Group(objects);
        this.canvas.add(newGroup);
        this.canvas.setActiveObject(newGroup);
        this.canvas.renderAll();

        this.groupEditMode = false;
        this.editingGroup = null;
        this.editingGroupOriginalObjects = [];

        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Exited group edit mode');
        }
        console.log('[CanvasManager] Exited group edit mode');
    }

    /**
     * Draw grid using pre-rendered static SVG files
     * PERFORMANCE: Static SVG files are cached by browser
     */
    public drawGrid(isDark: boolean = false): void {
        if (!this.canvas) return;

        const startTime = performance.now();

        // Use pre-rendered static SVG files for maximum performance
        // Cache bust version: increment when SVG files are updated
        const cacheBust = 'v5';
        const gridUrl = isDark
            ? `/static/vis_app/img/vis/grid-dark.svg?${cacheBust}`
            : `/static/vis_app/img/vis/grid-light.svg?${cacheBust}`;

        // Load as Fabric.js background image
        fabric.Image.fromURL(gridUrl, (img: any) => {
            this.canvas!.setBackgroundImage(img, this.canvas!.renderAll.bind(this.canvas), {
                scaleX: 1,
                scaleY: 1,
                originX: 'left',
                originY: 'top',
            });

            const endTime = performance.now();
            console.log(`[CanvasManager] ✅ Grid loaded from static SVG in ${(endTime - startTime).toFixed(2)}ms (${isDark ? 'dark' : 'light'} mode)`);

            if (this.statusBarCallback) {
                this.statusBarCallback('Grid enabled');
            }
        }, { crossOrigin: 'visitor' });
    }

    /**
     * Clear grid background from canvas
     */
    public clearGrid(): void {
        if (!this.canvas) return;

        // Determine current theme to restore proper background color
        const savedTheme = localStorage.getItem('canvas-theme') || localStorage.getItem('scitex-theme-preference') || 'dark';
        const isDark = savedTheme === 'dark';
        const bgColor = isDark ? '#2a2a2a' : '#ffffff';

        // Clear background image (SVG grid) and restore solid background color
        this.canvas.setBackgroundImage(null, () => {
            this.canvas!.backgroundColor = bgColor;
            this.canvas!.renderAll();
        });

        // Legacy cleanup: Remove any old Fabric.js grid objects (for backwards compatibility)
        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            if (obj.id === 'grid-line' || obj.id === 'column-guide') {
                this.canvas!.remove(obj);
            }
        });
    }

    /**
     * Toggle grid visibility
     */
    public toggleGrid(): void {
        this.gridEnabled = !this.gridEnabled;

        if (this.gridEnabled) {
            // Determine current theme from localStorage
            const savedTheme = localStorage.getItem('canvas-theme') || localStorage.getItem('scitex-theme-preference') || 'dark';
            this.drawGrid(savedTheme === 'dark');
        } else {
            this.clearGrid();
        }

        if (this.statusBarCallback) {
            this.statusBarCallback(`Grid ${this.gridEnabled ? 'enabled' : 'disabled'}`);
        }
        console.log(`[CanvasManager] Grid ${this.gridEnabled ? 'enabled' : 'disabled'}`);
    }

    /**
     * Update canvas theme
     */
    public updateCanvasTheme(isDark: boolean): void {
        if (!this.canvas) return;

        const themeChanged = this.isDarkMode !== isDark;
        this.isDarkMode = isDark;

        // Update canvas background color
        this.canvas.backgroundColor = isDark ? '#2a2a2a' : '#ffffff';

        // Redraw grid with appropriate color if grid is enabled
        if (this.gridEnabled) {
            this.drawGrid(isDark);
        }

        // Reprocess all figure images and SVG groups for dark mode display
        if (themeChanged) {
            this.reprocessAllImagesForTheme();
            this.reprocessAllSvgGroupsForTheme();
        }

        this.canvas.renderAll();
    }

    /**
     * Process image pixels for dark mode display
     * Converts black/near-black to light gray, white to transparent
     */
    private processImageForDarkMode(img: HTMLImageElement): string {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return img.src;

        ctx.drawImage(img, 0, 0);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;

        const BLACK_THRESHOLD = 40;  // Pixels darker than this are considered black
        const WHITE_THRESHOLD = 245; // Pixels lighter than this are considered white
        const TARGET_GRAY = 200;     // Light gray for dark mode text/axes

        for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];

            // Check if pixel is black/near-black
            if (r < BLACK_THRESHOLD && g < BLACK_THRESHOLD && b < BLACK_THRESHOLD) {
                // Convert to light gray
                data[i] = TARGET_GRAY;
                data[i + 1] = TARGET_GRAY;
                data[i + 2] = TARGET_GRAY;
            }
            // Check if pixel is white/near-white (background)
            else if (r > WHITE_THRESHOLD && g > WHITE_THRESHOLD && b > WHITE_THRESHOLD) {
                // Make transparent
                data[i + 3] = 0;
            }
        }

        ctx.putImageData(imageData, 0, 0);
        return canvas.toDataURL('image/png');
    }

    /**
     * Reprocess all figure images when theme changes
     */
    private reprocessAllImagesForTheme(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        let processedCount = 0;

        objects.forEach((obj: any) => {
            // Only process images that are figures (not grid background)
            if (obj.type === 'image' && obj.name && obj.name !== 'grid-background') {
                this.updateImageForTheme(obj);
                processedCount++;
            }
        });

        if (processedCount > 0) {
            console.log(`[CanvasManager] Reprocessed ${processedCount} images for ${this.isDarkMode ? 'dark' : 'light'} mode`);
        }
    }

    /**
     * Process SVG group paths for dark mode display
     * Converts black fills to light gray for visibility on dark canvas
     */
    public processSvgGroupForDarkMode(group: any): void {
        if (!group || group.type !== 'group') return;

        const children = group._objects || [];
        const TARGET_GRAY = '#c8c8c8'; // Light gray (rgb 200,200,200) for dark mode
        let modifiedCount = 0;

        children.forEach((child: any) => {
            if (child.type !== 'path') return;

            const fill = child.fill;
            const stroke = child.stroke;

            // Convert black fills to light gray
            if (fill === '#000000' || fill === 'rgb(0,0,0)' || fill === 'black') {
                // Store original color if not stored
                if (!child.originalFill) {
                    child.originalFill = fill;
                }
                child.set('fill', TARGET_GRAY);
                modifiedCount++;
            }

            // Convert black strokes to light gray
            if (stroke === '#000000' || stroke === 'rgb(0,0,0)' || stroke === 'black') {
                if (!child.originalStroke) {
                    child.originalStroke = stroke;
                }
                child.set('stroke', TARGET_GRAY);
                modifiedCount++;
            }
        });

        // Mark group dirty and update coordinates
        group.set('dirty', true);
        group.setCoords();

        console.log(`[CanvasManager] Dark mode: modified ${modifiedCount} path colors in group`);
    }

    /**
     * Restore SVG group paths to original colors (for light mode)
     */
    public restoreSvgGroupColors(group: any): void {
        if (!group || group.type !== 'group') return;

        const children = group._objects || [];
        let modifiedCount = 0;

        children.forEach((child: any) => {
            if (child.type !== 'path') return;

            // Restore original fill if stored
            if (child.originalFill) {
                child.set('fill', child.originalFill);
                modifiedCount++;
            }

            // Restore original stroke if stored
            if (child.originalStroke) {
                child.set('stroke', child.originalStroke);
                modifiedCount++;
            }
        });

        // Mark group dirty and update coordinates
        group.set('dirty', true);
        group.setCoords();

        console.log(`[CanvasManager] Light mode: restored ${modifiedCount} path colors in group`);
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
     * Update a single image for current theme
     */
    private updateImageForTheme(fabricImg: any): void {
        const element = fabricImg.getElement();
        if (!element) return;

        // Store original source if not already stored
        if (!this.originalImageSources.has(fabricImg)) {
            this.originalImageSources.set(fabricImg, element.src);
        }

        const originalSrc = this.originalImageSources.get(fabricImg)!;

        if (this.isDarkMode) {
            // Load original image and process for dark mode
            const tempImg = new Image();
            tempImg.crossOrigin = 'anonymous';
            tempImg.onload = () => {
                const processedSrc = this.processImageForDarkMode(tempImg);
                const newImg = new Image();
                newImg.crossOrigin = 'anonymous';
                newImg.onload = () => {
                    fabricImg.setElement(newImg);
                    this.canvas?.renderAll();
                };
                newImg.src = processedSrc;
            };
            tempImg.src = originalSrc;
        } else {
            // Restore original image
            const newImg = new Image();
            newImg.crossOrigin = 'anonymous';
            newImg.onload = () => {
                fabricImg.setElement(newImg);
                this.canvas?.renderAll();
            };
            newImg.src = originalSrc;
        }
    }

    /**
     * Save current state to undo stack
     */
    public saveUndoState(): void {
        if (!this.canvas || this.isUndoRedoing) return;

        const json = JSON.stringify(this.canvas.toJSON(['name', 'id']));

        // Don't save if state is same as last
        if (this.undoStack.length > 0 && this.undoStack[this.undoStack.length - 1] === json) {
            return;
        }

        this.undoStack.push(json);

        // Limit stack size
        if (this.undoStack.length > this.maxUndoSteps) {
            this.undoStack.shift();
        }

        // Clear redo stack when new action is performed
        this.redoStack = [];

        console.log(`[CanvasManager] Saved undo state (${this.undoStack.length} states)`);
    }

    /**
     * Undo last action
     */
    public undo(): void {
        if (!this.canvas || this.undoStack.length === 0) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Nothing to undo');
            }
            return;
        }

        this.isUndoRedoing = true;

        // Save current state to redo stack
        const currentState = JSON.stringify(this.canvas.toJSON(['name', 'id']));
        this.redoStack.push(currentState);

        // Pop and apply previous state
        const previousState = this.undoStack.pop()!;
        this.canvas.loadFromJSON(JSON.parse(previousState), () => {
            this.canvas!.renderAll();
            this.isUndoRedoing = false;

            if (this.statusBarCallback) {
                this.statusBarCallback(`Undo (${this.undoStack.length} left)`);
            }
            console.log(`[CanvasManager] Undo applied (${this.undoStack.length} states left)`);
        });
    }

    /**
     * Redo last undone action
     */
    public redo(): void {
        if (!this.canvas || this.redoStack.length === 0) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Nothing to redo');
            }
            return;
        }

        this.isUndoRedoing = true;

        // Save current state to undo stack
        const currentState = JSON.stringify(this.canvas.toJSON(['name', 'id']));
        this.undoStack.push(currentState);

        // Pop and apply redo state
        const redoState = this.redoStack.pop()!;
        this.canvas.loadFromJSON(JSON.parse(redoState), () => {
            this.canvas!.renderAll();
            this.isUndoRedoing = false;

            if (this.statusBarCallback) {
                this.statusBarCallback(`Redo (${this.redoStack.length} left)`);
            }
            console.log(`[CanvasManager] Redo applied (${this.redoStack.length} states left)`);
        });
    }

    // Clipboard for copy/paste
    private clipboard: any = null;

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
     */
    public copyActiveObject(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No object selected to copy');
            }
            return;
        }

        active.clone((cloned: any) => {
            this.clipboard = cloned;
            if (this.statusBarCallback) {
                this.statusBarCallback('Object copied');
            }
            console.log('[CanvasManager] Object copied to clipboard');
        });
    }

    /**
     * Paste object from clipboard
     */
    public pasteObject(): void {
        if (!this.canvas || !this.clipboard) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Nothing to paste');
            }
            return;
        }

        // Save undo state before pasting
        this.saveUndoState();

        this.clipboard.clone((cloned: any) => {
            cloned.set({
                left: (this.clipboard.left || 0) + 20,
                top: (this.clipboard.top || 0) + 20,
                evented: true,
            });

            this.canvas!.add(cloned);
            this.canvas!.setActiveObject(cloned);
            this.canvas!.renderAll();
            this.saveCanvasContent();

            // Update clipboard position for cascading pastes
            this.clipboard.left = cloned.left;
            this.clipboard.top = cloned.top;

            if (this.statusBarCallback) {
                this.statusBarCallback('Object pasted');
            }
            console.log('[CanvasManager] Object pasted from clipboard');
        });
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

        // Setup context menu
        this.setupContextMenu(canvasContainer);

        // Track right-click pan to distinguish from context menu
        let rightClickPanStartPoint: { x: number; y: number } | null = null;

        // Track right-click double-click for canvas reset
        let lastRightClickTime = 0;
        const DOUBLE_CLICK_THRESHOLD = 300; // ms

        // Mouse down - Check for panning or zoom dragging
        canvasContainer.addEventListener('mousedown', (e: MouseEvent) => {
            if (e.button === 1 || (e as any).spaceKey) {
                if (e.ctrlKey || e.metaKey) {
                    // Ctrl + middle mouse = zoom drag mode
                    this.canvasIsZoomDragging = true;
                    this.canvasZoomDragStartY = e.clientY;
                    this.canvasZoomDragStartLevel = this.canvasZoomLevel;
                    canvasContainer.style.cursor = 'ns-resize';
                    e.preventDefault();
                    console.log('[CanvasManager] Canvas zoom drag mode started');
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

                            // Use Fabric.js viewport transform for pan (maintains SVG crispness)
                            this.updateCanvasTransform();

                            // Update rulers
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
        }, 200); // Debounce 200ms
    }

    /**
     * Restore view state from localStorage
     */
    public restoreViewState(): void {
        try {
            const saved = localStorage.getItem('scitex-vis-viewstate');
            if (saved) {
                const state = JSON.parse(saved);
                if (state.zoom !== undefined) this.canvasZoomLevel = state.zoom;
                if (state.panX !== undefined) this.canvasPanOffset.x = state.panX;
                if (state.panY !== undefined) this.canvasPanOffset.y = state.panY;
                console.log('[CanvasManager] Restored view state:', state);
            }
        } catch (err) {
            console.warn('[CanvasManager] Failed to restore view state:', err);
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
    public addImage(src: string, options: {
        left?: number;
        top?: number;
        scaleToFit?: boolean;
        maxWidth?: number;
        maxHeight?: number;
        selectable?: boolean;
        name?: string;
        axisMetadata?: any;  // Axis metadata for snap/align by axis
        csvData?: string[][];  // CSV data for stats (must be set before adding to canvas)
        plotInfo?: any;  // Plot info for re-rendering
    } = {}): Promise<any> {
        return new Promise(async (resolve, reject) => {
            if (!this.canvas) {
                reject(new Error('Canvas not initialized'));
                return;
            }

            // If no axisMetadata provided and src is a data URL (PNG), try to extract embedded metadata
            let axisMetadata = options.axisMetadata;
            if (!axisMetadata && src.startsWith('data:image/png')) {
                try {
                    const response = await fetch('/vis/api/plot/metadata/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: src }),
                    });
                    const result = await response.json();
                    if (result.success && result.has_metadata && result.axes_bbox_px) {
                        axisMetadata = {
                            axes_bbox_px: result.axes_bbox_px,
                            figure_size_px: result.figure_size_px
                        };
                        console.log('[CanvasManager] Extracted embedded metadata:', axisMetadata);
                    }
                } catch (err) {
                    console.log('[CanvasManager] No embedded metadata or extraction failed');
                }
            }

            fabric.Image.fromURL(src, (img: any) => {
                if (!img || !img.width) {
                    reject(new Error('Failed to load image'));
                    return;
                }

                // Scale to fit if requested
                if (options.scaleToFit) {
                    const maxW = options.maxWidth || CANVAS_CONSTANTS.MAX_CANVAS_WIDTH * 0.8;
                    const maxH = options.maxHeight || CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT * 0.8;

                    const scaleX = maxW / img.width!;
                    const scaleY = maxH / img.height!;
                    const scale = Math.min(scaleX, scaleY, 1); // Don't upscale

                    img.scale(scale);
                }

                // Position - default to upper-left with small margin (5mm ≈ 19px at 96dpi)
                const defaultMargin = 19; // ~5mm
                img.set({
                    left: options.left ?? defaultMargin,
                    top: options.top ?? defaultMargin,
                    selectable: options.selectable !== false,
                    name: options.name || 'figure',
                });

                // Store original dimensions for scaling calculations
                img.originalWidth = img.width;
                img.originalHeight = img.height;

                // Store axis metadata for snap/align by axis
                if (axisMetadata) {
                    img.axisMetadata = axisMetadata;
                    console.log('[CanvasManager] Stored axis metadata on image:', axisMetadata);
                }

                // Store CSV data for stats (MUST be set before adding to canvas)
                // This is because setActiveObject triggers selection:created which enters element mode
                if (options.csvData && options.csvData.length > 0) {
                    img.csvData = options.csvData;
                    console.log(`[CanvasManager] Stored CSV data on image: ${options.csvData.length} rows`);
                }

                // Store plot info for re-rendering
                if (options.plotInfo) {
                    img.plotInfo = options.plotInfo;
                }

                // Save undo state before adding
                this.saveUndoState();

                // Store original source for theme switching
                this.originalImageSources.set(img, src);

                this.canvas!.add(img);
                this.canvas!.setActiveObject(img);

                // Process for dark mode if active
                if (this.isDarkMode) {
                    this.updateImageForTheme(img);
                } else {
                    this.canvas!.renderAll();
                }

                // Save canvas content after adding image
                this.saveCanvasContent();

                if (this.statusBarCallback) {
                    this.statusBarCallback(`Added image: ${options.name || 'figure'}`);
                }

                console.log(`[CanvasManager] Added image: ${options.name || 'figure'} (${img.width}×${img.height})`);
                resolve(img);
            }, { crossOrigin: 'anonymous' });
        });
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
    public addSvg(svgString: string, options: {
        left?: number;
        top?: number;
        scaleToFit?: boolean;
        maxWidth?: number;
        maxHeight?: number;
        name?: string;
        selectableElements?: boolean; // If true, elements inside can be selected individually
        axisMetadata?: any; // Metadata for element selection (must be attached BEFORE setActiveObject)
        plotInfo?: any; // Plot info (category, name, etc.)
        csvData?: any; // CSV data for stats
    } = {}): Promise<any> {
        return new Promise((resolve, reject) => {
            if (!this.canvas) {
                reject(new Error('Canvas not initialized'));
                return;
            }

            fabric.loadSVGFromString(svgString, (objects: any[], svgOptions: any) => {
                if (!objects || objects.length === 0) {
                    reject(new Error('Failed to load SVG'));
                    return;
                }

                // Create a group from all SVG elements
                const group = fabric.util.groupSVGElements(objects, svgOptions);

                // Scale to fit if requested
                if (options.scaleToFit) {
                    const maxW = options.maxWidth || CANVAS_CONSTANTS.MAX_CANVAS_WIDTH * 0.8;
                    const maxH = options.maxHeight || CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT * 0.8;

                    const scaleX = maxW / group.width!;
                    const scaleY = maxH / group.height!;
                    const scale = Math.min(scaleX, scaleY, 1);

                    group.scale(scale);
                }

                // Position
                const defaultMargin = 19;
                group.set({
                    left: options.left ?? defaultMargin,
                    top: options.top ?? defaultMargin,
                    name: options.name || 'svg-figure',
                });

                // If selectableElements is true, make this a non-grouped set
                // so individual elements can be selected
                if (options.selectableElements) {
                    // Add individual elements instead of group
                    const groupLeft = group.left || 0;
                    const groupTop = group.top || 0;
                    const scale = group.scaleX || 1;

                    objects.forEach((obj: any, index: number) => {
                        obj.set({
                            left: groupLeft + (obj.left || 0) * scale,
                            top: groupTop + (obj.top || 0) * scale,
                            scaleX: (obj.scaleX || 1) * scale,
                            scaleY: (obj.scaleY || 1) * scale,
                            selectable: true,
                            name: `${options.name || 'svg'}-element-${index}`,
                        });
                        this.canvas!.add(obj);
                    });

                    this.canvas!.renderAll();
                    this.saveCanvasContent();

                    if (this.statusBarCallback) {
                        this.statusBarCallback(`Added SVG with ${objects.length} selectable elements`);
                    }

                    resolve(objects);
                } else {
                    // Add as a single group (default behavior)
                    // IMPORTANT: Attach metadata BEFORE setActiveObject to enable element selection
                    // setActiveObject triggers selection:created which checks for axisMetadata
                    if (options.axisMetadata) {
                        group.axisMetadata = options.axisMetadata;
                    }
                    if (options.plotInfo) {
                        group.plotInfo = options.plotInfo;
                    }
                    if (options.csvData) {
                        group.csvData = options.csvData;
                    }

                    // Apply dark mode color transformation if in dark mode
                    if (this.isDarkMode) {
                        this.processSvgGroupForDarkMode(group);
                    }

                    this.canvas!.add(group);
                    this.canvas!.setActiveObject(group);
                    this.canvas!.renderAll();
                    this.saveCanvasContent();

                    if (this.statusBarCallback) {
                        this.statusBarCallback(`Added SVG: ${options.name || 'figure'}`);
                    }

                    resolve(group);
                }
            });
        });
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
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        // Save undo state before removing
        this.saveUndoState();

        // Check if it's an ActiveSelection (multiple objects selected)
        if (active.type === 'activeSelection') {
            // Get all objects in the selection
            const objects = active.getObjects();
            const count = objects.length;

            // Discard the selection first
            this.canvas.discardActiveObject();

            // Remove each object individually
            objects.forEach((obj: any) => {
                this.canvas!.remove(obj);
            });

            this.canvas.renderAll();

            if (this.statusBarCallback) {
                this.statusBarCallback(`${count} objects removed`);
            }
        } else {
            // Single object
            this.canvas.remove(active);
            this.canvas.renderAll();

            if (this.statusBarCallback) {
                this.statusBarCallback('Object removed');
            }
        }
    }

    /**
     * Select all objects on canvas
     */
    public selectAll(): void {
        if (!this.canvas) return;

        // Get all selectable objects (exclude grid, guidelines, etc.)
        const objects = this.canvas.getObjects().filter((obj: any) => {
            return obj.selectable !== false &&
                   obj.id !== 'grid-line' &&
                   obj.id !== 'column-guide' &&
                   !obj.isAlignmentLine;
        });

        if (objects.length === 0) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No objects to select');
            }
            return;
        }

        // Deselect any current selection
        this.canvas.discardActiveObject();

        // Create new selection with all objects
        const selection = new (window as any).fabric.ActiveSelection(objects, {
            canvas: this.canvas
        });
        this.canvas.setActiveObject(selection);
        this.canvas.renderAll();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Selected ${objects.length} objects`);
        }
    }

    /**
     * Setup right-click context menu
     */
    private setupContextMenu(container: HTMLElement): void {
        // Create context menu element
        const menu = document.createElement('div');
        menu.id = 'canvas-context-menu';
        menu.className = 'canvas-context-menu';
        menu.innerHTML = `
            <div class="context-menu-item" data-action="copy">
                <i class="fas fa-copy"></i> Copy
                <span class="shortcut">Ctrl+C</span>
            </div>
            <div class="context-menu-item" data-action="paste">
                <i class="fas fa-paste"></i> Paste
                <span class="shortcut">Ctrl+V</span>
            </div>
            <div class="context-menu-item" data-action="duplicate">
                <i class="fas fa-clone"></i> Duplicate
                <span class="shortcut">Ctrl+D</span>
            </div>
            <div class="context-menu-item" data-action="delete">
                <i class="fas fa-trash"></i> Delete
                <span class="shortcut">Del</span>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-submenu image-only-section" style="display:none;">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-crop-alt"></i> Crop
                    <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="crop-manual">
                        <i class="fas fa-crop"></i> Crop (Manual)
                    </div>
                    <div class="context-menu-item" data-action="crop-margin">
                        <i class="fas fa-compress-alt"></i> Auto Crop Margin
                    </div>
                    <div class="context-menu-item" data-action="crop-reset">
                        <i class="fas fa-undo"></i> Reset Crop
                    </div>
                </div>
            </div>
            <div class="context-menu-item" data-action="copy-view">
                <i class="fas fa-crop"></i> Copy View (ROI)
                <span class="shortcut">Ctrl+Shift+C</span>
            </div>
            <div class="context-menu-item" data-action="paste-view">
                <i class="fas fa-paste"></i> Paste View (ROI)
                <span class="shortcut">Ctrl+Shift+V</span>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item" data-action="bring-front">
                <i class="fas fa-layer-group"></i> Bring to Front
                <span class="shortcut">Alt+F</span>
            </div>
            <div class="context-menu-item" data-action="send-back">
                <i class="fas fa-layer-group"></i> Send to Back
                <span class="shortcut">Alt+B</span>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-submenu">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-align-left"></i> Align
                    <span class="shortcut">Alt+A</span>
                    <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="align-left">
                        <i class="fas fa-align-left"></i> Left
                        <span class="shortcut">L</span>
                    </div>
                    <div class="context-menu-item" data-action="align-center-h">
                        <i class="fas fa-align-center"></i> Horizontal
                        <span class="shortcut">H</span>
                    </div>
                    <div class="context-menu-item" data-action="align-right">
                        <i class="fas fa-align-right"></i> Right
                        <span class="shortcut">R</span>
                    </div>
                    <div class="context-menu-item" data-action="align-top">
                        <i class="fas fa-arrow-up"></i> Top
                        <span class="shortcut">T</span>
                    </div>
                    <div class="context-menu-item" data-action="align-center-v">
                        <i class="fas fa-arrows-alt-v"></i> Vertical
                        <span class="shortcut">V</span>
                    </div>
                    <div class="context-menu-item" data-action="align-bottom">
                        <i class="fas fa-arrow-down"></i> Bottom
                        <span class="shortcut">B</span>
                    </div>
                </div>
            </div>
            <div class="context-menu-submenu multi-select-section" style="display:none;">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-chart-line"></i> Align by Axis
                    <span class="shortcut">Alt+Shift+A</span>
                    <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="align-by-axis-l">
                        <i class="fas fa-grip-lines-vertical"></i> Y-Axis (Left)
                        <span class="shortcut">L</span>
                    </div>
                    <div class="context-menu-item" data-action="align-by-axis-c">
                        <i class="fas fa-arrows-alt-h"></i> Horizontal Center
                        <span class="shortcut">C</span>
                    </div>
                    <div class="context-menu-item" data-action="align-by-axis-r">
                        <i class="fas fa-grip-lines-vertical"></i> Right Edge
                        <span class="shortcut">R</span>
                    </div>
                    <div class="context-menu-separator"></div>
                    <div class="context-menu-item" data-action="align-by-axis-t">
                        <i class="fas fa-grip-lines"></i> Top Edge
                        <span class="shortcut">T</span>
                    </div>
                    <div class="context-menu-item" data-action="align-by-axis-m">
                        <i class="fas fa-arrows-alt-v"></i> Vertical Center
                        <span class="shortcut">M</span>
                    </div>
                    <div class="context-menu-item" data-action="align-by-axis-b">
                        <i class="fas fa-grip-lines"></i> X-Axis (Bottom)
                        <span class="shortcut">B</span>
                    </div>
                    <div class="context-menu-separator"></div>
                    <div class="context-menu-item" data-action="align-by-axis-s">
                        <i class="fas fa-layer-group"></i> Stack Vertically
                        <span class="shortcut">S</span>
                    </div>
                </div>
            </div>
            <div class="context-menu-submenu multi-select-section" style="display:none;">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-expand-arrows-alt"></i> Size
                    <span class="shortcut">Alt+S</span>
                    <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="match-size">
                        <i class="fas fa-compress-arrows-alt"></i> Match Size
                        <span class="shortcut">S</span>
                    </div>
                    <div class="context-menu-item" data-action="match-width">
                        <i class="fas fa-arrows-alt-h"></i> Match Width
                        <span class="shortcut">W</span>
                    </div>
                    <div class="context-menu-item" data-action="match-height">
                        <i class="fas fa-arrows-alt-v"></i> Match Height
                        <span class="shortcut">T</span>
                    </div>
                    <div class="context-menu-item" data-action="multiple-crop">
                        <i class="fas fa-crop-alt"></i> Multiple Crop
                        <span class="shortcut">C</span>
                    </div>
                </div>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-submenu">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-sync-alt"></i> Transform
                    <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="flip-h">
                        <i class="fas fa-arrows-alt-h"></i> Flip Horizontal
                    </div>
                    <div class="context-menu-item" data-action="flip-v">
                        <i class="fas fa-arrows-alt-v"></i> Flip Vertical
                    </div>
                    <div class="context-menu-item" data-action="rotate-90">
                        <i class="fas fa-redo"></i> Rotate 90°
                    </div>
                    <div class="context-menu-item" data-action="rotate-180">
                        <i class="fas fa-sync"></i> Rotate 180°
                    </div>
                    <div class="context-menu-item" data-action="reset-size">
                        <i class="fas fa-expand"></i> Reset Size (100%)
                    </div>
                </div>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item" data-action="group">
                <i class="fas fa-object-group"></i> Group
                <span class="shortcut">Ctrl+G</span>
            </div>
            <div class="context-menu-item" data-action="ungroup">
                <i class="fas fa-object-ungroup"></i> Ungroup
                <span class="shortcut">Ctrl+Shift+G</span>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-submenu">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-download"></i> Export
                    <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="export-png">
                        <i class="fas fa-file-image"></i> Export as PNG
                    </div>
                    <div class="context-menu-item" data-action="export-svg">
                        <i class="fas fa-bezier-curve"></i> Export as SVG
                    </div>
                    <div class="context-menu-item" data-action="export-pdf">
                        <i class="fas fa-file-pdf"></i> Export as PDF
                    </div>
                </div>
            </div>
            <div class="context-menu-item" data-action="save-canvas">
                <i class="fas fa-save"></i> Save Figure
                <span class="shortcut">Ctrl+S</span>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item" data-action="toggle-theme">
                <i class="fas fa-adjust"></i> Toggle Light/Dark
            </div>
            <div class="context-menu-item" data-action="zoom-fit">
                <i class="fas fa-expand"></i> Zoom to Fit
                <span class="shortcut">Ctrl+0</span>
            </div>
            <div class="context-menu-item" data-action="reset-view">
                <i class="fas fa-home"></i> Reset View
            </div>
            <div class="context-menu-separator stats-section" style="display:none;"></div>
            <div class="context-menu-submenu stats-section" style="display:none;">
                <div class="context-menu-item submenu-header">
                    <i class="fas fa-chart-bar"></i> Statistics
                    <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
                </div>
                <div class="submenu-items">
                    <div class="context-menu-item" data-action="stats-recommended">
                        <i class="fas fa-magic"></i> Run Recommended Test
                    </div>
                    <div class="context-menu-item" data-action="stats-all">
                        <i class="fas fa-vials"></i> Run All Applicable
                    </div>
                    <div class="context-menu-item" data-action="stats-select">
                        <i class="fas fa-list"></i> Select Test...
                    </div>
                    <div class="context-menu-separator"></div>
                    <div class="context-menu-item" data-action="stats-inspector">
                        <i class="fas fa-microscope"></i> Open Stats Inspector
                    </div>
                </div>
            </div>
        `;
        menu.style.cssText = `
            position: fixed;
            display: none;
            background: var(--bg-secondary, #1e1e1e);
            border: 1px solid var(--border-color, #333);
            border-radius: 6px;
            padding: 4px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            min-width: 160px;
        `;
        document.body.appendChild(menu);

        // Add styles for menu items
        const style = document.createElement('style');
        style.textContent = `
            .canvas-context-menu .context-menu-item {
                padding: 8px 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                color: var(--text-primary, #e0e0e0);
                font-size: 13px;
            }
            .canvas-context-menu .context-menu-item:hover {
                background: var(--bg-hover, #2a2a2a);
            }
            .canvas-context-menu .context-menu-item i {
                width: 16px;
                text-align: center;
                opacity: 0.7;
            }
            .canvas-context-menu .context-menu-item .shortcut {
                margin-left: auto;
                opacity: 0.5;
                font-size: 11px;
            }
            .canvas-context-menu .context-menu-separator {
                height: 1px;
                background: var(--border-color, #333);
                margin: 4px 0;
            }
            .canvas-context-menu .context-menu-submenu {
                position: relative;
            }
            .canvas-context-menu .context-menu-submenu .submenu-header {
                cursor: default;
            }
            .canvas-context-menu .context-menu-submenu .submenu-items {
                display: none;
                position: absolute;
                left: 100%;
                top: 0;
                background: var(--bg-secondary, #1e1e1e);
                border: 1px solid var(--border-color, #333);
                border-radius: 6px;
                padding: 4px 0;
                min-width: 120px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
            .canvas-context-menu .context-menu-submenu:hover .submenu-items {
                display: block;
            }
            .canvas-context-menu .context-menu-submenu.submenu-left .submenu-items {
                left: auto;
                right: 100%;
            }
        `;
        document.head.appendChild(style);

        // Right-click handler
        container.addEventListener('contextmenu', (e: MouseEvent) => {
            e.preventDefault();

            // Skip context menu if right-click was used for panning
            if (this.rightClickPanOccurred) {
                this.rightClickPanOccurred = false;
                menu.style.display = 'none';
                return;
            }

            // Check if we have an active object or element-level selection
            const activeObj = this.canvas?.getActiveObject();
            const hasElementSelection = this.selectedElementNames.size >= 2;

            if (!activeObj && !hasElementSelection) {
                menu.style.display = 'none';
                return;
            }

            // Show/hide multi-select-only options (Distribute, Size)
            // Align is always shown (single object aligns to canvas)
            const multiSelectSections = menu.querySelectorAll('.multi-select-section');
            const isMultiSelect = activeObj?.type === 'activeSelection';
            multiSelectSections.forEach(section => {
                (section as HTMLElement).style.display = isMultiSelect ? 'block' : 'none';
            });

            // Show/hide image-only options (Crop)
            const imageOnlySections = menu.querySelectorAll('.image-only-section');
            const isImage = activeObj?.type === 'image' ||
                (isMultiSelect && (activeObj as any).getObjects?.()?.some((o: any) => o.type === 'image'));
            imageOnlySections.forEach(section => {
                (section as HTMLElement).style.display = isImage ? 'block' : 'none';
            });

            // Show/hide stats section (requires multi-selection with plot data OR element-level selection)
            const statsSections = menu.querySelectorAll('.stats-section');
            const hasPlotData = isMultiSelect && activeObj && (activeObj as any).getObjects?.()?.some((o: any) => o.plotData);
            // hasElementSelection already declared above
            statsSections.forEach(section => {
                (section as HTMLElement).style.display = (isMultiSelect || hasPlotData || hasElementSelection) ? 'block' : 'none';
            });

            // Position menu at cursor
            menu.style.left = `${e.clientX}px`;
            menu.style.top = `${e.clientY}px`;
            menu.style.display = 'block';

            // Ensure menu stays in viewport
            const rect = menu.getBoundingClientRect();
            if (rect.right > window.innerWidth) {
                menu.style.left = `${window.innerWidth - rect.width - 5}px`;
            }
            if (rect.bottom > window.innerHeight) {
                menu.style.top = `${window.innerHeight - rect.height - 5}px`;
            }

            // Check if submenus need to open to the left
            const submenus = menu.querySelectorAll('.context-menu-submenu');
            const menuRight = menu.getBoundingClientRect().right;
            const submenuWidth = 140; // Approximate submenu width
            submenus.forEach(submenu => {
                if (menuRight + submenuWidth > window.innerWidth) {
                    submenu.classList.add('submenu-left');
                } else {
                    submenu.classList.remove('submenu-left');
                }
            });
        });

        // Click handlers for menu items
        menu.addEventListener('click', (e: MouseEvent) => {
            const target = (e.target as HTMLElement).closest('.context-menu-item');
            if (!target) return;

            // Don't close menu for submenu headers
            if ((target as HTMLElement).classList.contains('submenu-header')) {
                return;
            }

            const action = (target as HTMLElement).dataset.action;
            menu.style.display = 'none';

            switch (action) {
                case 'copy':
                    this.copyActiveObject();
                    break;
                case 'paste':
                    this.pasteObject();
                    break;
                case 'delete':
                    this.removeActiveObject();
                    this.saveCanvasContent();
                    break;
                case 'duplicate':
                    this.duplicateActiveObject();
                    break;
                case 'bring-front':
                    this.bringToFront();
                    break;
                case 'send-back':
                    this.sendToBack();
                    break;
                case 'align-left':
                    this.alignObjects('left');
                    break;
                case 'align-right':
                    this.alignObjects('right');
                    break;
                case 'align-top':
                    this.alignObjects('top');
                    break;
                case 'align-bottom':
                    this.alignObjects('bottom');
                    break;
                case 'align-center-h':
                    this.alignObjects('center-h');
                    break;
                case 'align-center-v':
                    this.alignObjects('center-v');
                    break;
                case 'distribute-h':
                    this.distributeObjects('horizontal');
                    break;
                case 'distribute-v':
                    this.distributeObjects('vertical');
                    break;
                case 'match-size':
                    this.matchSize();
                    break;
                case 'match-width':
                    this.matchWidth();
                    break;
                case 'match-height':
                    this.matchHeight();
                    break;
                case 'multiple-crop':
                    this.multipleCrop();
                    break;
                case 'align-by-axis-l':
                    this.alignByAxis('L');
                    break;
                case 'align-by-axis-c':
                    this.alignByAxis('C');
                    break;
                case 'align-by-axis-r':
                    this.alignByAxis('R');
                    break;
                case 'align-by-axis-t':
                    this.alignByAxis('T');
                    break;
                case 'align-by-axis-m':
                    this.alignByAxis('M');
                    break;
                case 'align-by-axis-b':
                    this.alignByAxis('B');
                    break;
                case 'align-by-axis-s':
                    this.stackVertically();
                    break;
                case 'crop-manual':
                    this.enterCropMode();
                    break;
                case 'crop-margin':
                    this.autoCropMargin();
                    break;
                case 'crop-reset':
                    this.resetCrop();
                    break;
                case 'flip-h':
                    this.flipHorizontal();
                    break;
                case 'flip-v':
                    this.flipVertical();
                    break;
                case 'rotate-90':
                    this.rotateObjects(90);
                    break;
                case 'rotate-180':
                    this.rotateObjects(180);
                    break;
                case 'reset-size':
                    this.resetSize();
                    break;
                case 'group':
                    this.groupObjects();
                    break;
                case 'ungroup':
                    this.ungroupObjects();
                    break;
                case 'copy-view':
                    this.copyView();
                    break;
                case 'paste-view':
                    this.pasteView();
                    break;
                // Statistics actions
                case 'stats-recommended':
                    this.runRecommendedStatTest();
                    break;
                case 'stats-all':
                    this.runAllStatTests();
                    break;
                case 'stats-select':
                    this.showStatTestSelector();
                    break;
                case 'stats-inspector':
                    this.openStatsInspector();
                    break;
                // Export actions
                case 'export-png':
                    this.exportAsPng();
                    break;
                case 'export-svg':
                    this.exportAsSvg();
                    break;
                case 'export-pdf':
                    this.exportAsPdf();
                    break;
                // Canvas actions
                case 'save-canvas':
                    this.saveCanvasContent();
                    if (this.statusBarCallback) {
                        this.statusBarCallback('Figure saved');
                    }
                    break;
                case 'toggle-theme':
                    this.toggleCanvasTheme();
                    break;
                case 'zoom-fit':
                    this.zoomToFit();
                    break;
                case 'reset-view':
                    this.resetView();
                    break;
            }
        });

        // Close menu on click outside
        document.addEventListener('click', (e: MouseEvent) => {
            if (!menu.contains(e.target as Node)) {
                menu.style.display = 'none';
            }
        });

        // Close menu on escape
        document.addEventListener('keydown', (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                menu.style.display = 'none';
            }
        });

        console.log('[CanvasManager] Context menu initialized');
    }

    /**
     * Duplicate active object
     */
    public duplicateActiveObject(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        // Save undo state before duplicating
        this.saveUndoState();

        active.clone((cloned: any) => {
            cloned.set({
                left: (active.left || 0) + 20,
                top: (active.top || 0) + 20,
            });
            this.canvas!.add(cloned);
            this.canvas!.setActiveObject(cloned);
            this.canvas!.renderAll();
            this.saveCanvasContent();

            if (this.statusBarCallback) {
                this.statusBarCallback('Object duplicated');
            }
        });
    }

    /**
     * Bring active object to front
     */
    public bringToFront(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (active) {
            this.canvas.bringToFront(active);
            this.canvas.renderAll();
            this.saveCanvasContent();

            if (this.statusBarCallback) {
                this.statusBarCallback('Brought to front');
            }
        }
    }

    /**
     * Send active object to back
     */
    public sendToBack(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (active) {
            this.canvas.sendToBack(active);
            this.canvas.renderAll();
            this.saveCanvasContent();

            if (this.statusBarCallback) {
                this.statusBarCallback('Sent to back');
            }
        }
    }

    /**
     * Arrange object (bring to front or send to back)
     * Used by keyboard shortcuts (Alt+G → F/B)
     */
    public arrangeObject(action: 'front' | 'back'): void {
        if (action === 'front') {
            this.bringToFront();
        } else {
            this.sendToBack();
        }
    }

    /**
     * Align selected objects
     * - Single object: Aligns to canvas (like PowerPoint aligns to slide)
     * - Multiple objects: Aligns objects relative to each other
     */
    public alignObjects(alignment: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v'): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject) return;

        this.saveUndoState();

        const alignmentNames: Record<string, string> = {
            'left': 'Left',
            'right': 'Right',
            'top': 'Top',
            'bottom': 'Bottom',
            'center-h': 'Horizontal Center',
            'center-v': 'Vertical Center',
        };

        // Single object - align to canvas
        if (activeObject.type !== 'activeSelection') {
            const canvasWidth = this.canvas.getWidth();
            const canvasHeight = this.canvas.getHeight();
            const bound = activeObject.getBoundingRect(true);

            switch (alignment) {
                case 'left':
                    activeObject.set('left', activeObject.left! - bound.left);
                    break;
                case 'right':
                    activeObject.set('left', activeObject.left! + (canvasWidth - (bound.left + bound.width)));
                    break;
                case 'top':
                    activeObject.set('top', activeObject.top! - bound.top);
                    break;
                case 'bottom':
                    activeObject.set('top', activeObject.top! + (canvasHeight - (bound.top + bound.height)));
                    break;
                case 'center-h':
                    activeObject.set('left', activeObject.left! + (canvasWidth / 2 - (bound.left + bound.width / 2)));
                    break;
                case 'center-v':
                    activeObject.set('top', activeObject.top! + (canvasHeight / 2 - (bound.top + bound.height / 2)));
                    break;
            }
            activeObject.setCoords();

            this.canvas.renderAll();
            this.saveCanvasContent();

            if (this.statusBarCallback) {
                this.statusBarCallback(`Aligned to canvas: ${alignmentNames[alignment]}`);
            }
            return;
        }

        // Multiple objects - align relative to each other
        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        // Calculate bounds of all selected objects
        let minLeft = Infinity, maxRight = -Infinity;
        let minTop = Infinity, maxBottom = -Infinity;

        objects.forEach((obj: any) => {
            const bound = obj.getBoundingRect(true);
            minLeft = Math.min(minLeft, bound.left);
            maxRight = Math.max(maxRight, bound.left + bound.width);
            minTop = Math.min(minTop, bound.top);
            maxBottom = Math.max(maxBottom, bound.top + bound.height);
        });

        const centerX = (minLeft + maxRight) / 2;
        const centerY = (minTop + maxBottom) / 2;

        objects.forEach((obj: any) => {
            const bound = obj.getBoundingRect(true);

            switch (alignment) {
                case 'left':
                    obj.set('left', obj.left! - (bound.left - minLeft));
                    break;
                case 'right':
                    obj.set('left', obj.left! + (maxRight - (bound.left + bound.width)));
                    break;
                case 'top':
                    obj.set('top', obj.top! - (bound.top - minTop));
                    break;
                case 'bottom':
                    obj.set('top', obj.top! + (maxBottom - (bound.top + bound.height)));
                    break;
                case 'center-h':
                    obj.set('left', obj.left! + (centerX - (bound.left + bound.width / 2)));
                    break;
                case 'center-v':
                    obj.set('top', obj.top! + (centerY - (bound.top + bound.height / 2)));
                    break;
            }
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Aligned: ${alignmentNames[alignment]}`);
        }
    }

    /**
     * Distribute selected objects evenly
     */
    public distributeObjects(direction: 'horizontal' | 'vertical'): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple objects to distribute');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 3) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select at least 3 objects to distribute');
            }
            return;
        }

        this.saveUndoState();

        // Get absolute bounding rects for all objects
        // Need to calculate absolute position since objects in ActiveSelection have relative coords
        const objectsWithBounds = objects.map((obj: any) => {
            const bound = obj.getBoundingRect(true, true); // absolute=true, calculate=true
            return {
                obj,
                bound,
                centerX: bound.left + bound.width / 2,
                centerY: bound.top + bound.height / 2
            };
        });

        // Sort objects by position
        objectsWithBounds.sort((a: any, b: any) => {
            return direction === 'horizontal'
                ? a.centerX - b.centerX
                : a.centerY - b.centerY;
        });

        // Calculate total space between first and last centers
        const first = objectsWithBounds[0];
        const last = objectsWithBounds[objectsWithBounds.length - 1];

        const totalSpace = direction === 'horizontal'
            ? last.centerX - first.centerX
            : last.centerY - first.centerY;

        const spacing = totalSpace / (objectsWithBounds.length - 1);

        // Distribute middle objects (skip first and last)
        for (let i = 1; i < objectsWithBounds.length - 1; i++) {
            const item = objectsWithBounds[i];
            const obj = item.obj;

            if (direction === 'horizontal') {
                const targetCenterX = first.centerX + spacing * i;
                const deltaX = targetCenterX - item.centerX;
                obj.set('left', (obj.left || 0) + deltaX);
            } else {
                const targetCenterY = first.centerY + spacing * i;
                const deltaY = targetCenterY - item.centerY;
                obj.set('top', (obj.top || 0) + deltaY);
            }
            obj.setCoords();
        }

        // Need to update the ActiveSelection's internal coordinates
        activeObject.setCoords();

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Distributed: ${direction === 'horizontal' ? 'Horizontally' : 'Vertically'}`);
        }
    }

    /**
     * Apply crop from first selected object to all selected objects (Multiple Crop)
     * PowerPoint-style: First object's crop values applied to all
     */
    public multipleCrop(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple images to apply multiple crop');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select at least 2 images');
            }
            return;
        }

        // Get first image's crop values
        const firstImg = objects[0];
        if (firstImg.type !== 'image') {
            if (this.statusBarCallback) {
                this.statusBarCallback('First selected object must be an image');
            }
            return;
        }

        this.saveUndoState();

        // Get crop values from first image
        const cropX = firstImg.cropX || 0;
        const cropY = firstImg.cropY || 0;
        const width = firstImg.width;
        const height = firstImg.height;

        // Apply to all other images
        let appliedCount = 0;
        objects.forEach((obj: any, index: number) => {
            if (index === 0) return; // Skip first
            if (obj.type === 'image') {
                obj.set({
                    cropX: cropX,
                    cropY: cropY,
                    width: width,
                    height: height,
                });
                obj.setCoords();
                appliedCount++;
            }
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Applied crop to ${appliedCount} images`);
        }
    }

    // Crop mode state
    private cropModeActive: boolean = false;
    private cropTarget: any = null;
    private cropOverlay: HTMLDivElement | null = null;
    private cropHandles: HTMLDivElement[] = [];
    private cropRect: { x: number, y: number, width: number, height: number } | null = null;

    /**
     * Enter manual crop mode for selected image
     * Shows crop handles that user can drag to adjust crop area
     */
    public enterCropMode(): void {
        if (!this.canvas) return;

        const activeObj = this.canvas.getActiveObject();
        if (!activeObj || activeObj.type !== 'image') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select an image to crop');
            }
            return;
        }

        this.cropModeActive = true;
        this.cropTarget = activeObj;

        // Create crop overlay UI
        this.createCropOverlay(activeObj);

        if (this.statusBarCallback) {
            this.statusBarCallback('Crop mode: Drag handles to adjust. Press Enter to apply, Escape to cancel.');
        }
    }

    // Store original image dimensions for crop calculations
    private cropOriginalWidth: number = 0;
    private cropOriginalHeight: number = 0;
    private cropOriginalBound: any = null;
    private cropScaleX: number = 1;
    private cropScaleY: number = 1;

    /**
     * Create crop overlay with handles (PowerPoint-style with dimmed outside area)
     */
    private createCropOverlay(target: any): void {
        const canvasContainer = document.getElementById('canvas-container');
        if (!canvasContainer) return;

        // Get object bounds in screen coordinates
        const bound = target.getBoundingRect(true);
        const zoom = this.canvasZoomLevel;
        const panX = this.canvasPanOffset.x;
        const panY = this.canvasPanOffset.y;
        const scaleX = target.scaleX || 1;
        const scaleY = target.scaleY || 1;

        const screenX = bound.left * zoom + panX;
        const screenY = bound.top * zoom + panY;
        const screenW = bound.width * zoom;
        const screenH = bound.height * zoom;

        // Store original image dimensions (unscaled) for crop calculations
        this.cropOriginalWidth = target.width;
        this.cropOriginalHeight = target.height;

        // Initialize crop rect to current visible area (in image coordinates)
        this.cropRect = { x: 0, y: 0, width: target.width, height: target.height };

        // Create main overlay container (covers the whole image area)
        this.cropOverlay = document.createElement('div');
        this.cropOverlay.id = 'crop-overlay';
        this.cropOverlay.style.cssText = `
            position: absolute;
            left: ${screenX}px;
            top: ${screenY}px;
            width: ${screenW}px;
            height: ${screenH}px;
            pointer-events: none;
            z-index: 2000;
        `;

        // Create 4 dim overlays for outside area (top, bottom, left, right)
        // These will be positioned relative to the crop rect
        const dimColor = 'rgba(0, 0, 0, 0.5)';

        const topDim = document.createElement('div');
        topDim.className = 'crop-dim crop-dim-top';
        topDim.style.cssText = `position:absolute;left:0;top:0;right:0;height:0;background:${dimColor};`;

        const bottomDim = document.createElement('div');
        bottomDim.className = 'crop-dim crop-dim-bottom';
        bottomDim.style.cssText = `position:absolute;left:0;bottom:0;right:0;height:0;background:${dimColor};`;

        const leftDim = document.createElement('div');
        leftDim.className = 'crop-dim crop-dim-left';
        leftDim.style.cssText = `position:absolute;left:0;top:0;width:0;bottom:0;background:${dimColor};`;

        const rightDim = document.createElement('div');
        rightDim.className = 'crop-dim crop-dim-right';
        rightDim.style.cssText = `position:absolute;right:0;top:0;width:0;bottom:0;background:${dimColor};`;

        this.cropOverlay.appendChild(topDim);
        this.cropOverlay.appendChild(bottomDim);
        this.cropOverlay.appendChild(leftDim);
        this.cropOverlay.appendChild(rightDim);

        // Create crop border (dashed line around crop area)
        const cropBorder = document.createElement('div');
        cropBorder.className = 'crop-border';
        cropBorder.style.cssText = `
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            border: 2px dashed #4a9eff;
            box-sizing: border-box;
            pointer-events: none;
        `;
        this.cropOverlay.appendChild(cropBorder);

        // Create corner handles
        const handlePositions = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'];
        handlePositions.forEach(pos => {
            const handle = document.createElement('div');
            handle.className = `crop-handle crop-handle-${pos}`;
            handle.dataset.position = pos;
            handle.style.cssText = `
                position: absolute;
                width: 10px;
                height: 10px;
                background: #4a9eff;
                border: 1px solid #fff;
                border-radius: 2px;
                pointer-events: auto;
                cursor: ${this.getCropCursor(pos)};
            `;
            this.positionCropHandle(handle, pos, screenW, screenH);
            this.cropOverlay!.appendChild(handle);
            this.cropHandles.push(handle);

            // Add drag handling
            this.setupCropHandleDrag(handle, pos, target, bound, scaleX, scaleY);
        });

        canvasContainer.appendChild(this.cropOverlay);

        // Store for later use
        this.cropOriginalBound = bound;
        this.cropScaleX = scaleX;
        this.cropScaleY = scaleY;

        // Initial positioning of dim overlays and crop border
        this.updateCropOverlay(this.cropRect!, bound, scaleX, scaleY);

        // Add keyboard listeners for Enter/Escape
        this.setupCropKeyboardListeners();
    }

    /**
     * Get cursor for crop handle position
     */
    private getCropCursor(pos: string): string {
        const cursors: Record<string, string> = {
            'nw': 'nw-resize', 'ne': 'ne-resize', 'sw': 'sw-resize', 'se': 'se-resize',
            'n': 'n-resize', 's': 's-resize', 'e': 'e-resize', 'w': 'w-resize'
        };
        return cursors[pos] || 'move';
    }

    /**
     * Position a crop handle
     */
    private positionCropHandle(handle: HTMLDivElement, pos: string, width: number, height: number): void {
        const size = 10;
        const half = size / 2;
        switch (pos) {
            case 'nw': handle.style.left = `-${half}px`; handle.style.top = `-${half}px`; break;
            case 'ne': handle.style.right = `-${half}px`; handle.style.top = `-${half}px`; break;
            case 'sw': handle.style.left = `-${half}px`; handle.style.bottom = `-${half}px`; break;
            case 'se': handle.style.right = `-${half}px`; handle.style.bottom = `-${half}px`; break;
            case 'n': handle.style.left = `${width / 2 - half}px`; handle.style.top = `-${half}px`; break;
            case 's': handle.style.left = `${width / 2 - half}px`; handle.style.bottom = `-${half}px`; break;
            case 'e': handle.style.right = `-${half}px`; handle.style.top = `${height / 2 - half}px`; break;
            case 'w': handle.style.left = `-${half}px`; handle.style.top = `${height / 2 - half}px`; break;
        }
    }

    /**
     * Setup drag handling for crop handle
     */
    private setupCropHandleDrag(handle: HTMLDivElement, pos: string, target: any, originalBound: any, scaleX: number, scaleY: number): void {
        let startX = 0, startY = 0;
        let startRect = { ...this.cropRect! };

        const onMouseMove = (e: MouseEvent) => {
            // Convert screen delta to image coordinates (accounting for zoom and scale)
            const dx = (e.clientX - startX) / (this.canvasZoomLevel * scaleX);
            const dy = (e.clientY - startY) / (this.canvasZoomLevel * scaleY);

            const newRect = { ...startRect };

            // Adjust rect based on handle position
            if (pos.includes('w')) { newRect.x += dx; newRect.width -= dx; }
            if (pos.includes('e')) { newRect.width += dx; }
            if (pos.includes('n')) { newRect.y += dy; newRect.height -= dy; }
            if (pos.includes('s')) { newRect.height += dy; }

            // Clamp to valid bounds (use original image dimensions, not bounding rect)
            newRect.x = Math.max(0, newRect.x);
            newRect.y = Math.max(0, newRect.y);
            newRect.width = Math.max(20, Math.min(newRect.width, this.cropOriginalWidth - newRect.x));
            newRect.height = Math.max(20, Math.min(newRect.height, this.cropOriginalHeight - newRect.y));

            this.cropRect = newRect;
            this.updateCropOverlay(newRect, originalBound, scaleX, scaleY);
        };

        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        handle.addEventListener('mousedown', (e: MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            startX = e.clientX;
            startY = e.clientY;
            startRect = { ...this.cropRect! };
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    /**
     * Update crop overlay position/size (PowerPoint-style with dim areas)
     */
    private updateCropOverlay(rect: any, originalBound: any, scaleX: number = 1, scaleY: number = 1): void {
        if (!this.cropOverlay) return;

        const zoom = this.canvasZoomLevel;
        const panX = this.canvasPanOffset.x;
        const panY = this.canvasPanOffset.y;

        // Full image bounds in screen coordinates
        const imgScreenX = originalBound.left * zoom + panX;
        const imgScreenY = originalBound.top * zoom + panY;
        const imgScreenW = originalBound.width * zoom;
        const imgScreenH = originalBound.height * zoom;

        // Crop rect in screen coordinates (relative to image top-left)
        const cropScreenX = rect.x * scaleX * zoom;
        const cropScreenY = rect.y * scaleY * zoom;
        const cropScreenW = rect.width * scaleX * zoom;
        const cropScreenH = rect.height * scaleY * zoom;

        // Main overlay stays at full image bounds
        this.cropOverlay.style.left = `${imgScreenX}px`;
        this.cropOverlay.style.top = `${imgScreenY}px`;
        this.cropOverlay.style.width = `${imgScreenW}px`;
        this.cropOverlay.style.height = `${imgScreenH}px`;

        // Update dim overlays (cover areas outside crop rect)
        const topDim = this.cropOverlay.querySelector('.crop-dim-top') as HTMLElement;
        const bottomDim = this.cropOverlay.querySelector('.crop-dim-bottom') as HTMLElement;
        const leftDim = this.cropOverlay.querySelector('.crop-dim-left') as HTMLElement;
        const rightDim = this.cropOverlay.querySelector('.crop-dim-right') as HTMLElement;

        if (topDim) {
            topDim.style.height = `${cropScreenY}px`;
        }
        if (bottomDim) {
            bottomDim.style.height = `${imgScreenH - cropScreenY - cropScreenH}px`;
        }
        if (leftDim) {
            leftDim.style.top = `${cropScreenY}px`;
            leftDim.style.width = `${cropScreenX}px`;
            leftDim.style.height = `${cropScreenH}px`;
        }
        if (rightDim) {
            rightDim.style.top = `${cropScreenY}px`;
            rightDim.style.width = `${imgScreenW - cropScreenX - cropScreenW}px`;
            rightDim.style.height = `${cropScreenH}px`;
        }

        // Update crop border position
        const cropBorder = this.cropOverlay.querySelector('.crop-border') as HTMLElement;
        if (cropBorder) {
            cropBorder.style.left = `${cropScreenX}px`;
            cropBorder.style.top = `${cropScreenY}px`;
            cropBorder.style.width = `${cropScreenW}px`;
            cropBorder.style.height = `${cropScreenH}px`;
        }

        // Reposition handles (relative to crop border)
        this.cropHandles.forEach(handle => {
            const pos = handle.dataset.position!;
            // Position handles relative to crop rect within the overlay
            this.positionCropHandleInOverlay(handle, pos, cropScreenX, cropScreenY, cropScreenW, cropScreenH);
        });
    }

    /**
     * Position crop handle within the overlay (for PowerPoint-style crop)
     */
    private positionCropHandleInOverlay(handle: HTMLDivElement, pos: string, cropX: number, cropY: number, width: number, height: number): void {
        const size = 10;
        const half = size / 2;

        // Base position on crop rect
        let left = cropX;
        let top = cropY;

        switch (pos) {
            case 'nw': left = cropX - half; top = cropY - half; break;
            case 'ne': left = cropX + width - half; top = cropY - half; break;
            case 'sw': left = cropX - half; top = cropY + height - half; break;
            case 'se': left = cropX + width - half; top = cropY + height - half; break;
            case 'n': left = cropX + width / 2 - half; top = cropY - half; break;
            case 's': left = cropX + width / 2 - half; top = cropY + height - half; break;
            case 'e': left = cropX + width - half; top = cropY + height / 2 - half; break;
            case 'w': left = cropX - half; top = cropY + height / 2 - half; break;
        }

        handle.style.left = `${left}px`;
        handle.style.top = `${top}px`;
        handle.style.right = 'auto';
        handle.style.bottom = 'auto';
    }

    /**
     * Setup keyboard listeners for crop mode
     */
    private setupCropKeyboardListeners(): void {
        const handler = (e: KeyboardEvent) => {
            if (!this.cropModeActive) return;

            if (e.key === 'Enter') {
                e.preventDefault();
                this.applyCrop();
                document.removeEventListener('keydown', handler);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.exitCropMode();
                document.removeEventListener('keydown', handler);
            }
        };
        document.addEventListener('keydown', handler);
    }

    /**
     * Apply the current crop
     */
    private applyCrop(): void {
        if (!this.cropTarget || !this.cropRect) {
            this.exitCropMode();
            return;
        }

        this.saveUndoState();

        // Apply crop to the image
        const target = this.cropTarget;
        const rect = this.cropRect;

        // Fabric.js crop properties
        target.set({
            cropX: (target.cropX || 0) + rect.x,
            cropY: (target.cropY || 0) + rect.y,
            width: rect.width,
            height: rect.height,
        });
        target.setCoords();

        this.canvas!.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Crop applied');
        }

        this.exitCropMode();
    }

    /**
     * Exit crop mode without applying
     */
    private exitCropMode(): void {
        this.cropModeActive = false;
        this.cropTarget = null;
        this.cropRect = null;

        // Remove overlay
        if (this.cropOverlay) {
            this.cropOverlay.remove();
            this.cropOverlay = null;
        }
        this.cropHandles = [];

        if (this.statusBarCallback) {
            this.statusBarCallback('Crop mode exited');
        }
    }

    /**
     * Reset crop on selected image(s)
     */
    public resetCrop(): void {
        if (!this.canvas) return;

        const activeObj = this.canvas.getActiveObject();
        if (!activeObj) return;

        this.saveUndoState();

        const resetImage = (img: any) => {
            if (img.type !== 'image') return;
            // Reset to original dimensions
            const element = img.getElement();
            if (element) {
                img.set({
                    cropX: 0,
                    cropY: 0,
                    width: element.naturalWidth || element.width,
                    height: element.naturalHeight || element.height,
                });
                img.setCoords();
            }
        };

        if (activeObj.type === 'activeSelection') {
            (activeObj as any).getObjects().forEach(resetImage);
        } else {
            resetImage(activeObj);
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Crop reset to original');
        }
    }

    /**
     * Auto crop margin using Python backend
     * Detects and removes white/transparent margins from images
     */
    public async autoCropMargin(): Promise<void> {
        if (!this.canvas) return;

        const activeObj = this.canvas.getActiveObject();
        if (!activeObj) return;

        // Collect images to process
        const images: any[] = [];
        if (activeObj.type === 'activeSelection') {
            (activeObj as any).getObjects().forEach((obj: any) => {
                if (obj.type === 'image') images.push(obj);
            });
        } else if (activeObj.type === 'image') {
            images.push(activeObj);
        }

        if (images.length === 0) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select image(s) to auto-crop');
            }
            return;
        }

        if (this.statusBarCallback) {
            this.statusBarCallback(`Auto-cropping ${images.length} image(s)...`);
        }

        this.saveUndoState();

        // Process each image
        for (const img of images) {
            try {
                await this.autoCropSingleImage(img);
            } catch (error) {
                console.error('[CanvasManager] Auto-crop failed for image:', error);
            }
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Auto-cropped ${images.length} image(s)`);
        }
    }

    /**
     * Auto crop a single image using canvas analysis
     * Finds content bounds and removes margins
     */
    private async autoCropSingleImage(fabricImg: any): Promise<void> {
        const element = fabricImg.getElement();
        if (!element) return;

        // Create temporary canvas for image analysis
        const tempCanvas = document.createElement('canvas');
        const ctx = tempCanvas.getContext('2d');
        if (!ctx) return;

        const imgWidth = element.naturalWidth || element.width;
        const imgHeight = element.naturalHeight || element.height;
        tempCanvas.width = imgWidth;
        tempCanvas.height = imgHeight;

        ctx.drawImage(element, 0, 0);

        // Get image data
        const imageData = ctx.getImageData(0, 0, imgWidth, imgHeight);
        const data = imageData.data;

        // Find content bounds (non-white/non-transparent pixels)
        let minX = imgWidth, minY = imgHeight, maxX = 0, maxY = 0;
        const threshold = 250; // Consider pixels with R,G,B > 250 as white

        for (let y = 0; y < imgHeight; y++) {
            for (let x = 0; x < imgWidth; x++) {
                const idx = (y * imgWidth + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];
                const a = data[idx + 3];

                // Check if pixel is not white and not transparent
                const isContent = a > 10 && (r < threshold || g < threshold || b < threshold);

                if (isContent) {
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        // Add small padding
        const padding = 2;
        minX = Math.max(0, minX - padding);
        minY = Math.max(0, minY - padding);
        maxX = Math.min(imgWidth - 1, maxX + padding);
        maxY = Math.min(imgHeight - 1, maxY + padding);

        // Apply crop if bounds were found
        if (maxX > minX && maxY > minY) {
            fabricImg.set({
                cropX: (fabricImg.cropX || 0) + minX,
                cropY: (fabricImg.cropY || 0) + minY,
                width: maxX - minX + 1,
                height: maxY - minY + 1,
            });
            fabricImg.setCoords();
        }
    }

    /**
     * Match size of selected objects to first object
     * PowerPoint-style: First object's size applied to all
     */
    public matchSize(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple objects to match size');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        this.saveUndoState();

        // Get first object's dimensions
        const first = objects[0];
        const targetWidth = first.getScaledWidth();
        const targetHeight = first.getScaledHeight();

        // Apply to all other objects
        objects.forEach((obj: any, index: number) => {
            if (index === 0) return;

            const currentWidth = obj.getScaledWidth();
            const currentHeight = obj.getScaledHeight();

            // Scale to match (preserve aspect ratio option could be added)
            obj.scaleX = (obj.scaleX || 1) * (targetWidth / currentWidth);
            obj.scaleY = (obj.scaleY || 1) * (targetHeight / currentHeight);
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Matched size to ${objects.length - 1} objects`);
        }
    }

    /**
     * Match width only (maintain aspect ratio)
     */
    public matchWidth(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple objects to match width');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        this.saveUndoState();

        const targetWidth = objects[0].getScaledWidth();

        objects.forEach((obj: any, index: number) => {
            if (index === 0) return;

            const currentWidth = obj.getScaledWidth();
            const scale = targetWidth / currentWidth;

            // Scale both dimensions to preserve aspect ratio
            obj.scaleX = (obj.scaleX || 1) * scale;
            obj.scaleY = (obj.scaleY || 1) * scale;
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Matched width`);
        }
    }

    /**
     * Match height only (maintain aspect ratio)
     */
    public matchHeight(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple objects to match height');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        this.saveUndoState();

        const targetHeight = objects[0].getScaledHeight();

        objects.forEach((obj: any, index: number) => {
            if (index === 0) return;

            const currentHeight = obj.getScaledHeight();
            const scale = targetHeight / currentHeight;

            obj.scaleX = (obj.scaleX || 1) * scale;
            obj.scaleY = (obj.scaleY || 1) * scale;
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Matched height`);
        }
    }

    /**
     * Reset object size to original (100%)
     */
    public resetSize(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.scaleX = 1;
                obj.scaleY = 1;
                obj.setCoords();
            });
        } else {
            active.scaleX = 1;
            active.scaleY = 1;
            active.setCoords();
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Reset to original size');
        }
    }

    /**
     * Flip selected objects horizontally
     */
    public flipHorizontal(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.flipX = !obj.flipX;
            });
        } else {
            active.flipX = !active.flipX;
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Flipped horizontally');
        }
    }

    /**
     * Flip selected objects vertically
     */
    public flipVertical(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.flipY = !obj.flipY;
            });
        } else {
            active.flipY = !active.flipY;
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Flipped vertically');
        }
    }

    /**
     * Rotate selected objects by specified degrees
     */
    public rotateObjects(degrees: number): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.angle = ((obj.angle || 0) + degrees) % 360;
                obj.setCoords();
            });
        } else {
            active.angle = ((active.angle || 0) + degrees) % 360;
            active.setCoords();
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Rotated ${degrees}°`);
        }
    }

    /**
     * Group selected objects
     */
    public groupObjects(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple objects to group');
            }
            return;
        }

        this.saveUndoState();

        const group = (activeObject as any).toGroup();
        this.canvas.setActiveObject(group);
        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Objects grouped');
        }
    }

    /**
     * Ungroup selected group
     */
    public ungroupObjects(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active || active.type !== 'group') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select a group to ungroup');
            }
            return;
        }

        this.saveUndoState();

        const selection = (active as any).toActiveSelection();
        this.canvas.setActiveObject(selection);
        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback('Group ungrouped');
        }
    }

    /**
     * Align selected plots by their axis positions.
     * Uses axes_bbox_px from metadata to align Y-axes (left edge) and X-axes (bottom edge).
     * The first selected object is the reference - others align to it.
     */
    /**
     * Align by axis with direction support (like regular alignment)
     * @param direction - L=left(Y-axis), C=center-H, R=right, T=top, M=middle-V, B=bottom(X-axis)
     */
    public alignByAxis(direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' = 'L'): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select objects to align by axis');
            }
            return;
        }

        // Get objects to align
        let objects: any[];
        if (active.type === 'activeSelection') {
            objects = (active as any).getObjects();
        } else {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple plots to align by axis');
            }
            return;
        }

        // Filter to only objects with axis metadata
        const plotsWithMeta = objects.filter((obj: any) => obj.axisMetadata?.axes_bbox_px);

        // Debug logging
        console.log(`[CanvasManager] alignByAxis(${direction}): ${objects.length} objects, ${plotsWithMeta.length} have axis metadata`);
        objects.forEach((obj: any, i: number) => {
            console.log(`  [${i}] ${obj.name || obj.type}: axisMetadata=${obj.axisMetadata ? 'yes' : 'no'}`);
        });

        if (plotsWithMeta.length < 2) {
            const withoutMeta = objects.length - plotsWithMeta.length;
            if (this.statusBarCallback) {
                this.statusBarCallback(`Need 2+ plots with axis metadata (${withoutMeta} missing metadata)`);
            }
            return;
        }

        this.saveUndoState();

        // First object is the reference
        const refObj = plotsWithMeta[0];
        const refMeta = refObj.axisMetadata.axes_bbox_px;
        const refScaleX = refObj.scaleX || 1;
        const refScaleY = refObj.scaleY || 1;

        // Reference axis positions in canvas coordinates based on direction
        let refPosition: number;
        const isHorizontal = ['L', 'C', 'R'].includes(direction);

        if (direction === 'L') {
            // Y-axis left edge
            refPosition = refObj.left + refMeta.x0 * refScaleX;
        } else if (direction === 'C') {
            // Horizontal center of plot area
            refPosition = refObj.left + ((refMeta.x0 + refMeta.x1) / 2) * refScaleX;
        } else if (direction === 'R') {
            // Right edge of plot area
            refPosition = refObj.left + refMeta.x1 * refScaleX;
        } else if (direction === 'T') {
            // Top edge of plot area
            refPosition = refObj.top + refMeta.y0 * refScaleY;
        } else if (direction === 'M') {
            // Vertical center of plot area
            refPosition = refObj.top + ((refMeta.y0 + refMeta.y1) / 2) * refScaleY;
        } else {
            // B = Bottom (X-axis)
            refPosition = refObj.top + refMeta.y1 * refScaleY;
        }

        let alignedCount = 0;

        // Align remaining objects to the reference
        for (let i = 1; i < plotsWithMeta.length; i++) {
            const obj = plotsWithMeta[i];
            const meta = obj.axisMetadata.axes_bbox_px;
            const scaleX = obj.scaleX || 1;
            const scaleY = obj.scaleY || 1;

            let currentPosition: number;
            if (direction === 'L') {
                currentPosition = obj.left + meta.x0 * scaleX;
            } else if (direction === 'C') {
                currentPosition = obj.left + ((meta.x0 + meta.x1) / 2) * scaleX;
            } else if (direction === 'R') {
                currentPosition = obj.left + meta.x1 * scaleX;
            } else if (direction === 'T') {
                currentPosition = obj.top + meta.y0 * scaleY;
            } else if (direction === 'M') {
                currentPosition = obj.top + ((meta.y0 + meta.y1) / 2) * scaleY;
            } else {
                currentPosition = obj.top + meta.y1 * scaleY;
            }

            const delta = refPosition - currentPosition;

            if (isHorizontal) {
                obj.left = (obj.left || 0) + delta;
            } else {
                obj.top = (obj.top || 0) + delta;
            }
            obj.setCoords();
            alignedCount++;
        }

        // Refresh the selection
        this.canvas.discardActiveObject();
        const selection = new (window as any).fabric.ActiveSelection(plotsWithMeta, {
            canvas: this.canvas
        });
        this.canvas.setActiveObject(selection);
        this.canvas.renderAll();
        this.saveCanvasContent();

        const dirNames: Record<string, string> = {
            'L': 'Y-axis (left)',
            'C': 'center-H',
            'R': 'right edge',
            'T': 'top edge',
            'M': 'center-V',
            'B': 'X-axis (bottom)'
        };

        if (this.statusBarCallback) {
            this.statusBarCallback(`Aligned ${alignedCount + 1} plots by ${dirNames[direction]}`);
        }
    }

    /**
     * Stack selected plots vertically with Y-axis alignment.
     * First aligns Y-axes (left edges), then stacks plots so each plot's
     * top edge touches the previous plot's X-axis (bottom edge).
     * Order is determined by current vertical position (top to bottom).
     */
    public stackVertically(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select objects to stack vertically');
            }
            return;
        }

        let objects: any[];
        if (active.type === 'activeSelection') {
            objects = (active as any).getObjects();
        } else {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple plots to stack');
            }
            return;
        }

        // Filter to only objects with axis metadata
        const plotsWithMeta = objects.filter((obj: any) => obj.axisMetadata?.axes_bbox_px);

        if (plotsWithMeta.length < 2) {
            const withoutMeta = objects.length - plotsWithMeta.length;
            if (this.statusBarCallback) {
                this.statusBarCallback(`Need 2+ plots with axis metadata (${withoutMeta} missing metadata)`);
            }
            return;
        }

        this.saveUndoState();

        // Sort plots by current vertical position (top to bottom)
        plotsWithMeta.sort((a: any, b: any) => (a.top || 0) - (b.top || 0));

        // First pass: align all Y-axes (left edges) to the first plot
        const refObj = plotsWithMeta[0];
        const refMeta = refObj.axisMetadata.axes_bbox_px;
        const refScaleX = refObj.scaleX || 1;
        const refYAxisX = refObj.left + refMeta.x0 * refScaleX;

        for (let i = 1; i < plotsWithMeta.length; i++) {
            const obj = plotsWithMeta[i];
            const meta = obj.axisMetadata.axes_bbox_px;
            const scaleX = obj.scaleX || 1;
            const currentYAxisX = obj.left + meta.x0 * scaleX;
            const deltaX = refYAxisX - currentYAxisX;
            obj.left = (obj.left || 0) + deltaX;
        }

        // Second pass: stack vertically (each plot's top at previous plot's X-axis)
        for (let i = 1; i < plotsWithMeta.length; i++) {
            const prevObj = plotsWithMeta[i - 1];
            const prevMeta = prevObj.axisMetadata.axes_bbox_px;
            const prevScaleY = prevObj.scaleY || 1;
            // Previous plot's X-axis (bottom of plot area) in canvas coordinates
            const prevXAxisY = prevObj.top + prevMeta.y1 * prevScaleY;

            const obj = plotsWithMeta[i];
            const meta = obj.axisMetadata.axes_bbox_px;
            const scaleY = obj.scaleY || 1;
            // Current plot's top of plot area in canvas coordinates
            const currentPlotTopY = obj.top + meta.y0 * scaleY;

            // Move this plot so its plot area top aligns with previous plot's X-axis
            const deltaY = prevXAxisY - currentPlotTopY;
            obj.top = (obj.top || 0) + deltaY;
            obj.setCoords();
        }

        // Update coordinates for first plot too
        refObj.setCoords();

        // Refresh the selection
        this.canvas.discardActiveObject();
        const selection = new (window as any).fabric.ActiveSelection(plotsWithMeta, {
            canvas: this.canvas
        });
        this.canvas.setActiveObject(selection);
        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Stacked ${plotsWithMeta.length} plots vertically with aligned Y-axes`);
        }
    }

    // Store debug lines for cleanup
    private axisDebugLines: any[] = [];

    /**
     * Show debug lines indicating axis positions on figures
     * Red = Y-axis (x0), Blue = X-axis (y1), Green = plot bounds
     */
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

    private elementSelectionTarget: any = null;
    private elementSelectionOverlay: HTMLCanvasElement | null = null;
    private selectedElementNames: Set<string> = new Set();  // Multi-selection support
    private hoveredElementName: string | null = null;
    private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void;

    /**
     * Set callback for element selection changes
     */
    public setElementSelectionCallback(callback: (elementNames: string[], elementInfos: any[]) => void): void {
        this.elementSelectionCallback = callback;
    }

    /**
     * Get currently selected element names
     */
    public getSelectedElementNames(): string[] {
        return Array.from(this.selectedElementNames);
    }

    /**
     * Enter element selection mode for a plot image
     */
    private enterElementSelectionMode(target: any, pointer?: { x: number, y: number }): void {
        if (!target.axisMetadata?.element_bboxes) {
            console.warn('[CanvasManager] No element_bboxes on target');
            return;
        }

        // Don't re-enter if already in element selection mode for this target
        if (this.elementSelectionTarget === target) {
            return;
        }

        this.elementSelectionTarget = target;
        const bboxes = target.axisMetadata.element_bboxes;
        const elementKeys = Object.keys(bboxes);
        console.log('[CanvasManager] Entering element selection mode', elementKeys);
        // Debug: Check if path_simplified is available
        for (const key of elementKeys) {
            const bbox = bboxes[key];
            console.log(`[CanvasManager] Element ${key}:`, {
                hasPathSimplified: !!bbox.path_simplified,
                pathLength: bbox.path_simplified?.length || 0,
                hasBbox: !!bbox.bbox,
                elementType: bbox.element_type
            });
        }

        // Create overlay canvas for element highlights
        this.createElementOverlay(target);

        // If pointer provided and valid, try to select element at that position
        if (pointer && pointer.x !== 0 && pointer.y !== 0) {
            const element = this.findElementAtPosition(pointer.x, pointer.y);
            if (element) {
                this.selectElement(element);
            }
        }

        if (this.statusBarCallback) {
            this.statusBarCallback('Element selection mode - Click to select, Ctrl+Click to multi-select');
        }
    }

    /**
     * Exit element selection mode
     */
    public exitElementSelectionMode(): void {
        if (!this.elementSelectionTarget) return;

        this.elementSelectionTarget = null;
        this.selectedElementNames.clear();
        this.hoveredElementName = null;

        // Remove overlay
        if (this.elementSelectionOverlay && this.elementSelectionOverlay.parentNode) {
            this.elementSelectionOverlay.parentNode.removeChild(this.elementSelectionOverlay);
        }
        this.elementSelectionOverlay = null;

        if (this.elementSelectionCallback) {
            this.elementSelectionCallback([], []);
        }

        if (this.statusBarCallback) {
            this.statusBarCallback('Exited element selection mode');
        }

        console.log('[CanvasManager] Exited element selection mode');
    }

    /**
     * Check if currently in element selection mode
     */
    public isInElementSelectionMode(): boolean {
        return this.elementSelectionTarget !== null;
    }

    /**
     * Create overlay canvas for element highlights
     */
    private createElementOverlay(target: any): void {
        // Remove any existing overlay
        if (this.elementSelectionOverlay && this.elementSelectionOverlay.parentNode) {
            this.elementSelectionOverlay.parentNode.removeChild(this.elementSelectionOverlay);
        }

        const canvasEl = this.canvas?.getElement();
        if (!canvasEl) return;

        const container = canvasEl.parentElement;
        if (!container) return;

        // Create overlay canvas
        const overlay = document.createElement('canvas');
        overlay.id = 'element-selection-overlay';
        overlay.style.position = 'absolute';
        overlay.style.pointerEvents = 'none';
        overlay.style.left = '0';
        overlay.style.top = '0';
        overlay.width = canvasEl.width;
        overlay.height = canvasEl.height;
        overlay.style.zIndex = '10';

        container.style.position = 'relative';
        container.appendChild(overlay);
        this.elementSelectionOverlay = overlay;

        // Setup mouse events for element detection
        this.setupElementSelectionEvents();
    }

    /**
     * Setup mouse events for element selection
     */
    private setupElementSelectionEvents(): void {
        if (!this.canvas) return;

        // Store handler reference for cleanup
        const mouseMoveHandler = (e: any) => {
            if (!this.elementSelectionTarget) return;

            const pointer = this.canvas.getPointer(e.e);
            const element = this.findElementAtPosition(pointer.x, pointer.y);

            if (element !== this.hoveredElementName) {
                this.hoveredElementName = element;
                this.updateElementOverlay();
            }
        };

        const mouseDownHandler = (e: any) => {
            if (!this.elementSelectionTarget) return;

            // Check if click is outside the target image
            const target = e.target;
            if (target !== this.elementSelectionTarget) {
                this.exitElementSelectionMode();
                return;
            }

            const pointer = this.canvas.getPointer(e.e);
            const isMultiSelect = e.e.ctrlKey || e.e.shiftKey;

            // Alt+click for cycle selection
            if (e.e.altKey) {
                const element = this.cycleElementSelection(pointer.x, pointer.y);
                if (element) {
                    this.selectElement(element, isMultiSelect);
                }
            } else {
                const element = this.findElementAtPosition(pointer.x, pointer.y);
                if (element) {
                    this.selectElement(element, isMultiSelect);
                }
            }
        };

        this.canvas.on('mouse:move', mouseMoveHandler);
        this.canvas.on('mouse:down', mouseDownHandler);

        // Store handlers for cleanup (simple approach - they get removed when canvas is disposed)
        (this.canvas as any)._elementSelectionMouseMove = mouseMoveHandler;
        (this.canvas as any)._elementSelectionMouseDown = mouseDownHandler;
    }

    /**
     * Find element at canvas position
     */
    private findElementAtPosition(canvasX: number, canvasY: number): string | null {
        if (!this.elementSelectionTarget) return null;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return null;

        // Convert canvas position to image-local position
        // Fabric.js uses center origin by default, so left/top are center coords
        const imgScaleX = target.scaleX || 1;
        const imgScaleY = target.scaleY || 1;
        const imgWidth = target.width || 0;
        const imgHeight = target.height || 0;

        // Get figure_size_px from metadata - bbox coordinates are in figure pixels
        const figureSize = target.axisMetadata?.figure_size_px;
        const figureWidth = figureSize?.width || imgWidth;
        const figureHeight = figureSize?.height || imgHeight;

        // Convert center coords to top-left corner
        const imgLeft = (target.left || 0) - (imgWidth * imgScaleX / 2);
        const imgTop = (target.top || 0) - (imgHeight * imgScaleY / 2);

        // Position relative to image (in object pixels)
        const objX = (canvasX - imgLeft) / imgScaleX;
        const objY = (canvasY - imgTop) / imgScaleY;

        // Check if point is inside image bounds
        if (objX < 0 || objX > imgWidth || objY < 0 || objY > imgHeight) {
            return null;
        }

        // Convert object pixels to figure pixels for hit detection
        // bbox/path_simplified coordinates are in figure pixels
        const figX = objX * (figureWidth / imgWidth);
        const figY = objY * (figureHeight / imgHeight);

        // Use the imported ElementSelectionManager for hit detection
        return this.findElementAtImageCoords(bboxes, figX, figY);
    }

    /**
     * Find element at image coordinates (reimplemented inline for simplicity)
     */
    private findElementAtImageCoords(bboxes: any, imgX: number, imgY: number): string | null {
        const PROXIMITY_THRESHOLD = 15;
        const SCATTER_THRESHOLD = 20;

        // First: Check for data elements with points/path_simplified (lines, scatter)
        let closestDataElement: string | null = null;
        let minDistance = Infinity;

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            // Support both old 'points' and new 'path_simplified' formats
            const points = bbox.points || bbox.path_simplified;
            // Get bbox coords - support both old (x0,y0,x1,y1) and new (bbox.x0,...) formats
            const bboxCoords = bbox.bbox || bbox;
            const x0 = bboxCoords.x0 ?? 0;
            const y0 = bboxCoords.y0 ?? 0;
            const x1 = bboxCoords.x1 ?? 0;
            const y1 = bboxCoords.y1 ?? 0;

            if (points && points.length > 0) {
                if (imgX >= x0 - SCATTER_THRESHOLD &&
                    imgX <= x1 + SCATTER_THRESHOLD &&
                    imgY >= y0 - SCATTER_THRESHOLD &&
                    imgY <= y1 + SCATTER_THRESHOLD) {

                    const elementType = bbox.element_type || 'line';
                    let dist: number;

                    if (elementType === 'scatter') {
                        dist = this.distanceToNearestPoint(imgX, imgY, points);
                    } else {
                        dist = this.distanceToLine(imgX, imgY, points);
                    }

                    if (dist < minDistance) {
                        minDistance = dist;
                        closestDataElement = name;
                    }
                }
            }
        }

        if (closestDataElement) {
            const bbox = bboxes[closestDataElement];
            const threshold = (bbox.element_type === 'scatter') ? SCATTER_THRESHOLD : PROXIMITY_THRESHOLD;
            if (minDistance <= threshold) {
                return closestDataElement;
            }
        }

        // Second: Check bbox containment
        const matches: { name: string; area: number; isPanel: boolean }[] = [];

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            // Support both old (x0,y0,x1,y1) and new (bbox.x0,...) formats
            const bboxCoords = bbox.bbox || bbox;
            const x0 = bboxCoords.x0 ?? 0;
            const y0 = bboxCoords.y0 ?? 0;
            const x1 = bboxCoords.x1 ?? 0;
            const y1 = bboxCoords.y1 ?? 0;

            if (imgX >= x0 && imgX <= x1 && imgY >= y0 && imgY <= y1) {
                const area = (x1 - x0) * (y1 - y0);
                const isPanel = bbox.is_panel || name === 'panel' || name.endsWith('_panel');
                const hasPoints = bbox.points || bbox.path_simplified;

                if (!hasPoints || hasPoints.length === 0) {
                    matches.push({ name, area, isPanel });
                }
            }
        }

        // Return smallest non-panel element
        const nonPanels = matches.filter(m => !m.isPanel);
        if (nonPanels.length > 0) {
            nonPanels.sort((a, b) => a.area - b.area);
            return nonPanels[0].name;
        }

        // Fallback to panel
        const panels = matches.filter(m => m.isPanel);
        if (panels.length > 0) {
            panels.sort((a, b) => a.area - b.area);
            return panels[0].name;
        }

        return null;
    }

    private distanceToNearestPoint(px: number, py: number, points: number[][]): number {
        let minDist = Infinity;
        for (const [x, y] of points) {
            const dist = Math.sqrt((px - x) ** 2 + (py - y) ** 2);
            if (dist < minDist) minDist = dist;
        }
        return minDist;
    }

    private distanceToLine(px: number, py: number, points: number[][]): number {
        let minDist = Infinity;
        for (let i = 0; i < points.length - 1; i++) {
            const [x1, y1] = points[i];
            const [x2, y2] = points[i + 1];
            const dist = this.distanceToSegment(px, py, x1, y1, x2, y2);
            if (dist < minDist) minDist = dist;
        }
        return minDist;
    }

    private distanceToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const lenSq = dx * dx + dy * dy;
        if (lenSq === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
        let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
        t = Math.max(0, Math.min(1, t));
        const projX = x1 + t * dx;
        const projY = y1 + t * dy;
        return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2);
    }

    // Cycle selection state
    private elementsAtCursor: string[] = [];
    private currentCycleIndex: number = 0;

    private cycleElementSelection(canvasX: number, canvasY: number): string | null {
        if (!this.elementSelectionTarget) return null;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return null;

        // Convert to image coords (then to figure coords)
        const imgScaleX = target.scaleX || 1;
        const imgScaleY = target.scaleY || 1;
        const imgWidth = target.width || 0;
        const imgHeight = target.height || 0;

        // Get figure_size_px from metadata - bbox coordinates are in figure pixels
        const figureSize = target.axisMetadata?.figure_size_px;
        const figureWidth = figureSize?.width || imgWidth;
        const figureHeight = figureSize?.height || imgHeight;

        // Convert center coords to top-left corner
        const imgLeft = (target.left || 0) - (imgWidth * imgScaleX / 2);
        const imgTop = (target.top || 0) - (imgHeight * imgScaleY / 2);

        // Position relative to image (in object pixels)
        const objX = (canvasX - imgLeft) / imgScaleX;
        const objY = (canvasY - imgTop) / imgScaleY;

        // Convert object pixels to figure pixels for hit detection
        const figX = objX * (figureWidth / imgWidth);
        const figY = objY * (figureHeight / imgHeight);

        // Find all elements at position
        const allElements = this.findAllElementsAtImageCoords(bboxes, figX, figY);

        if (allElements.length > 0) {
            if (JSON.stringify(allElements) !== JSON.stringify(this.elementsAtCursor)) {
                this.elementsAtCursor = allElements;
                this.currentCycleIndex = 0;
            } else {
                this.currentCycleIndex = (this.currentCycleIndex + 1) % this.elementsAtCursor.length;
            }

            const total = this.elementsAtCursor.length;
            const current = this.currentCycleIndex + 1;
            console.log(`[ElementSelection] Cycle: ${current}/${total}`);

            return this.elementsAtCursor[this.currentCycleIndex];
        }

        return null;
    }

    private findAllElementsAtImageCoords(bboxes: any, imgX: number, imgY: number): string[] {
        const PROXIMITY_THRESHOLD = 15;
        const SCATTER_THRESHOLD = 20;
        const results: { name: string; priority: number; distance: number }[] = [];

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            let match = false;
            let distance = Infinity;
            let priority = 0;

            const hasPoints = bbox.points && bbox.points.length > 0;
            const elementType = bbox.element_type || '';
            const isPanel = bbox.is_panel || name === 'panel' || name.endsWith('_panel');

            if (hasPoints) {
                if (imgX >= bbox.x0 - SCATTER_THRESHOLD && imgX <= bbox.x1 + SCATTER_THRESHOLD &&
                    imgY >= bbox.y0 - SCATTER_THRESHOLD && imgY <= bbox.y1 + SCATTER_THRESHOLD) {
                    if (elementType === 'scatter') {
                        distance = this.distanceToNearestPoint(imgX, imgY, bbox.points);
                        if (distance <= SCATTER_THRESHOLD) { match = true; priority = 1; }
                    } else {
                        distance = this.distanceToLine(imgX, imgY, bbox.points);
                        if (distance <= PROXIMITY_THRESHOLD) { match = true; priority = 2; }
                    }
                }
            }

            if (imgX >= bbox.x0 && imgX <= bbox.x1 && imgY >= bbox.y0 && imgY <= bbox.y1) {
                const area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0);
                if (!match) { match = true; distance = 0; }
                if (isPanel) { priority = 100; }
                else if (!hasPoints) { priority = 10 + Math.min(area / 10000, 50); }
            }

            if (match) { results.push({ name, priority, distance }); }
        }

        results.sort((a, b) => a.priority !== b.priority ? a.priority - b.priority : a.distance - b.distance);
        return results.map(r => r.name);
    }

    /**
     * Select an element by name (supports multi-selection with Ctrl/Shift)
     */
    private selectElement(elementName: string, addToSelection: boolean = false): void {
        const bboxes = this.elementSelectionTarget?.axisMetadata?.element_bboxes;

        if (addToSelection) {
            // Toggle selection: if already selected, remove; otherwise add
            if (this.selectedElementNames.has(elementName)) {
                this.selectedElementNames.delete(elementName);
            } else {
                this.selectedElementNames.add(elementName);
            }
        } else {
            // Single selection: clear others and select this one
            this.selectedElementNames.clear();
            this.selectedElementNames.add(elementName);
        }

        this.updateElementOverlay();

        // Build arrays of selected element names and infos
        const selectedNames = Array.from(this.selectedElementNames);
        const selectedInfos = selectedNames.map(name => bboxes?.[name]).filter(Boolean);

        if (this.elementSelectionCallback) {
            this.elementSelectionCallback(selectedNames, selectedInfos);
        }

        if (this.statusBarCallback) {
            if (selectedNames.length === 1) {
                const info = bboxes?.[selectedNames[0]];
                this.statusBarCallback(`Selected: ${info?.label || selectedNames[0]}`);
            } else if (selectedNames.length > 1) {
                const labels = selectedNames.map(n => bboxes?.[n]?.label || n).join(', ');
                this.statusBarCallback(`Selected ${selectedNames.length} elements: ${labels}`);
            }
        }

        console.log('[CanvasManager] Selected elements:', selectedNames);
    }

    /**
     * Clear element selection
     */
    public clearElementSelection(): void {
        this.selectedElementNames.clear();
        this.updateElementOverlay();

        if (this.elementSelectionCallback) {
            this.elementSelectionCallback([], []);
        }
    }

    /**
     * Update the element overlay to show current hover/selection
     */
    private updateElementOverlay(): void {
        if (!this.elementSelectionOverlay || !this.elementSelectionTarget) return;

        const ctx = this.elementSelectionOverlay.getContext('2d');
        if (!ctx) return;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return;

        // Clear overlay
        ctx.clearRect(0, 0, this.elementSelectionOverlay.width, this.elementSelectionOverlay.height);

        // Get viewport transform (for pan/zoom)
        const vpt = this.canvas?.viewportTransform || [1, 0, 0, 1, 0, 0];
        const zoom = vpt[0];  // Scale factor
        const panX = vpt[4];  // X translation
        const panY = vpt[5];  // Y translation

        // Get image transform - account for Fabric.js center origin
        const imgScaleX = target.scaleX || 1;
        const imgScaleY = target.scaleY || 1;
        const imgWidth = target.width || 0;
        const imgHeight = target.height || 0;

        // Get figure_size_px from metadata - coordinates are in figure pixels
        // The path_simplified coordinates are in the original figure coordinate system
        const figureSize = target.axisMetadata?.figure_size_px;
        const figureWidth = figureSize?.width || imgWidth;
        const figureHeight = figureSize?.height || imgHeight;

        // Calculate the ratio between Fabric object size and figure pixels
        // path_simplified coords are in figure pixels, need to convert to object pixels
        const figureToObjectScaleX = imgWidth / figureWidth;
        const figureToObjectScaleY = imgHeight / figureHeight;

        // Fabric.js uses center origin by default, so left/top are center coords
        // Convert to top-left corner position in CANVAS coordinates
        const canvasLeft = (target.left || 0) - (imgWidth * imgScaleX / 2);
        const canvasTop = (target.top || 0) - (imgHeight * imgScaleY / 2);

        // Apply viewport transform to get SCREEN coordinates
        const imgLeft = canvasLeft * zoom + panX;
        const imgTop = canvasTop * zoom + panY;

        // Total scale: figure pixels -> object pixels -> canvas pixels -> screen pixels
        const totalScaleX = figureToObjectScaleX * imgScaleX * zoom;
        const totalScaleY = figureToObjectScaleY * imgScaleY * zoom;

        console.log('[CanvasManager] updateElementOverlay scale calculation:', {
            figureSize: { width: figureWidth, height: figureHeight },
            objectSize: { width: imgWidth, height: imgHeight },
            figureToObjectScale: { x: figureToObjectScaleX, y: figureToObjectScaleY },
            imgScale: { x: imgScaleX, y: imgScaleY },
            zoom,
            totalScale: { x: totalScaleX, y: totalScaleY }
        });

        // Draw hovered element (if not already selected)
        if (this.hoveredElementName && !this.selectedElementNames.has(this.hoveredElementName)) {
            const bbox = bboxes[this.hoveredElementName];
            if (bbox) {
                this.drawElementHighlight(ctx, bbox, imgLeft, imgTop, totalScaleX, totalScaleY, 'hover');
            }
        }

        // Draw all selected elements
        for (const elementName of this.selectedElementNames) {
            const bbox = bboxes[elementName];
            if (bbox) {
                this.drawElementHighlight(ctx, bbox, imgLeft, imgTop, totalScaleX, totalScaleY, 'selected');
            }
        }
    }

    /**
     * Draw element highlight
     */
    private drawElementHighlight(
        ctx: CanvasRenderingContext2D,
        bbox: any,
        imgLeft: number,
        imgTop: number,
        scaleX: number,
        scaleY: number,
        type: 'hover' | 'selected'
    ): void {
        const color = type === 'hover' ? 'rgba(100, 200, 255, 0.5)' : 'rgba(255, 180, 100, 0.7)';
        const strokeColor = type === 'hover' ? 'rgba(100, 200, 255, 0.8)' : 'rgba(255, 140, 50, 0.9)';

        ctx.save();

        // Support both old 'points' and new 'path_simplified' formats
        const points = bbox.points || bbox.path_simplified;
        // Support both old (x0,y0,x1,y1) and new (bbox.x0,...) formats
        const bboxCoords = bbox.bbox || bbox;

        console.log(`[CanvasManager] drawElementHighlight:`, {
            hasPoints: !!points,
            pointsLength: points?.length || 0,
            elementType: bbox.element_type,
            bboxKeys: Object.keys(bbox)
        });

        // If element has points (line/scatter), draw along the path
        if (points && points.length > 1) {
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = type === 'hover' ? 3 : 4;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            if (bbox.element_type === 'scatter') {
                ctx.fillStyle = color;
                for (const [x, y] of points) {
                    ctx.beginPath();
                    ctx.arc(imgLeft + x * scaleX, imgTop + y * scaleY, 6, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.stroke();
                }
            } else {
                ctx.beginPath();
                ctx.moveTo(imgLeft + points[0][0] * scaleX, imgTop + points[0][1] * scaleY);
                for (let i = 1; i < points.length; i++) {
                    ctx.lineTo(imgLeft + points[i][0] * scaleX, imgTop + points[i][1] * scaleY);
                }
                ctx.stroke();
            }
        } else {
            // Draw rectangle for elements without path data
            const x0 = bboxCoords.x0 ?? 0;
            const y0 = bboxCoords.y0 ?? 0;
            const x1 = bboxCoords.x1 ?? 0;
            const y1 = bboxCoords.y1 ?? 0;
            const x = imgLeft + x0 * scaleX;
            const y = imgTop + y0 * scaleY;
            const w = (x1 - x0) * scaleX;
            const h = (y1 - y0) * scaleY;

            ctx.fillStyle = color;
            ctx.fillRect(x, y, w, h);
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);
        }

        // Draw label
        const labelX = imgLeft + bbox.x0 * scaleX;
        const labelY = imgTop + bbox.y0 * scaleY - 5;
        ctx.fillStyle = strokeColor;
        ctx.font = '12px sans-serif';
        ctx.fillText(bbox.label || '', labelX, labelY);

        ctx.restore();
    }

    // =========================================================================
    // Statistics Integration
    // =========================================================================

    /**
     * Extract group data from selected objects for statistical testing.
     * Supports both:
     * 1. Multiple Fabric objects selected (multi-object selection)
     * 2. Multiple elements selected within a single plot image (element-level selection)
     */
    private extractGroupsFromSelection(): { name: string; values: number[] }[] {
        if (!this.canvas) return [];

        const groups: { name: string; values: number[] }[] = [];

        console.log('[Stats] extractGroupsFromSelection called');
        console.log('[Stats] elementSelectionTarget:', this.elementSelectionTarget);
        console.log('[Stats] selectedElementNames:', Array.from(this.selectedElementNames));

        // Check if we're in element selection mode with multiple elements selected
        if (this.elementSelectionTarget && this.selectedElementNames.size > 0) {
            const target = this.elementSelectionTarget;
            const bboxes = target.axisMetadata?.element_bboxes;
            const csvData = target.csvData || target.axisMetadata?.csv_data;

            console.log('[Stats] bboxes:', bboxes);
            console.log('[Stats] csvData:', csvData);

            if (bboxes && csvData) {
                for (const elementName of this.selectedElementNames) {
                    const bbox = bboxes[elementName];
                    if (bbox) {
                        // Extract data for this element (e.g., boxplot group)
                        const elementData = this.extractElementData(elementName, bbox, csvData, target);
                        if (elementData && elementData.values.length > 0) {
                            groups.push(elementData);
                        }
                    }
                }
            }

            // If we got groups from element selection, return them
            if (groups.length > 0) {
                return groups;
            }
        }

        // Fallback: Extract from multiple Fabric objects selected
        const activeObjects = this.canvas.getActiveObjects();

        for (const obj of activeObjects) {
            // Check if object has plot data attached
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

    /**
     * Extract data values for a specific element within a plot
     */
    private extractElementData(
        elementName: string,
        bbox: any,
        csvData: any,
        target: any
    ): { name: string; values: number[] } | null {
        const elementType = bbox.element_type;
        const label = bbox.label || elementName;

        // Handle boxplot elements - try to find corresponding data column
        if (elementType === 'boxplot' || elementName.startsWith('boxplot_')) {
            // Extract boxplot index from name (e.g., "boxplot_0" -> 0)
            const match = elementName.match(/boxplot_(\d+)/);
            if (match) {
                const boxIndex = parseInt(match[1], 10);

                // Try to get data from CSV columns
                // Boxplots typically have data in Y columns corresponding to each box
                if (csvData && csvData.rows && csvData.columns) {
                    // Look for Y-value column for this box
                    const yColPatterns = [
                        `y_${boxIndex}`,
                        `value_${boxIndex}`,
                        csvData.columns[boxIndex + 1], // Skip x column
                    ];

                    for (const pattern of yColPatterns) {
                        if (csvData.columns.includes(pattern)) {
                            const values = csvData.rows
                                .map((row: any) => parseFloat(row[pattern]))
                                .filter((v: number) => !isNaN(v));

                            if (values.length > 0) {
                                return { name: label, values };
                            }
                        }
                    }

                    // If columns don't match pattern, try direct column index
                    // Box plots often have data organized as groups
                    const colName = csvData.columns[boxIndex + 1]; // +1 to skip index column
                    if (colName) {
                        const values = csvData.rows
                            .map((row: any) => parseFloat(row[colName]))
                            .filter((v: number) => !isNaN(v));

                        if (values.length > 0) {
                            return { name: label, values };
                        }
                    }
                }
            }
        }

        // Handle bar elements
        if (elementType === 'bar' || elementName.startsWith('bar_')) {
            // Similar extraction logic for bars
            // For now, return the bbox metadata if it contains values
            if (bbox.values && Array.isArray(bbox.values)) {
                return { name: label, values: bbox.values };
            }
        }

        // Check if element has direct values attached
        if (bbox.values && Array.isArray(bbox.values)) {
            return { name: label, values: bbox.values };
        }

        // Try to infer from trace_idx
        if (typeof bbox.trace_idx === 'number' && csvData) {
            const colIdx = bbox.trace_idx + 1; // +1 to skip index column
            const colName = csvData.columns?.[colIdx];
            if (colName) {
                const values = csvData.rows
                    ?.map((row: any) => parseFloat(row[colName]))
                    .filter((v: number) => !isNaN(v));

                if (values && values.length > 0) {
                    return { name: label, values };
                }
            }
        }

        console.warn(`[CanvasManager] Could not extract data for element: ${elementName}`);
        return null;
    }

    /**
     * Run the recommended statistical test
     */
    private async runRecommendedStatTest(): Promise<void> {
        const groups = this.extractGroupsFromSelection();

        if (groups.length < 2) {
            console.warn('[Stats] Need at least 2 groups selected for comparison');
            return;
        }

        try {
            // Get recommended test
            const contextResp = await fetch('/vis/api/stats/context/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plot_type: 'boxplot',
                    data: { groups },
                    metadata: {},
                }),
            });

            const contextData = await contextResp.json();
            if (!contextData.success || !contextData.recommended.length) {
                console.warn('[Stats] No recommended test found');
                return;
            }

            const testName = contextData.recommended[0];

            // Run the test
            const testResp = await fetch('/vis/api/stats/run/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    test_name: testName,
                    groups,
                    paired: false,
                }),
            });

            const testData = await testResp.json();
            if (!testData.success) {
                console.error('[Stats] Test failed:', testData.error);
                return;
            }

            // Add bracket annotation to canvas
            this.addStatBracketAnnotation(testData.annotation, groups);

            console.log('[Stats] Test result:', testData.result);
        } catch (error) {
            console.error('[Stats] Error running test:', error);
        }
    }

    /**
     * Run all applicable statistical tests
     */
    private async runAllStatTests(): Promise<void> {
        const groups = this.extractGroupsFromSelection();

        if (groups.length < 2) {
            console.warn('[Stats] Need at least 2 groups selected');
            return;
        }

        try {
            const response = await fetch('/vis/api/stats/run-all/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    groups,
                    outcome_type: 'continuous',
                    design: 'between',
                    paired: false,
                    correction_method: 'fdr_bh',
                    include_effect_sizes: true,
                }),
            });

            const data = await response.json();
            if (!data.success) {
                console.error('[Stats] Run all failed:', data.error);
                return;
            }

            // Show inspector panel with results
            this.showStatsInspectorPanel(data.inspector_data);

            console.log('[Stats] All tests complete:', data.results);
        } catch (error) {
            console.error('[Stats] Error running all tests:', error);
        }
    }

    /**
     * Show test selector dialog
     */
    private async showStatTestSelector(): Promise<void> {
        const groups = this.extractGroupsFromSelection();

        if (groups.length < 2) {
            console.warn('[Stats] Need at least 2 groups selected');
            return;
        }

        // Import stats manager dynamically to avoid circular deps
        const { statsManager } = await import('./StatsManager.ts');

        // Get mouse position for context menu
        const rect = this.canvas?.upperCanvasEl.getBoundingClientRect();
        const x = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
        const y = rect ? rect.top + rect.height / 2 : window.innerHeight / 2;

        statsManager.showContextMenu(x, y, groups, async (testName: string) => {
            // Run selected test
            try {
                const response = await fetch('/vis/api/stats/run/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        test_name: testName,
                        groups,
                        paired: false,
                    }),
                });

                const data = await response.json();
                if (data.success) {
                    this.addStatBracketAnnotation(data.annotation, groups);
                }
            } catch (error) {
                console.error('[Stats] Error:', error);
            }
        });
    }

    /**
     * Open the Stats Inspector panel
     */
    private openStatsInspector(): void {
        // Create empty inspector if no data yet
        this.showStatsInspectorPanel({ tests: [], effects: [] });
    }

    /**
     * Show Stats Inspector panel with data
     */
    private showStatsInspectorPanel(data: { tests: any[]; effects: any[] }): void {
        let panel = document.getElementById('stats-inspector-panel');

        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'stats-inspector-panel';
            panel.className = 'stats-inspector-panel';
            document.body.appendChild(panel);
        }

        const formatP = (p: number | null): string => {
            if (p === null) return '-';
            if (p < 0.001) return '< 0.001 ***';
            if (p < 0.01) return `${p.toFixed(3)} **`;
            if (p < 0.05) return `${p.toFixed(3)} *`;
            return `${p.toFixed(3)} ns`;
        };

        panel.innerHTML = `
            <div class="stats-inspector-header">
                <span>Statistics Inspector</span>
                <button class="close-btn">&times;</button>
            </div>
            <div class="stats-inspector-content">
                <h4>Tests</h4>
                ${data.tests.length > 0 ? `
                    <table class="stats-table">
                        <thead>
                            <tr><th>Test</th><th>p-value</th><th>Stat</th></tr>
                        </thead>
                        <tbody>
                            ${data.tests.map(t => `
                                <tr>
                                    <td>${t.label || t.name}</td>
                                    <td>${formatP(t.p_adj || t.p_raw)}</td>
                                    <td>${t.stat?.toFixed(3) || '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p>No tests run yet</p>'}

                ${data.effects.length > 0 ? `
                    <h4>Effect Sizes</h4>
                    <table class="stats-table">
                        <thead>
                            <tr><th>Measure</th><th>Value</th><th>Interpretation</th></tr>
                        </thead>
                        <tbody>
                            ${data.effects.map(e => `
                                <tr>
                                    <td>${e.label || e.name}</td>
                                    <td>${e.value?.toFixed(3) || '-'}</td>
                                    <td>${e.note || '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : ''}
            </div>
        `;

        // Add close button handler
        const closeBtn = panel.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                panel!.style.display = 'none';
            });
        }

        panel.style.display = 'block';
    }

    /**
     * Add statistical bracket annotation to canvas
     */
    private addStatBracketAnnotation(
        annotation: any,
        groups: { name: string; values: number[] }[]
    ): void {
        if (!this.canvas) return;

        const activeObjects = this.canvas.getActiveObjects();
        if (activeObjects.length < 2) return;

        // Get positions of first two objects for bracket
        const obj1 = activeObjects[0];
        const obj2 = activeObjects[1];

        const x1 = obj1.left! + (obj1.width! * (obj1.scaleX || 1)) / 2;
        const x2 = obj2.left! + (obj2.width! * (obj2.scaleX || 1)) / 2;
        const topY = Math.min(obj1.top!, obj2.top!) - 30;

        const bracketHeight = annotation.bracket_style?.bracket_height || 5;
        const starOffset = annotation.bracket_style?.star_offset || 3;

        // Create bracket lines using fabric.js
        const leftLine = new fabric.Line(
            [x1, topY + bracketHeight, x1, topY],
            { stroke: '#000000', strokeWidth: 1 }
        );

        const rightLine = new fabric.Line(
            [x2, topY + bracketHeight, x2, topY],
            { stroke: '#000000', strokeWidth: 1 }
        );

        const topLine = new fabric.Line(
            [x1, topY, x2, topY],
            { stroke: '#000000', strokeWidth: 1 }
        );

        // Create stars text
        const starsText = new fabric.Text(annotation.stars || 'ns', {
            left: (x1 + x2) / 2,
            top: topY - starOffset - 14,
            fontSize: 14,
            fontFamily: 'Arial',
            originX: 'center',
            fill: '#000000',
        });

        // Group all elements
        const group = new fabric.Group([leftLine, rightLine, topLine, starsText], {
            selectable: true,
            hasControls: true,
            lockRotation: true,
        });

        // Store annotation data for serialization
        (group as any).statAnnotation = annotation;
        (group as any).objectType = 'stat_bracket';

        this.canvas.add(group);
        this.canvas.renderAll();

        console.log('[Stats] Added bracket annotation:', annotation.stars);
    }

    /**
     * Export canvas as PNG
     */
    public exportAsPng(): void {
        if (!this.canvas) return;

        const dataUrl = this.canvas.toDataURL({
            format: 'png',
            quality: 1,
            multiplier: 2  // 2x resolution for better quality
        });

        const link = document.createElement('a');
        link.download = `figure-${Date.now()}.png`;
        link.href = dataUrl;
        link.click();

        if (this.statusBarCallback) {
            this.statusBarCallback('Exported as PNG');
        }
    }

    /**
     * Export canvas as SVG
     */
    public exportAsSvg(): void {
        if (!this.canvas) return;

        const svg = this.canvas.toSVG();
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.download = `figure-${Date.now()}.svg`;
        link.href = url;
        link.click();

        URL.revokeObjectURL(url);

        if (this.statusBarCallback) {
            this.statusBarCallback('Exported as SVG');
        }
    }

    /**
     * Export canvas as PDF (requires jsPDF library)
     */
    public exportAsPdf(): void {
        if (!this.canvas) return;

        // Check if jsPDF is available
        const jsPDF = (window as any).jspdf?.jsPDF || (window as any).jsPDF;
        if (!jsPDF) {
            console.warn('[CanvasManager] jsPDF not available, falling back to PNG');
            if (this.statusBarCallback) {
                this.statusBarCallback('PDF export requires jsPDF library');
            }
            return;
        }

        const dataUrl = this.canvas.toDataURL({
            format: 'png',
            quality: 1,
            multiplier: 2
        });

        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();

        // Create PDF with canvas dimensions (in mm)
        const pxToMm = 0.264583;  // 1px = 0.264583mm at 96 DPI
        const pdfWidth = canvasWidth * pxToMm;
        const pdfHeight = canvasHeight * pxToMm;

        const pdf = new jsPDF({
            orientation: pdfWidth > pdfHeight ? 'landscape' : 'portrait',
            unit: 'mm',
            format: [pdfWidth, pdfHeight]
        });

        pdf.addImage(dataUrl, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save(`figure-${Date.now()}.pdf`);

        if (this.statusBarCallback) {
            this.statusBarCallback('Exported as PDF');
        }
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
