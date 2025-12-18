/**
 * ElementSelectionManager - Coordinates element-level selection within plot images
 *
 * Responsibilities:
 * - Element selection mode state management
 * - Mouse event handling and coordination
 * - Multi-selection support
 * - Delegates to specialized managers for:
 *   - HitmapManager: Fast 24-bit RGB ID picking
 *   - HitDetector: Geometry-based fallback detection
 *   - ElementHighlighter: Visual overlay and highlighting
 *   - StatsExtractor: Data extraction for statistical analysis
 *
 * Refactored from 1051 lines - extracted hitmap, highlighting, hit detection, and stats.
 */

import { HitmapManager, HitmapColorMap } from './HitmapManager.js';
import { ElementHighlighter, HighlightType } from './ElementHighlighter.js';
import { HitDetector } from './HitDetector.js';
import { StatsExtractor, GroupData, StatsData } from './StatsExtractor.js';

export class ElementSelectionManager {
    // Extracted managers
    private hitmapManager: HitmapManager;
    private highlighter: ElementHighlighter;
    private hitDetector: HitDetector;
    private statsExtractor: StatsExtractor;

    // Selection state
    private elementSelectionTarget: any = null;
    private selectedElementNames: Set<string> = new Set();
    private hoveredElementName: string | null = null;
    private elementSelectionCallback?: (elementNames: string[], elementInfos: any[]) => void;

    // Cycle selection state
    private elementsAtCursor: string[] = [];
    private currentCycleIndex: number = 0;

    constructor(
        private canvas: any,
        private statusBarCallback?: (message: string) => void
    ) {
        this.hitmapManager = new HitmapManager();
        this.highlighter = new ElementHighlighter();
        this.hitDetector = new HitDetector();
        this.statsExtractor = new StatsExtractor();
    }

    // ========== HITMAP DELEGATION ==========

    public async loadHitmap(hitmapUrl: string, colorMap: HitmapColorMap): Promise<void> {
        return this.hitmapManager.load(hitmapUrl, colorMap);
    }

    public isHitmapReady(): boolean {
        return this.hitmapManager.isReady();
    }

    public clearHitmap(): void {
        this.hitmapManager.clear();
    }

    public findElementByHitmap(
        imgX: number, imgY: number,
        imgWidth: number, imgHeight: number,
        radius: number = 2
    ): string | null {
        return this.hitmapManager.findElement(imgX, imgY, imgWidth, imgHeight, radius);
    }

    public findAllElementsByHitmap(
        imgX: number, imgY: number,
        imgWidth: number, imgHeight: number,
        radius: number = 3
    ): string[] {
        return this.hitmapManager.findAllElements(imgX, imgY, imgWidth, imgHeight, radius);
    }

    // ========== SELECTION CALLBACK ==========

    public setElementSelectionCallback(callback: (elementNames: string[], elementInfos: any[]) => void): void {
        this.elementSelectionCallback = callback;
    }

    public getSelectedElementNames(): string[] {
        return Array.from(this.selectedElementNames);
    }

    // ========== SELECTION MODE MANAGEMENT ==========

