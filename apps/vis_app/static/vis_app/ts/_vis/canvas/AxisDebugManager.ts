/**
 * AxisDebugManager - Debug visualization for axis metadata
 *
 * Responsibilities:
 * - Show axis debug lines on canvas objects
 * - Visualize Y-axis (red) and X-axis (blue) positions
 * - Auto-clear debug lines after timeout
 */

export class AxisDebugManager {
    private axisDebugLines: any[] = [];

    constructor(
        private canvas: any,
        private statusCallback?: (message: string) => void
    ) {
        console.log('[AxisDebugManager] Initialized');
    }

    /**
     * Show axis debug lines for objects with axis metadata
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
            console.log('[AxisDebugManager] No objects with axis metadata to show debug lines');
            return;
        }

        console.log(`[AxisDebugManager] Showing axis debug lines for ${targetObjects.length} objects`);

        const fabric = (window as any).fabric;
        if (!fabric) {
            console.error('[AxisDebugManager] Fabric.js not available');
            return;
        }

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
            const yAxisLine = new fabric.Line(
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
            const xAxisLine = new fabric.Line(
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
            this.canvas.add(yAxisLine, xAxisLine);
            this.axisDebugLines.push(yAxisLine, xAxisLine);
        });

        this.canvas.renderAll();

        // Auto-clear after 5 seconds
        setTimeout(() => this.clearAxisDebugLines(), 5000);

        if (this.statusCallback) {
            this.statusCallback('Showing axis debug lines (auto-clear in 5s)');
        }
    }

    /**
     * Clear axis debug lines from canvas
     */
    public clearAxisDebugLines(): void {
        if (!this.canvas) return;

        this.axisDebugLines.forEach(line => {
            this.canvas.remove(line);
        });
        this.axisDebugLines = [];
        this.canvas.renderAll();
    }

    /**
     * Cleanup
     */
    public destroy(): void {
        this.clearAxisDebugLines();
    }
}
