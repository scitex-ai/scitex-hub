/**
 * ElementHighlighter - Handles element overlay canvas and highlight drawing
 *
 * Manages the visual overlay for element selection highlighting.
 * Extracted from ElementSelectionManager.ts for single responsibility.
 */

export type HighlightType = 'hover' | 'selected';

export interface HighlightColors {
    fill: string;
    stroke: string;
}

const HIGHLIGHT_COLORS: Record<HighlightType, HighlightColors> = {
    hover: {
        fill: 'rgba(100, 200, 255, 0.5)',
        stroke: 'rgba(100, 200, 255, 0.8)'
    },
    selected: {
        fill: 'rgba(255, 180, 100, 0.7)',
        stroke: 'rgba(255, 140, 50, 0.9)'
    }
};

export class ElementHighlighter {
    private overlay: HTMLCanvasElement | null = null;

    /**
     * Create overlay canvas for element highlights
     */
    public createOverlay(canvasElement: HTMLCanvasElement): HTMLCanvasElement | null {
        this.removeOverlay();

        const container = canvasElement.parentElement;
        if (!container) return null;

        const overlay = document.createElement('canvas');
        overlay.id = 'element-selection-overlay';
        overlay.style.position = 'absolute';
        overlay.style.pointerEvents = 'none';
        overlay.style.left = '0';
        overlay.style.top = '0';
        overlay.width = canvasElement.width;
        overlay.height = canvasElement.height;
        overlay.style.zIndex = '10';

        container.style.position = 'relative';
        container.appendChild(overlay);
        this.overlay = overlay;

        return overlay;
    }

    /**
     * Remove the overlay canvas
     */
    public removeOverlay(): void {
        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
        this.overlay = null;
    }

    /**
     * Get the overlay canvas
     */
    public getOverlay(): HTMLCanvasElement | null {
        return this.overlay;
    }

    /**
     * Clear the overlay canvas
     */
    public clear(): void {
        if (!this.overlay) return;
        const ctx = this.overlay.getContext('2d');
        if (ctx) {
            ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);
        }
    }

    /**
     * Draw element highlight on the overlay
     */
    public drawHighlight(
        bbox: any,
        imgLeft: number,
        imgTop: number,
        scaleX: number,
        scaleY: number,
        type: HighlightType
    ): void {
        if (!this.overlay) return;
        const ctx = this.overlay.getContext('2d');
        if (!ctx) return;

        const colors = HIGHLIGHT_COLORS[type];
        ctx.save();

        const points = bbox.points || bbox.path_simplified;
        const bboxCoords = bbox.bbox || bbox;

        // If element has points (line/scatter), draw along the path
        if (points && points.length > 1) {
            this.drawPathHighlight(ctx, points, bbox.element_type, imgLeft, imgTop, scaleX, scaleY, colors, type);
        } else {
            // Draw rectangle for elements without path data
            this.drawRectHighlight(ctx, bboxCoords, imgLeft, imgTop, scaleX, scaleY, colors);
        }

        // Draw label
        this.drawLabel(ctx, bbox, imgLeft, imgTop, scaleX, scaleY, colors.stroke);

        ctx.restore();
    }

    /**
     * Draw path-based highlight (for lines and scatter)
     */
    private drawPathHighlight(
        ctx: CanvasRenderingContext2D,
        points: number[][],
        elementType: string | undefined,
        imgLeft: number,
        imgTop: number,
        scaleX: number,
        scaleY: number,
        colors: HighlightColors,
        type: HighlightType
    ): void {
        ctx.strokeStyle = colors.stroke;
        ctx.lineWidth = type === 'hover' ? 3 : 4;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (elementType === 'scatter') {
            ctx.fillStyle = colors.fill;
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
    }

    /**
     * Draw rectangle-based highlight
     */
    private drawRectHighlight(
        ctx: CanvasRenderingContext2D,
        bboxCoords: any,
        imgLeft: number,
        imgTop: number,
        scaleX: number,
        scaleY: number,
        colors: HighlightColors
    ): void {
        const x0 = bboxCoords.x0 ?? 0;
        const y0 = bboxCoords.y0 ?? 0;
        const x1 = bboxCoords.x1 ?? 0;
        const y1 = bboxCoords.y1 ?? 0;
        const x = imgLeft + x0 * scaleX;
        const y = imgTop + y0 * scaleY;
        const w = (x1 - x0) * scaleX;
        const h = (y1 - y0) * scaleY;

        ctx.fillStyle = colors.fill;
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = colors.stroke;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);
    }

    /**
     * Draw element label
     */
    private drawLabel(
        ctx: CanvasRenderingContext2D,
        bbox: any,
        imgLeft: number,
        imgTop: number,
        scaleX: number,
        scaleY: number,
        color: string
    ): void {
        const labelX = imgLeft + bbox.x0 * scaleX;
        const labelY = imgTop + bbox.y0 * scaleY - 5;
        ctx.fillStyle = color;
        ctx.font = '12px sans-serif';
        ctx.fillText(bbox.label || '', labelX, labelY);
    }
}