    public enterElementSelectionMode(target: any, pointer?: { x: number, y: number }): void {
        if (!target.axisMetadata?.element_bboxes) {
            console.warn('[ElementSelectionManager] No element_bboxes on target');
            return;
        }

        if (this.elementSelectionTarget === target) {
            return;
        }

        this.elementSelectionTarget = target;
        const bboxes = target.axisMetadata.element_bboxes;
        const elementKeys = Object.keys(bboxes);
        console.log('[ElementSelectionManager] Entering element selection mode', elementKeys);

        // Load hitmap if available
        if (target.axisMetadata?.hitmap && target.axisMetadata?.hitmap_color_map) {
            this.loadHitmap(target.axisMetadata.hitmap, target.axisMetadata.hitmap_color_map)
                .then(() => console.log('[ElementSelectionManager] Hitmap loaded for fast picking'))
                .catch(e => console.log('[ElementSelectionManager] Hitmap load failed, using bbox fallback:', e));
        }

        // Debug log element info
        for (const key of elementKeys) {
            const bbox = bboxes[key];
            console.log(`[ElementSelectionManager] Element ${key}:`, {
                hasPathSimplified: !!bbox.path_simplified,
                pathLength: bbox.path_simplified?.length || 0,
                hasBbox: !!bbox.bbox,
                elementType: bbox.element_type
            });
        }

        this.createElementOverlay(target);

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

    public exitElementSelectionMode(): void {
        if (!this.elementSelectionTarget) return;

        this.elementSelectionTarget = null;
        this.selectedElementNames.clear();
        this.hoveredElementName = null;

        this.highlighter.removeOverlay();

        if (this.elementSelectionCallback) {
            this.elementSelectionCallback([], []);
        }

        if (this.statusBarCallback) {
            this.statusBarCallback('Exited element selection mode');
        }

        console.log('[ElementSelectionManager] Exited element selection mode');
    }

    public isInElementSelectionMode(): boolean {
        return this.elementSelectionTarget !== null;
    }

    // ========== OVERLAY AND EVENTS ==========

    public createElementOverlay(target: any): void {
        const canvasEl = this.canvas?.getElement();
        if (!canvasEl) return;

        this.highlighter.createOverlay(canvasEl);
        this.setupElementSelectionEvents();
    }

    public setupElementSelectionEvents(): void {
        if (!this.canvas) return;

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

            const target = e.target;
            if (target !== this.elementSelectionTarget) {
                this.exitElementSelectionMode();
                return;
            }

            const pointer = this.canvas.getPointer(e.e);
            const isMultiSelect = e.e.ctrlKey || e.e.shiftKey;

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

        (this.canvas as any)._elementSelectionMouseMove = mouseMoveHandler;
        (this.canvas as any)._elementSelectionMouseDown = mouseDownHandler;
    }

    // ========== HIT DETECTION ==========

    public findElementAtPosition(canvasX: number, canvasY: number): string | null {
        if (!this.elementSelectionTarget) return null;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return null;

        const { objX, objY, imgWidth, imgHeight, figX, figY } = this.convertCanvasToImageCoords(canvasX, canvasY);

        if (objX < 0 || objX > imgWidth || objY < 0 || objY > imgHeight) {
            return null;
        }

        // Fast path: hitmap
        if (this.isHitmapReady()) {
            const element = this.findElementByHitmap(objX, objY, imgWidth, imgHeight);
            if (element) return element;
        }

        // Fallback: geometry-based detection
        return this.hitDetector.findElementAtImageCoords(bboxes, figX, figY);
    }

    public findElementAtImageCoords(bboxes: any, imgX: number, imgY: number): string | null {
        return this.hitDetector.findElementAtImageCoords(bboxes, imgX, imgY);
    }

    public cycleElementSelection(canvasX: number, canvasY: number): string | null {
        if (!this.elementSelectionTarget) return null;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return null;

        const { figX, figY } = this.convertCanvasToImageCoords(canvasX, canvasY);
        const allElements = this.hitDetector.findAllElementsAtImageCoords(bboxes, figX, figY);

        if (allElements.length > 0) {
            if (JSON.stringify(allElements) !== JSON.stringify(this.elementsAtCursor)) {
                this.elementsAtCursor = allElements;
                this.currentCycleIndex = 0;
            } else {
                this.currentCycleIndex = (this.currentCycleIndex + 1) % this.elementsAtCursor.length;
            }

            console.log(`[ElementSelectionManager] Cycle: ${this.currentCycleIndex + 1}/${this.elementsAtCursor.length}`);
            return this.elementsAtCursor[this.currentCycleIndex];
        }

        return null;
    }

    // ========== SELECTION MANAGEMENT ==========

    public selectElement(elementName: string, addToSelection: boolean = false): void {
        const bboxes = this.elementSelectionTarget?.axisMetadata?.element_bboxes;

        if (addToSelection) {
            if (this.selectedElementNames.has(elementName)) {
                this.selectedElementNames.delete(elementName);
            } else {
                this.selectedElementNames.add(elementName);
            }
        } else {
            this.selectedElementNames.clear();
            this.selectedElementNames.add(elementName);
        }

        this.updateElementOverlay();

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

    public clearElementSelection(): void {
        this.selectedElementNames.clear();
        this.updateElementOverlay();

        if (this.elementSelectionCallback) {
            this.elementSelectionCallback([], []);
        }
    }

    // ========== OVERLAY UPDATE ==========

    public updateElementOverlay(): void {
        if (!this.elementSelectionTarget) return;

        const target = this.elementSelectionTarget;
        const bboxes = target.axisMetadata?.element_bboxes;
        if (!bboxes) return;

        this.highlighter.clear();

        const { imgLeft, imgTop, totalScaleX, totalScaleY } = this.getImageTransform();

        // Draw hovered element
        if (this.hoveredElementName && !this.selectedElementNames.has(this.hoveredElementName)) {
            const bbox = bboxes[this.hoveredElementName];
            if (bbox) {
                this.highlighter.drawHighlight(bbox, imgLeft, imgTop, totalScaleX, totalScaleY, 'hover');
            }
        }

        // Draw selected elements
        for (const elementName of this.selectedElementNames) {
            const bbox = bboxes[elementName];
            if (bbox) {
                this.highlighter.drawHighlight(bbox, imgLeft, imgTop, totalScaleX, totalScaleY, 'selected');
            }
        }
    }

    public drawElementHighlight(
        ctx: CanvasRenderingContext2D,
        bbox: any,
        imgLeft: number,
        imgTop: number,
        scaleX: number,
        scaleY: number,
        type: HighlightType
    ): void {
        this.highlighter.drawHighlight(bbox, imgLeft, imgTop, scaleX, scaleY, type);
    }

    // ========== STATS EXTRACTION ==========

    public extractGroupsFromSelection(csvData: any): GroupData[] {
        return this.statsExtractor.extractGroupsFromSelection(
            this.selectedElementNames,
            this.elementSelectionTarget,
            csvData
        );
    }

    public extractElementData(
        elementName: string,
        bbox: any,
        csvData: any,
        target: any
    ): GroupData | null {
        return this.statsExtractor.extractElementData(elementName, bbox, csvData, target);
    }

    public openStatsInspector(): void {
        console.log('[ElementSelectionManager] Open stats inspector');
    }

    public showStatsInspectorPanel(data: StatsData): void {
        this.statsExtractor.showStatsInspectorPanel(data);
    }

    public addStatBracketAnnotation(
        annotation: any,
        groups: GroupData[]
    ): void {
        console.log('[ElementSelectionManager] Add stat bracket annotation:', annotation);
    }

    // ========== COORDINATE CONVERSION HELPERS ==========

    private convertCanvasToImageCoords(canvasX: number, canvasY: number): {
        objX: number; objY: number;
        imgWidth: number; imgHeight: number;
        figX: number; figY: number;
    } {
        const target = this.elementSelectionTarget;
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

        return { objX, objY, imgWidth, imgHeight, figX, figY };
    }

    private getImageTransform(): {
        imgLeft: number; imgTop: number;
        totalScaleX: number; totalScaleY: number;
    } {
        const target = this.elementSelectionTarget;
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

        return { imgLeft, imgTop, totalScaleX, totalScaleY };
    }
}
