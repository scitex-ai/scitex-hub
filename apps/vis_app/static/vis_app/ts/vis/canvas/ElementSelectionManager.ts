/**
 * ElementSelectionManager - Handles element-level selection within plot images
 *
 * Responsibilities:
 * - Element selection mode state management
 * - Element overlay creation and management
 * - Mouse event handling for element detection
 * - Hit detection using bounding boxes, paths, AND hitmap (if available)
 * - Multi-selection support
 * - Element highlighting and visual feedback
 * - Data extraction for statistical analysis
 *
 * Hit Detection Strategy:
 * 1. Hitmap (if loaded): Fast 24-bit RGB ID lookup with neighborhood sampling
 * 2. Fallback: Legacy bbox/geometry-based proximity detection
 *
 * Phase 5 refactoring - extracted from CanvasManager.ts
 */

// Hitmap types
interface HitmapElementInfo {
    id: number;
    type: string;
    label: string;
    axes_index: number;
    rgb: [number, number, number];
}

interface HitmapColorMap {
    [id: string]: HitmapElementInfo;
}

export class ElementSelectionManager {
    // Hitmap data for fast picking
    private hitmapImageData: ImageData | null = null;
    private hitmapColorMap: Map<number, HitmapElementInfo> = new Map();
    private hitmapWidth: number = 0;
    private hitmapHeight: number = 0;
    // Selection state
    private elementSelectionTarget: any = null;
    private elementSelectionOverlay: HTMLCanvasElement | null = null;
    private selectedElementNames: Set<string> = new Set();
    private hoveredElementName: string | null = null;
    private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void;

    // Cycle selection state
    private elementsAtCursor: string[] = [];
    private currentCycleIndex: number = 0;

    // Hit detection thresholds
    private readonly PROXIMITY_THRESHOLD = 15;
    private readonly SCATTER_THRESHOLD = 20;

    constructor(
        private canvas: any,
        private statusBarCallback?: (message: string) => void
    ) {}

    // ========== HITMAP METHODS (Fast 24-bit RGB ID picking) ==========

    /**
     * Load hitmap from PNG URL and color map
     * @param hitmapUrl - URL to plot_hitmap.png
     * @param colorMap - Mapping from element ID to element info
     */
    public async loadHitmap(hitmapUrl: string, colorMap: HitmapColorMap): Promise<void> {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';

            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');

                if (!ctx) {
                    reject(new Error('Failed to get 2D context'));
                    return;
                }

                ctx.drawImage(img, 0, 0);
                this.hitmapImageData = ctx.getImageData(0, 0, img.width, img.height);
                this.hitmapWidth = img.width;
                this.hitmapHeight = img.height;

                // Build ID -> info map
                this.hitmapColorMap.clear();
                for (const [idStr, info] of Object.entries(colorMap)) {
                    const id = parseInt(idStr, 10);
                    if (!isNaN(id)) {
                        this.hitmapColorMap.set(id, info);
                    }
                }

                console.log(`[ElementSelectionManager] Loaded hitmap ${this.hitmapWidth}x${this.hitmapHeight} with ${this.hitmapColorMap.size} elements`);
                resolve();
            };

