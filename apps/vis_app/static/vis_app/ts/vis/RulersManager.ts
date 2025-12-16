/**
 * RulersManager - Handles all ruler rendering, unit toggling, and dragging
 *
 * Responsibilities:
 * - Initialize and draw all four rulers (top, bottom, left, right)
 * - Toggle between mm and inch units
 * - Render ruler markings with appropriate intervals
 * - Handle ruler dragging for canvas panning
 * - Synchronize ruler transform with canvas zoom/pan
 */

import { RulerUnit, CANVAS_CONSTANTS } from './types.ts';

export class RulersManager {
    private rulerUnit: RulerUnit = 'mm';
    private canvasZoomLevel: number = 0.22; // Start at 22% to match CanvasManager initial zoom
    private canvasPanOffset: { x: number, y: number } = { x: 0, y: 0 };
    private canvasIsPanning: boolean = false;
    private canvasPanStartPoint: { x: number, y: number } | null = null;
    private isDarkTheme: boolean = false;  // Track current theme for rulers
    private onTransformUpdate?: () => void;  // Callback to SigmaEditor for transform sync

    constructor(
        private canvas: any, // Fabric.js canvas instance
        private statusBarCallback?: (message: string) => void
    ) {}

    /**
     * Set callback for transform updates (called from SigmaEditor)
     */
    public setTransformCallback(callback: () => void): void {
        this.onTransformUpdate = callback;
    }

    /**
     * Get current ruler unit
     */
    public getRulerUnit(): RulerUnit {
        return this.rulerUnit;
    }

    /**
     * Set canvas zoom level (called from main editor)
     */
    public setCanvasZoomLevel(level: number): void {
        this.canvasZoomLevel = level;
    }

    /**
     * Set canvas pan offset (called from main editor)
     */
    public setCanvasPanOffset(offset: { x: number, y: number }): void {
        this.canvasPanOffset = offset;
    }

    /**
     * Get canvas pan offset (for coordination with other managers)
     */
    public getCanvasPanOffset(): { x: number, y: number } {
        return this.canvasPanOffset;
    }

    /**
     * Get canvas zoom level (for coordination with other managers)
     */
    public getCanvasZoomLevel(): number {
        return this.canvasZoomLevel;
    }

    /**
     * Initialize rulers on canvas load
     */
    public initializeRulers(): void {
        // Rulers follow GLOBAL theme, not canvas theme
        const globalTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
        this.isDarkTheme = globalTheme === 'dark';

        // Draw immediately
        this.drawRulers();

        // Also schedule a redraw after DOM is fully ready (belt and suspenders approach)
        requestAnimationFrame(() => {
            this.drawRulers();
        });
    }

    /**
     * Draw all rulers based on canvas dimensions
     * PERFORMANCE: Pre-rendered SVG instead of 840+ DOM elements
     */
    public drawRulers(): void {
        if (!this.canvas) {
            console.warn('[RulersManager] Cannot draw rulers: canvas not set');
            return;
        }

        const startTime = performance.now();
        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();
        const dpi = CANVAS_CONSTANTS.DPI;

        // Validate canvas dimensions
        if (!canvasWidth || !canvasHeight || canvasWidth <= 0 || canvasHeight <= 0) {
            console.warn(`[RulersManager] Invalid canvas dimensions: ${canvasWidth}x${canvasHeight}, retrying...`);
            // Retry after a short delay
            setTimeout(() => this.drawRulers(), 100);
            return;
        }

        // Check if SVG elements exist
        const rulerH = document.getElementById('ruler-h');
        const rulerV = document.getElementById('ruler-v');
        if (!rulerH || !rulerV) {
            console.warn('[RulersManager] Ruler SVG elements not found, retrying...');
            setTimeout(() => this.drawRulers(), 100);
            return;
        }

        // Render all four rulers with pre-generated SVG
        this.renderHorizontalRuler(canvasWidth, dpi, 'ruler-h');  // Top
        this.renderHorizontalRuler(canvasWidth, dpi, 'ruler-b');  // Bottom
        this.renderVerticalRuler(canvasHeight, dpi, 'ruler-v');   // Left
        this.renderVerticalRuler(canvasHeight, dpi, 'ruler-r');   // Right

        // Set up click handlers on ruler labels for unit toggle
        this.setupRulerLabelClickHandlers();

        const endTime = performance.now();
        console.log(`[RulersManager] ✅ All 4 rulers rendered in ${(endTime - startTime).toFixed(2)}ms (canvas: ${canvasWidth}x${canvasHeight})`);
    }

