/**
 * Canvas Manager
 * Manages Fabric.js canvas initialization, grid rendering, and canvas background
 */

export class CanvasManager {
    private canvas: any;
    private gridSize: number;
    private darkCanvasMode: boolean;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            gridSize: number;
            darkCanvasMode: boolean;
            updateStatus: (message: string) => void;
        }
    ) {
        this.canvas = canvas;
        this.gridSize = options.gridSize;
        this.darkCanvasMode = options.darkCanvasMode;
        this.updateStatus = options.updateStatus;
    }

    /**
     * Initialize Fabric.js canvas with default settings
     */
    public initCanvas(
        canvasId: string,
        width: number,
        height: number
    ): any {
        const canvasElement = document.getElementById(canvasId) as HTMLCanvasElement;
        if (!canvasElement) {
            console.error(`[CanvasManager] Canvas element '${canvasId}' not found`);
            return null;
        }

        // Clean up any old inline styles on container
        const containerEl = document.querySelector('.vis-canvas-container') as HTMLElement;
        if (containerEl) {
            containerEl.style.removeProperty('padding');
            console.log('[CanvasManager] Cleared inline padding from canvas container for ruler alignment');
        }

        // SCIENTIFIC INTEGRITY: Canvas background ALWAYS white (#ffffff)
        // regardless of UI theme (light/dark). This ensures exported figures
        // are publication-ready and theme-independent.
        const canvas = new (window as any).fabric.Canvas(canvasId, {
            width: width,
            height: height,
            backgroundColor: '#ffffff',  // NEVER change - scientific integrity
            selection: true,
            selectionKey: 'ctrlKey',  // PowerPoint-style: Ctrl+Click for multi-selection
        });

        this.canvas = canvas;
        return canvas;
    }

    /**
     * Draw 2mm grid with column position guidelines
     */
    public drawGrid(): void {
        if (!this.canvas) return;

        const width = this.canvas.getWidth();
        const height = this.canvas.getHeight();

        // Clear existing grid first
        this.clearGrid();

        // Choose grid color based on canvas background
        const gridColor = this.darkCanvasMode ? '#404040' : '#e5e5e5';
        const columnLineColor = this.darkCanvasMode ? '#0080c0' : '#0080c0'; // Blue for column positions

        // Column positions in pixels (at 300 DPI)
        const mmToPx = 11.811;
        const columnPositions = [45, 90, 135]; // 0.5, 1.0, 1.5 columns (in mm)

        // Draw 2mm grid - vertical lines
        for (let i = 0; i <= width / this.gridSize; i++) {
            const x = i * this.gridSize;
            const line = new (window as any).fabric.Line([x, 0, x, height], {
                stroke: gridColor,
                strokeWidth: i % 5 === 0 ? 1 : 0.5,  // Major/minor lines every 10mm
                selectable: false,
                evented: false,
                hoverCursor: 'default',
                excludeFromExport: true,
            } as any);
            line.set('id', 'grid-line');
            line.set('selectable', false);
            line.set('evented', false);
            this.canvas.add(line);
            this.canvas.sendToBack(line);
        }

        // Draw 2mm grid - horizontal lines
        for (let i = 0; i <= height / this.gridSize; i++) {
            const y = i * this.gridSize;
            const line = new (window as any).fabric.Line([0, y, width, y], {
                stroke: gridColor,
                strokeWidth: i % 5 === 0 ? 1 : 0.5,  // Major/minor lines every 10mm
                selectable: false,
                evented: false,
                hoverCursor: 'default',
                excludeFromExport: true,
            } as any);
            line.set('id', 'grid-line');
            line.set('selectable', false);
            line.set('evented', false);
            this.canvas.add(line);
            this.canvas.sendToBack(line);
        }

        // Draw column position guidelines (45mm, 90mm, 135mm)
        columnPositions.forEach(mmPos => {
            const x = mmPos * mmToPx;
            if (x <= width) {
                const line = new (window as any).fabric.Line([x, 0, x, height], {
                    stroke: columnLineColor,
                    strokeWidth: 1.5,
                    strokeDashArray: [10, 5], // Dashed line
                    selectable: false,
                    evented: false,
                    hoverCursor: 'default',
                    excludeFromExport: true,
                    opacity: 0.4,
                } as any);
                line.set('id', 'grid-line');
                line.set('selectable', false);
                line.set('evented', false);
                this.canvas.add(line);
                this.canvas.sendToBack(line);
            }
        });

        this.canvas.renderAll();
    }

    /**
     * Remove all grid lines from canvas
     */
    public clearGrid(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            if (obj.id === 'grid-line') {
                this.canvas!.remove(obj);
            }
        });
        this.canvas.renderAll();
    }

    /**
     * Toggle canvas background between white and dark (viewing comfort only)
     */
    public toggleCanvasBackground(darkMode: boolean): void {
        if (!this.canvas) return;

        this.darkCanvasMode = darkMode;

        const warningEl = document.getElementById('dark-canvas-warning');
        const containerEl = document.querySelector('.vis-canvas-container') as HTMLElement;

        if (this.darkCanvasMode) {
            // Switch to dark background (for viewing comfort - eyes)
            this.canvas.setBackgroundColor('#2a2a2a', () => {
                this.canvas!.renderAll();
            });

            // Also darken the container (keep padding for ruler alignment)
            if (containerEl) {
                containerEl.style.backgroundColor = '#2a2a2a';
                containerEl.style.removeProperty('padding');
            }

            // Show warning
            if (warningEl) {
                warningEl.style.display = 'flex';
            }

            this.updateStatus('Dark canvas enabled (viewing only - export will be white)');
            console.log('[CanvasManager] Dark canvas mode: ON (export will be white)');

        } else {
            // Switch back to white background
            this.canvas.setBackgroundColor('#ffffff', () => {
                this.canvas!.renderAll();
            });

            // Restore white container background
            if (containerEl) {
                containerEl.style.backgroundColor = '#ffffff';
                containerEl.style.removeProperty('padding');
            }

            // Hide warning
            if (warningEl) {
                warningEl.style.display = 'none';
            }

            this.updateStatus('White canvas restored');
            console.log('[CanvasManager] Dark canvas mode: OFF');
        }

        // Redraw grid with appropriate color
        this.drawGrid();
    }

    /**
     * Update canvas info display (size, DPI)
     */
    public updateCanvasInfo(currentPreset: any): void {
        if (!this.canvas) return;

        const width = this.canvas.getWidth();
        const height = this.canvas.getHeight();
        const dpi = currentPreset?.dpi || 300;

        // Calculate mm dimensions
        const widthMm = (width / dpi) * 25.4;
        const heightMm = (height / dpi) * 25.4;

        const sizeEl = document.getElementById('canvas-size');
        if (sizeEl) {
            sizeEl.textContent = `${Math.round(widthMm)}mm × ${Math.round(heightMm)}mm (${width} × ${height}px)`;
        }

        const dpiEl = document.getElementById('canvas-dpi');
        if (dpiEl) {
            dpiEl.textContent = `${dpi} DPI`;
        }
    }

    /**
     * Update grid size (for preset changes)
     */
    public updateGridSize(newGridSize: number): void {
        this.gridSize = newGridSize;
        this.drawGrid();
    }

    /**
     * Get current dark mode state
     */
    public isDarkMode(): boolean {
        return this.darkCanvasMode;
    }
}
