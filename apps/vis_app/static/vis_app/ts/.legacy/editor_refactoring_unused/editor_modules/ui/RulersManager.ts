/**
 * RulersManager - Manages ruler state, dragging, and visibility
 *
 * Responsibilities:
 * - Toggle ruler unit and visibility
 * - Handle ruler dragging for canvas panning
 * - Update ruler transform with canvas zoom/pan
 * - Coordinate with RulerRenderer for drawing
 */

import { RulerRenderer, RulerUnit } from './RulerRenderer.ts';

export class RulersManager {
    private renderer: RulerRenderer;
    private rulerVisible: boolean = true;
    private isPanning: boolean = false;
    private panStartPoint: { x: number; y: number } | null = null;

    constructor(
        private zoomLevel: number = 1.0,
        private panOffset: { x: number; y: number } = { x: 0, y: 0 },
        private onPanChange?: (offset: { x: number; y: number }) => void,
        private statusCallback?: (message: string) => void
    ) {
        this.renderer = new RulerRenderer('mm');
    }

    /**
     * Get current ruler unit
     */
    public getRulerUnit(): RulerUnit {
        return this.renderer.getUnit();
    }

    /**
     * Set ruler visibility
     */
    public setRulerVisible(visible: boolean): void {
        this.rulerVisible = visible;
        this.toggleRulers();
    }

    /**
     * Update zoom level (called from ZoomManager)
     */
    public setZoomLevel(level: number): void {
        this.zoomLevel = level;
        this.updateTransform();
    }

    /**
     * Update pan offset (called from external pan handlers)
     */
    public setPanOffset(offset: { x: number; y: number }): void {
        this.panOffset = offset;
        this.updateTransform();
    }

    /**
     * Initialize rulers on canvas load
     */
    public initializeRulers(canvas: any): void {
        if (!canvas) return;
        const canvasWidth = canvas.getWidth();
        const canvasHeight = canvas.getHeight();
        this.drawRulers(canvasWidth, canvasHeight, 300); // Default DPI
    }

    /**
     * Draw all four rulers
     */
    public drawRulers(width: number, height: number, dpi: number): void {
        if (!this.rulerVisible) return;

        // Preserve scroll position to prevent page jumping
        const scrollX = window.scrollX || window.pageXOffset;
        const scrollY = window.scrollY || window.pageYOffset;

        this.renderer.drawHorizontalRuler(width, dpi, 'ruler-horizontal');
        this.renderer.drawVerticalRuler(height, dpi, 'ruler-vertical');
        this.renderer.drawHorizontalRuler(width, dpi, 'ruler-horizontal-bottom');
        this.renderer.drawVerticalRuler(height, dpi, 'ruler-vertical-right');

        // Restore scroll position
        window.scrollTo(scrollX, scrollY);
    }

    /**
     * Toggle ruler unit between mm and inches
     */
    public toggleRulerUnit(canvas: any, dpi: number): void {
        const currentUnit = this.renderer.getUnit();
        const newUnit: RulerUnit = currentUnit === 'mm' ? 'inches' : 'mm';
        this.renderer.setUnit(newUnit);

        // Update UI label
        const label = document.getElementById('ruler-unit-label');
        if (label) {
            label.textContent = newUnit;
        }

        // Redraw with new unit
        if (canvas) {
            this.drawRulers(canvas.getWidth(), canvas.getHeight(), dpi);
        }

        console.log(`[RulersManager] Unit changed to: ${newUnit}`);
        if (this.statusCallback) {
            this.statusCallback(`Ruler units: ${newUnit}`);
        }
    }

    /**
     * Setup ruler dragging for canvas panning
     */
    public setupRulerDragging(): void {
        const rulers = [
            'ruler-horizontal',
            'ruler-vertical',
            'ruler-horizontal-bottom',
            'ruler-vertical-right'
        ].map(id => document.getElementById(id)).filter(r => r) as HTMLElement[];

        const corners = Array.from(document.querySelectorAll('.ruler-corner')) as HTMLElement[];
        const allRulers = [...rulers, ...corners];

        allRulers.forEach(ruler => {
            ruler.style.cursor = 'grab';

            ruler.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.isPanning = true;
                this.panStartPoint = { x: e.clientX, y: e.clientY };
                ruler.style.cursor = 'grabbing';
            });

            ruler.addEventListener('mouseenter', () => {
                if (!this.isPanning) ruler.style.cursor = 'grab';
            });

            ruler.addEventListener('mouseleave', () => {
                if (!this.isPanning) ruler.style.cursor = 'default';
            });
        });

        // Global mouse move and up for ruler dragging
        document.addEventListener('mousemove', (e) => {
            if (this.isPanning && this.panStartPoint) {
                let deltaX = e.clientX - this.panStartPoint.x;
                let deltaY = e.clientY - this.panStartPoint.y;

                // Alt key = Fine-tuned panning (10% speed)
                if (e.altKey) {
                    deltaX *= 0.1;
                    deltaY *= 0.1;
                }

                this.panOffset.x += deltaX;
                this.panOffset.y += deltaY;
                this.updateTransform();

                // Notify parent of pan change
                if (this.onPanChange) {
                    this.onPanChange(this.panOffset);
                }

                this.panStartPoint = { x: e.clientX, y: e.clientY };
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.isPanning) {
                this.isPanning = false;
                this.panStartPoint = null;

                allRulers.forEach(ruler => {
                    ruler.style.cursor = 'grab';
                });
            }
        });

        console.log('[RulersManager] Ruler dragging initialized');
    }

    /**
     * Update transform on rulers area
     */
    private updateTransform(): void {
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (rulersArea) {
            rulersArea.style.transform = `translate(${this.panOffset.x}px, ${this.panOffset.y}px) scale(${this.zoomLevel})`;
            rulersArea.style.transformOrigin = 'top left';
        }
    }

    /**
     * Toggle rulers visibility
     */
    private toggleRulers(): void {
        const rulersArea = document.querySelector('.vis-rulers-area');
        if (rulersArea) {
            if (this.rulerVisible) {
                rulersArea.classList.remove('rulers-hidden');
            } else {
                rulersArea.classList.add('rulers-hidden');
            }
        }
    }
}