    /**
     * Set up click handlers on ruler labels for unit toggle
     * Click on any "0mm", "10mm", etc. label to toggle between mm and inch
     */
    private setupRulerLabelClickHandlers(): void {
        const rulerLabels = document.querySelectorAll('.ruler-label');
        rulerLabels.forEach(label => {
            // Remove existing listener to avoid duplicates
            label.removeEventListener('click', this.handleRulerLabelClick);
            label.addEventListener('click', this.handleRulerLabelClick);
        });
    }

    /**
     * Handle click on ruler label - toggle units
     */
    private handleRulerLabelClick = (e: Event): void => {
        e.stopPropagation();
        this.toggleRulerUnit();
    };

    /**
     * Toggle ruler unit between mm and inch
     */
    public toggleRulerUnit(): void {
        this.rulerUnit = this.rulerUnit === 'mm' ? 'inch' : 'mm';

        // Update button label (if it exists - for backward compatibility)
        const label = document.getElementById('ruler-unit-label');
        if (label) {
            label.textContent = this.rulerUnit;
        }

        // Redraw rulers with new unit
        this.drawRulers();

        console.log(`Ruler unit changed to: ${this.rulerUnit}`);
        if (this.statusBarCallback) {
            this.statusBarCallback(`Ruler units: ${this.rulerUnit}`);
        }
    }

    /**
     * Update ruler theme (light/dark)
     */
    public updateRulerTheme(isDark: boolean): void {
        this.isDarkTheme = isDark;
        this.drawRulers();  // Redraw with new theme colors
        console.log(`[RulersManager] Theme updated to ${isDark ? 'dark' : 'light'}`);
    }

    /**
     * Render horizontal ruler as pre-generated SVG (mm or inch)
     * PERFORMANCE: Generates complete SVG string instead of DOM manipulation
     */
    private renderHorizontalRuler(width: number, dpi: number, rulerId: string = 'ruler-h'): void {
        const svg = document.getElementById(rulerId);
        if (!svg) return;

        const rulerHeight = 60;
        svg.setAttribute('width', width.toString());
        svg.setAttribute('height', rulerHeight.toString());
        svg.setAttribute('viewBox', `0 0 ${width} ${rulerHeight}`);
        svg.style.width = `${width}px`;
        svg.style.height = `${rulerHeight}px`;

        // Generate complete SVG content as string
        if (this.rulerUnit === 'mm') {
            svg.innerHTML = this.generateHorizontalRulerMm(width, dpi, rulerHeight);
        } else {
            svg.innerHTML = this.generateHorizontalRulerInch(width, dpi, rulerHeight);
        }
    }

    /**
     * Generate horizontal ruler SVG with mm markings (pre-rendered)
     * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
     * THEME-AWARE: Adapts colors based on isDarkTheme
     */
    private generateHorizontalRulerMm(width: number, dpi: number, rulerHeight: number): string {
        const pxToMm = (px: number) => (px / dpi) * 25.4;
        const mmToPx = (mm: number) => (mm * dpi) / 25.4;

        // Theme-aware colors (light mode minor ticks made more visible)
        const majorColor = this.isDarkTheme ? '#ccc' : '#888';
        const textColor = this.isDarkTheme ? '#aaa' : '#555';
        const minorColor = this.isDarkTheme ? '#666' : '#aaa';

        const maxMm = pxToMm(width);
        const majorInterval = 10;  // 10mm
        const middleInterval = 5;   // 5mm
        const minorInterval = 1;    // 1mm

        let svgContent = '';

        // Add 0mm tick mark at origin
        svgContent += `<line x1="0" y1="40" x2="0" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1.5"/>`;
        svgContent += `<text x="3" y="35" text-anchor="start" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>0mm (click to toggle inch)</title>0mm</text>`;

        // Generate all tick marks
        for (let mm = minorInterval; mm <= maxMm; mm += minorInterval) {
            const x = mmToPx(mm);

            if (mm % majorInterval === 0) {
                // Major tick (10mm)
                svgContent += `<line x1="${x}" y1="40" x2="${x}" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1.5"/>`;
                svgContent += `<text x="${x}" y="35" text-anchor="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>${mm}mm (click to toggle inch)</title>${mm}mm</text>`;
            } else if (mm % middleInterval === 0) {
                // Middle tick (5mm)
                svgContent += `<line x1="${x}" y1="48" x2="${x}" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1"/>`;
            } else {
                // Minor tick (1mm)
                svgContent += `<line x1="${x}" y1="54" x2="${x}" y2="${rulerHeight}" stroke="${minorColor}" stroke-width="0.5"/>`;
            }
        }

        // Add column width markers (0.5, 1.0, 1.5, 2.0 columns)
        const columnMarkers = [
            { mm: 45, label: '0.5 col' },
            { mm: 90, label: '1.0 col' },
            { mm: 135, label: '1.5 col' },
            { mm: 180, label: '2.0 col' }
        ];

        // Column label color aligned with ruler text color
        const columnLabelColor = this.isDarkTheme ? '#aaa' : '#555';
        columnMarkers.forEach(marker => {
            const x = mmToPx(marker.mm);
            if (x <= width) {
                svgContent += `<text x="${x}" y="12" text-anchor="middle" font-size="11" fill="${columnLabelColor}" font-weight="500">${marker.label}</text>`;
            }
        });

        return svgContent;
    }

