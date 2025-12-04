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

    constructor(
        private statusBarCallback?: (message: string) => void,
        private rulersAreaTransformCallback?: () => void
    ) {}

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
                selectionKey: 'ctrlKey',  // PowerPoint-style multi-select
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
        } catch (error) {
            console.error('[CanvasManager] Error initializing canvas:', error);
        }
    }

    /**
     * Draw grid using pre-rendered static SVG files
     * PERFORMANCE: Static SVG files are cached by browser
     */
    public drawGrid(isDark: boolean = false): void {
        if (!this.canvas) return;

        const startTime = performance.now();

        // Use pre-rendered static SVG files for maximum performance
        const gridUrl = isDark
            ? '/static/vis_app/img/vis/grid-dark.svg'
            : '/static/vis_app/img/vis/grid-light.svg';

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

        // Clear background image (SVG grid)
        this.canvas.setBackgroundImage(null, this.canvas.renderAll.bind(this.canvas));

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

        // Update canvas background color
        this.canvas.backgroundColor = isDark ? '#2a2a2a' : '#ffffff';

        // Redraw grid with appropriate color if grid is enabled
        if (this.gridEnabled) {
            this.drawGrid(isDark);
        }

        this.canvas.renderAll();
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
            }
        });

        // Mouse move - Handle panning or zoom dragging
        canvasContainer.addEventListener('mousemove', (e: MouseEvent) => {
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

                this.canvasPanOffset.x += deltaX;
                this.canvasPanOffset.y += deltaY;

                // Throttle updates using requestAnimationFrame
                if (!this.pendingDragUpdate) {
                    this.pendingDragUpdate = true;
                    this.canvasDragThrottleFrame = requestAnimationFrame(() => {
                        this.updateCanvasTransform();
                        if (this.rulersAreaTransformCallback) {
                            this.rulersAreaTransformCallback();
                        }
                        this.pendingDragUpdate = false;
                    });
                }

                this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
            }
        });

        // Mouse up - Reset panning or zoom dragging
        canvasContainer.addEventListener('mouseup', () => {
            if (this.canvasIsZoomDragging) {
                this.canvasIsZoomDragging = false;
                canvasContainer.style.cursor = 'default';
                console.log('[CanvasManager] Canvas zoom drag mode ended');
            }
            if (this.canvasIsPanning) {
                this.canvasIsPanning = false;
                this.canvasPanStartPoint = null;
                canvasContainer.style.cursor = 'default';
                console.log('[CanvasManager] Canvas pan mode ended');
            }

            // Cancel any pending throttled updates
            if (this.canvasDragThrottleFrame !== null) {
                cancelAnimationFrame(this.canvasDragThrottleFrame);
                this.canvasDragThrottleFrame = null;
                this.pendingDragUpdate = false;
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
        this.canvas.renderAll();
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
     */
    public addImage(src: string, options: {
        left?: number;
        top?: number;
        scaleToFit?: boolean;
        maxWidth?: number;
        maxHeight?: number;
        selectable?: boolean;
        name?: string;
    } = {}): Promise<any> {
        return new Promise((resolve, reject) => {
            if (!this.canvas) {
                reject(new Error('Canvas not initialized'));
                return;
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

                // Position
                img.set({
                    left: options.left ?? (CANVAS_CONSTANTS.MAX_CANVAS_WIDTH - (img.width! * (img.scaleX || 1))) / 2,
                    top: options.top ?? (CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT - (img.height! * (img.scaleY || 1))) / 2,
                    selectable: options.selectable !== false,
                    name: options.name || 'figure',
                });

                this.canvas!.add(img);
                this.canvas!.setActiveObject(img);
                this.canvas!.renderAll();

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
     * Remove active object
     */
    public removeActiveObject(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (active) {
            this.canvas.remove(active);
            this.canvas.renderAll();

            if (this.statusBarCallback) {
                this.statusBarCallback('Object removed');
            }
        }
    }
}