            img.onerror = () => reject(new Error(`Failed to load hitmap: ${hitmapUrl}`));
            img.src = hitmapUrl;
        });
    }

    /**
     * Check if hitmap is loaded
     */
    public isHitmapReady(): boolean {
        return this.hitmapImageData !== null;
    }

    /**
     * Clear hitmap data
     */
    public clearHitmap(): void {
        this.hitmapImageData = null;
        this.hitmapColorMap.clear();
        this.hitmapWidth = 0;
        this.hitmapHeight = 0;
    }

    /**
     * Decode RGB to element ID (24-bit encoding)
     */
    private rgbToId(r: number, g: number, b: number): number {
        return (r << 16) | (g << 8) | b;
    }

    /**
     * Find element using hitmap with neighborhood sampling
     * @param imgX - X in image pixels
     * @param imgY - Y in image pixels
     * @param imgWidth - Image display width
     * @param imgHeight - Image display height
     * @param radius - Neighborhood radius (default 2 = 5x5)
     */
    public findElementByHitmap(
        imgX: number,
        imgY: number,
        imgWidth: number,
        imgHeight: number,
        radius: number = 2
    ): string | null {
        if (!this.hitmapImageData) return null;

        // Scale to hitmap coordinates
        const hx = Math.floor((imgX / imgWidth) * this.hitmapWidth);
        const hy = Math.floor((imgY / imgHeight) * this.hitmapHeight);

        const data = this.hitmapImageData.data;
        const foundIds = new Map<number, number>(); // id -> min distance

        // Sample neighborhood
        for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
                const px = hx + dx;
                const py = hy + dy;

                if (px >= 0 && px < this.hitmapWidth && py >= 0 && py < this.hitmapHeight) {
                    const idx = (py * this.hitmapWidth + px) * 4;
                    const id = this.rgbToId(data[idx], data[idx + 1], data[idx + 2]);

                    if (id > 0 && this.hitmapColorMap.has(id)) {
                        const dist = Math.abs(dx) + Math.abs(dy);
                        const existing = foundIds.get(id);
                        if (existing === undefined || dist < existing) {
                            foundIds.set(id, dist);
                        }
                    }
                }
            }
        }

        if (foundIds.size === 0) return null;

        // Return closest element's label
        const sorted = [...foundIds.entries()].sort((a, b) => a[1] - b[1]);
        const info = this.hitmapColorMap.get(sorted[0][0]);
        return info?.label || null;
    }

    /**
     * Find all elements at position using hitmap (for cycle selection)
     */
    public findAllElementsByHitmap(
        imgX: number,
        imgY: number,
        imgWidth: number,
        imgHeight: number,
        radius: number = 3
    ): string[] {
        if (!this.hitmapImageData) return [];

        const hx = Math.floor((imgX / imgWidth) * this.hitmapWidth);
        const hy = Math.floor((imgY / imgHeight) * this.hitmapHeight);

        const data = this.hitmapImageData.data;
        const foundIds = new Map<number, number>();

        for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
                const px = hx + dx;
                const py = hy + dy;

                if (px >= 0 && px < this.hitmapWidth && py >= 0 && py < this.hitmapHeight) {
                    const idx = (py * this.hitmapWidth + px) * 4;
                    const id = this.rgbToId(data[idx], data[idx + 1], data[idx + 2]);

                    if (id > 0 && this.hitmapColorMap.has(id)) {
                        const dist = Math.abs(dx) + Math.abs(dy);
                        const existing = foundIds.get(id);
                        if (existing === undefined || dist < existing) {
                            foundIds.set(id, dist);
                        }
                    }
                }
            }
        }

        const sorted = [...foundIds.entries()].sort((a, b) => a[1] - b[1]);
        return sorted.map(([id]) => this.hitmapColorMap.get(id)?.label || '').filter(Boolean);
    }

    // ========== END HITMAP METHODS ==========

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
    public enterElementSelectionMode(target: any, pointer?: { x: number, y: number }): void {
        if (!target.axisMetadata?.element_bboxes) {
            console.warn('[ElementSelectionManager] No element_bboxes on target');
            return;
        }

        // Don't re-enter if already in element selection mode for this target
        if (this.elementSelectionTarget === target) {
            return;
        }

        this.elementSelectionTarget = target;
        const bboxes = target.axisMetadata.element_bboxes;
        const elementKeys = Object.keys(bboxes);
        console.log('[ElementSelectionManager] Entering element selection mode', elementKeys);

        // Load hitmap if available (for fast element picking)
        if (target.axisMetadata?.hitmap && target.axisMetadata?.hitmap_color_map) {
            this.loadHitmap(target.axisMetadata.hitmap, target.axisMetadata.hitmap_color_map)
                .then(() => console.log('[ElementSelectionManager] Hitmap loaded for fast picking'))
                .catch(e => console.log('[ElementSelectionManager] Hitmap load failed, using bbox fallback:', e));
        }

        // Debug: Check if path_simplified is available
        for (const key of elementKeys) {
            const bbox = bboxes[key];
            console.log(`[ElementSelectionManager] Element ${key}:`, {
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

        console.log('[ElementSelectionManager] Exited element selection mode');
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
    public createElementOverlay(target: any): void {
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
    public setupElementSelectionEvents(): void {
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
     * Uses hitmap if available (fast), falls back to bbox/geometry detection
     */
    public findElementAtPosition(canvasX: number, canvasY: number): string | null {
        if (!this.elementSelectionTarget) return null;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return null;

        // Convert canvas position to image-local position
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

        // FAST PATH: Use hitmap if available
        if (this.isHitmapReady()) {
            const element = this.findElementByHitmap(objX, objY, imgWidth, imgHeight);
            if (element) return element;
        }

        // FALLBACK: Convert object pixels to figure pixels for geometry-based hit detection
        const figX = objX * (figureWidth / imgWidth);
        const figY = objY * (figureHeight / imgHeight);

        return this.findElementAtImageCoords(bboxes, figX, figY);
    }

    /**
     * Find element at image coordinates
     */
    public findElementAtImageCoords(bboxes: any, imgX: number, imgY: number): string | null {
        // First: Check for data elements with points/path_simplified (lines, scatter)
        let closestDataElement: string | null = null;
        let minDistance = Infinity;

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            const points = bbox.points || bbox.path_simplified;
            const bboxCoords = bbox.bbox || bbox;
            const x0 = bboxCoords.x0 ?? 0;
            const y0 = bboxCoords.y0 ?? 0;
            const x1 = bboxCoords.x1 ?? 0;
            const y1 = bboxCoords.y1 ?? 0;

            if (points && points.length > 0) {
                if (imgX >= x0 - this.SCATTER_THRESHOLD &&
                    imgX <= x1 + this.SCATTER_THRESHOLD &&
                    imgY >= y0 - this.SCATTER_THRESHOLD &&
                    imgY <= y1 + this.SCATTER_THRESHOLD) {

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
            const threshold = (bbox.element_type === 'scatter') ? this.SCATTER_THRESHOLD : this.PROXIMITY_THRESHOLD;
            if (minDistance <= threshold) {
                return closestDataElement;
            }
        }

        // Second: Check bbox containment
        const matches: { name: string; area: number; isPanel: boolean }[] = [];

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
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

    /**
     * Cycle through overlapping elements at cursor position
     */
    public cycleElementSelection(canvasX: number, canvasY: number): string | null {
        if (!this.elementSelectionTarget) return null;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return null;

        // Convert to image coords (then to figure coords)
        const imgScaleX = target.scaleX || 1;
        const imgScaleY = target.scaleY || 1;
        const imgWidth = target.width || 0;
        const imgHeight = target.height || 0;

        const figureSize = target.axisMetadata?.figure_size_px;
        const figureWidth = figureSize?.width || imgWidth;
        const figureHeight = figureSize?.height || imgHeight;

        const imgLeft = (target.left || 0) - (imgWidth * imgScaleX / 2);
        const imgTop = (target.top || 0) - (imgHeight * imgScaleY / 2);

        const objX = (canvasX - imgLeft) / imgScaleX;
        const objY = (canvasY - imgTop) / imgScaleY;

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
            console.log(`[ElementSelectionManager] Cycle: ${current}/${total}`);

            return this.elementsAtCursor[this.currentCycleIndex];
        }

        return null;
    }

    /**
     * Select an element by name (supports multi-selection with Ctrl/Shift)
     */
    public selectElement(elementName: string, addToSelection: boolean = false): void {
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

        console.log('[ElementSelectionManager] Selected elements:', selectedNames);
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
    public updateElementOverlay(): void {
        if (!this.elementSelectionOverlay || !this.elementSelectionTarget) return;

        const ctx = this.elementSelectionOverlay.getContext('2d');
        if (!ctx) return;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return;

        // Clear overlay
        ctx.clearRect(0, 0, this.elementSelectionOverlay.width, this.elementSelectionOverlay.height);

        // Get image transform
        const imgScaleX = target.scaleX || 1;
        const imgScaleY = target.scaleY || 1;
        const imgWidth = target.width || 0;
        const imgHeight = target.height || 0;

        const figureSize = target.axisMetadata?.figure_size_px;
        const figureWidth = figureSize?.width || imgWidth;
        const figureHeight = figureSize?.height || imgHeight;

        const figureToObjectScaleX = imgWidth / figureWidth;
        const figureToObjectScaleY = imgHeight / figureHeight;

        const imgLeft = (target.left || 0) - (imgWidth * imgScaleX / 2);
        const imgTop = (target.top || 0) - (imgHeight * imgScaleY / 2);

        const totalScaleX = figureToObjectScaleX * imgScaleX;
        const totalScaleY = figureToObjectScaleY * imgScaleY;

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
    public drawElementHighlight(
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

        const points = bbox.points || bbox.path_simplified;
        const bboxCoords = bbox.bbox || bbox;

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

    /**
     * Extract group data from selected elements for statistical testing
     */
    public extractGroupsFromSelection(csvData: any): { name: string; values: number[] }[] {
        const groups: { name: string; values: number[] }[] = [];

        if (!this.elementSelectionTarget || this.selectedElementNames.size === 0) {
            return groups;
        }

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;

        if (bboxes && csvData) {
            for (const elementName of this.selectedElementNames) {
                const bbox = bboxes[elementName];
                if (bbox) {
                    const elementData = this.extractElementData(elementName, bbox, csvData, target);
                    if (elementData && elementData.values.length > 0) {
                        groups.push(elementData);
                    }
                }
            }
        }

        return groups;
    }

    /**
     * Extract data values for a specific element within a plot
     */
    public extractElementData(
        elementName: string,
        bbox: any,
        csvData: any,
        target: any
    ): { name: string; values: number[] } | null {
        const elementType = bbox.element_type;
        const label = bbox.label || elementName;

        // Handle boxplot elements
        if (elementType === 'boxplot' || elementName.startsWith('boxplot_')) {
            const match = elementName.match(/boxplot_(\d+)/);
            if (match) {
                const boxIndex = parseInt(match[1], 10);

                if (csvData && csvData.rows && csvData.columns) {
                    const yColPatterns = [
                        `y_${boxIndex}`,
                        `value_${boxIndex}`,
                        csvData.columns[boxIndex + 1],
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

                    const colName = csvData.columns[boxIndex + 1];
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
            const colIdx = bbox.trace_idx + 1;
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

        console.warn(`[ElementSelectionManager] Could not extract data for element: ${elementName}`);
        return null;
    }

    /**
     * Open the Stats Inspector panel
     */
    public openStatsInspector(): void {
        // Trigger stats inspector - implementation depends on integration
        console.log('[ElementSelectionManager] Open stats inspector');
    }

    /**
     * Show Stats Inspector panel with data
     */
    public showStatsInspectorPanel(data: { tests: any[]; effects: any[] }): void {
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
    public addStatBracketAnnotation(
        annotation: any,
        groups: { name: string; values: number[] }[]
    ): void {
        // This would need the fabric canvas reference
        console.log('[ElementSelectionManager] Add stat bracket annotation:', annotation);
    }

    // ========== PRIVATE HELPER METHODS ==========

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

    private findAllElementsAtImageCoords(bboxes: any, imgX: number, imgY: number): string[] {
        const results: { name: string; priority: number; distance: number }[] = [];

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            let match = false;
            let distance = Infinity;
            let priority = 0;

            const hasPoints = bbox.points && bbox.points.length > 0;
            const elementType = bbox.element_type || '';
            const isPanel = bbox.is_panel || name === 'panel' || name.endsWith('_panel');

            if (hasPoints) {
                if (imgX >= bbox.x0 - this.SCATTER_THRESHOLD && imgX <= bbox.x1 + this.SCATTER_THRESHOLD &&
                    imgY >= bbox.y0 - this.SCATTER_THRESHOLD && imgY <= bbox.y1 + this.SCATTER_THRESHOLD) {
                    if (elementType === 'scatter') {
                        distance = this.distanceToNearestPoint(imgX, imgY, bbox.points);
                        if (distance <= this.SCATTER_THRESHOLD) { match = true; priority = 1; }
                    } else {
                        distance = this.distanceToLine(imgX, imgY, bbox.points);
                        if (distance <= this.PROXIMITY_THRESHOLD) { match = true; priority = 2; }
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
}