    /**
     * Generate horizontal ruler SVG with inch markings (pre-rendered)
     * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
     * THEME-AWARE: Adapts colors based on isDarkTheme
     */
    private generateHorizontalRulerInch(width: number, dpi: number, rulerHeight: number): string {
        const pxToInch = (px: number) => px / dpi;
        const inchToPx = (inch: number) => inch * dpi;

        // Theme-aware colors (light mode minor ticks made more visible)
        const majorColor = this.isDarkTheme ? '#ccc' : '#888';
        const textColor = this.isDarkTheme ? '#aaa' : '#555';
        const minorColor = this.isDarkTheme ? '#666' : '#aaa';

        const maxInch = pxToInch(width);
        let svgContent = '';

        // Full inch markers
        for (let inch = 0; inch <= maxInch; inch++) {
            const x = inchToPx(inch);
            svgContent += `<line x1="${x}" y1="40" x2="${x}" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1.5"/>`;
            if (inch === 0) {
                // Special handling for 0" - position like mm ruler to avoid being cut off
                svgContent += `<text x="3" y="35" text-anchor="start" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>0" (click to toggle mm)</title>0"</text>`;
            } else {
                svgContent += `<text x="${x}" y="35" text-anchor="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>${inch}" (click to toggle mm)</title>${inch}"</text>`;
            }
        }

        // Fractional inch markers (1/2, 1/4, 1/8, 1/16)
        const fractions = [
            { divisor: 2, y: 48, stroke: majorColor, width: '1' },
            { divisor: 4, y: 51, stroke: majorColor, width: '0.8' },
            { divisor: 8, y: 54, stroke: minorColor, width: '0.6' },
            { divisor: 16, y: 56, stroke: minorColor, width: '0.4' }
        ];

        fractions.forEach(frac => {
            for (let inch = 0; inch <= maxInch; inch++) {
                for (let i = 1; i < frac.divisor; i++) {
                    if (i % 2 === 0 && frac.divisor > 2) continue;
                    if (i % 4 === 0 && frac.divisor > 4) continue;
                    if (i % 8 === 0 && frac.divisor > 8) continue;

                    const position = inch + (i / frac.divisor);
                    const x = inchToPx(position);

                    if (x <= width) {
                        svgContent += `<line x1="${x}" y1="${frac.y}" x2="${x}" y2="${rulerHeight}" stroke="${frac.stroke}" stroke-width="${frac.width}"/>`;
                    }
                }
            }
        });

        // Column width markers (convert from mm to inch)
        const columnMarkersInch = [
            { inch: 45 / 25.4, label: '0.5 col' },
            { inch: 90 / 25.4, label: '1.0 col' },
            { inch: 135 / 25.4, label: '1.5 col' },
            { inch: 180 / 25.4, label: '2.0 col' }
        ];

        // Column label color aligned with ruler text color
        const columnLabelColor = this.isDarkTheme ? '#aaa' : '#555';
        columnMarkersInch.forEach(marker => {
            const x = inchToPx(marker.inch);
            if (x <= width) {
                svgContent += `<text x="${x}" y="12" text-anchor="middle" font-size="11" fill="${columnLabelColor}" font-weight="500">${marker.label}</text>`;
            }
        });

        return svgContent;
    }

    /**
     * Render vertical ruler as pre-generated SVG (mm or inch)
     * PERFORMANCE: Generates complete SVG string instead of DOM manipulation
     */
    private renderVerticalRuler(height: number, dpi: number, rulerId: string = 'ruler-v'): void {
        const svg = document.getElementById(rulerId);
        if (!svg) return;

        const rulerWidth = 60;
        svg.setAttribute('width', rulerWidth.toString());
        svg.setAttribute('height', height.toString());
        svg.setAttribute('viewBox', `0 0 ${rulerWidth} ${height}`);
        svg.style.width = `${rulerWidth}px`;
        svg.style.height = `${height}px`;

        // Generate complete SVG content as string
        if (this.rulerUnit === 'mm') {
            svg.innerHTML = this.generateVerticalRulerMm(height, dpi, rulerWidth);
        } else {
            svg.innerHTML = this.generateVerticalRulerInch(height, dpi, rulerWidth);
        }
    }

    /**
     * Generate vertical ruler SVG with mm markings (pre-rendered)
     * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
     * THEME-AWARE: Adapts colors based on isDarkTheme
     */
    private generateVerticalRulerMm(height: number, dpi: number, rulerWidth: number): string {
        const pxToMm = (px: number) => (px / dpi) * 25.4;
        const mmToPx = (mm: number) => (mm * dpi) / 25.4;

        // Theme-aware colors (light mode minor ticks made more visible)
        const majorColor = this.isDarkTheme ? '#ccc' : '#888';
        const textColor = this.isDarkTheme ? '#aaa' : '#555';
        const minorColor = this.isDarkTheme ? '#666' : '#aaa';

        const maxMm = pxToMm(height);
        const majorInterval = 10;  // 10mm
        const middleInterval = 5;   // 5mm
        const minorInterval = 1;    // 1mm

        let svgContent = '';

        // Add 0mm tick mark at origin
        svgContent += `<line x1="40" y1="0" x2="${rulerWidth}" y2="0" stroke="${majorColor}" stroke-width="1.5"/>`;
        svgContent += `<text x="30" y="8" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, 8)"><title>0mm (click to toggle inch)</title>0mm</text>`;

        for (let mm = minorInterval; mm <= maxMm; mm += minorInterval) {
            const y = mmToPx(mm);

            if (mm % majorInterval === 0) {
                // Major tick
                svgContent += `<line x1="40" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${majorColor}" stroke-width="1.5"/>`;
                svgContent += `<text x="30" y="${y}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, ${y})"><title>${mm}mm (click to toggle inch)</title>${mm}mm</text>`;
            } else if (mm % middleInterval === 0) {
                // Middle tick
                svgContent += `<line x1="48" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${majorColor}" stroke-width="1"/>`;
            } else {
                // Minor tick
                svgContent += `<line x1="54" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${minorColor}" stroke-width="0.5"/>`;
            }
        }

        return svgContent;
    }

    /**
     * Generate vertical ruler SVG with inch markings (pre-rendered)
     * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
     * THEME-AWARE: Adapts colors based on isDarkTheme
     */
    private generateVerticalRulerInch(height: number, dpi: number, rulerWidth: number): string {
        const pxToInch = (px: number) => px / dpi;
        const inchToPx = (inch: number) => inch * dpi;

        // Theme-aware colors (light mode minor ticks made more visible)
        const majorColor = this.isDarkTheme ? '#ccc' : '#888';
        const textColor = this.isDarkTheme ? '#aaa' : '#555';
        const minorColor = this.isDarkTheme ? '#666' : '#aaa';

        const maxInch = pxToInch(height);
        let svgContent = '';

        // Full inch markers
        for (let inch = 0; inch <= maxInch; inch++) {
            const y = inchToPx(inch);
            svgContent += `<line x1="40" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${majorColor}" stroke-width="1.5"/>`;
            if (inch === 0) {
                // Special handling for 0" - position like mm ruler to avoid being cut off
                svgContent += `<text x="30" y="8" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, 8)"><title>0" (click to toggle mm)</title>0"</text>`;
            } else {
                svgContent += `<text x="30" y="${y}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, ${y})"><title>${inch}" (click to toggle mm)</title>${inch}"</text>`;
            }
        }

        // Fractional inch markers
        const fractions = [
            { divisor: 2, x: 48, stroke: majorColor, width: '1' },
            { divisor: 4, x: 51, stroke: majorColor, width: '0.8' },
            { divisor: 8, x: 54, stroke: minorColor, width: '0.6' },
            { divisor: 16, x: 56, stroke: minorColor, width: '0.4' }
        ];

        fractions.forEach(frac => {
            for (let inch = 0; inch <= maxInch; inch++) {
                for (let i = 1; i < frac.divisor; i++) {
                    if (i % 2 === 0 && frac.divisor > 2) continue;
                    if (i % 4 === 0 && frac.divisor > 4) continue;
                    if (i % 8 === 0 && frac.divisor > 8) continue;

                    const position = inch + (i / frac.divisor);
                    const y = inchToPx(position);

                    if (y <= height) {
                        svgContent += `<line x1="${frac.x}" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${frac.stroke}" stroke-width="${frac.width}"/>`;
                    }
                }
            }
        });

        return svgContent;
    }

    /**
     * Setup ruler dragging for canvas panning (transform-based)
     */
    public setupRulerDragging(): void {
        const rulerH = document.getElementById('ruler-h');
        const rulerV = document.getElementById('ruler-v');
        const rulerCorners = document.querySelectorAll('.ruler-corner');

        const rulers = [rulerH, rulerV, ...Array.from(rulerCorners)].filter(r => r) as HTMLElement[];

        rulers.forEach(ruler => {
            ruler.style.cursor = 'grab';

            ruler.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.canvasIsPanning = true;
                this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
                ruler.style.cursor = 'grabbing';
            });

            // Double-click (left) to reset pan position to origin
            ruler.addEventListener('dblclick', (e) => {
                e.preventDefault();
                this.canvasPanOffset.x = 0;
                this.canvasPanOffset.y = 0;
                this.updateRulersAreaTransform();
                console.log('[RulersManager] Pan reset to origin (double-click)');
                if (this.statusBarCallback) {
                    this.statusBarCallback('Pan reset to origin');
                }
            });

            // Double right-click to reset pan position to origin (same as left double-click)
            let lastRightClickTime = 0;
            const DOUBLE_CLICK_THRESHOLD = 300; // ms
            ruler.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const now = Date.now();
                if (now - lastRightClickTime < DOUBLE_CLICK_THRESHOLD) {
                    // Double right-click - reset pan
                    this.canvasPanOffset.x = 0;
                    this.canvasPanOffset.y = 0;
                    this.updateRulersAreaTransform();
                    console.log('[RulersManager] Pan reset to origin (right double-click)');
                    if (this.statusBarCallback) {
                        this.statusBarCallback('Pan reset to origin');
                    }
                    lastRightClickTime = 0;
                } else {
                    lastRightClickTime = now;
                }
            });

            ruler.addEventListener('mouseenter', () => {
                if (!this.canvasIsPanning) ruler.style.cursor = 'grab';
            });

            ruler.addEventListener('mouseleave', () => {
                if (!this.canvasIsPanning) ruler.style.cursor = 'default';
            });
        });

        document.addEventListener('mousemove', (e) => {
            if (this.canvasIsPanning && this.canvasPanStartPoint) {
                let deltaX = e.clientX - this.canvasPanStartPoint.x;
                let deltaY = e.clientY - this.canvasPanStartPoint.y;

                if (e.altKey) {
                    deltaX *= 0.1;
                    deltaY *= 0.1;
                }

                this.canvasPanOffset.x += deltaX;
                this.canvasPanOffset.y += deltaY;
                this.updateRulersAreaTransform();

                this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.canvasIsPanning) {
                this.canvasIsPanning = false;
                this.canvasPanStartPoint = null;

                rulers.forEach(ruler => {
                    ruler.style.cursor = 'grab';
                });
            }
        });

        console.log('[RulersManager] Ruler dragging (transform-based) initialized');
    }

    /**
     * Update transform on the entire rulers area (rulers + canvas together)
     * Uses callback to SigmaEditor to ensure sync with CanvasManager
     */
    public updateRulersAreaTransform(): void {
        if (this.onTransformUpdate) {
            // Use the callback to let SigmaEditor handle the transform
            // This ensures sync with CanvasManager's zoom/pan state
            this.onTransformUpdate();
        } else {
            // Fallback to local implementation
            const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
            if (rulersArea) {
                rulersArea.style.transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
                rulersArea.style.transformOrigin = 'top left';
            }
        }
    }

    /**
     * Reset pan offset to origin and notify CanvasManager
     */
    public resetPanToOrigin(): void {
        this.canvasPanOffset.x = 0;
        this.canvasPanOffset.y = 0;
    }
}
