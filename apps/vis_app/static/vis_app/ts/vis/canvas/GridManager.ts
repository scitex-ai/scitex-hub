/**
 * GridManager - Handles grid rendering and visibility
 *
 * Responsibilities:
 * - Draw grid using static SVG files (light/dark mode)
 * - Toggle grid visibility
 * - Clear grid background
 *
 * PERFORMANCE: Uses pre-rendered static SVG files cached by browser
 */

export class GridManager {
    private gridEnabled: boolean = true;

    /**
     * Create a new GridManager
     * @param canvas - Fabric.js canvas instance
     * @param statusCallback - Optional callback for status messages
     */
    constructor(
        private canvas: any,
        private statusCallback?: (message: string) => void
    ) {}

    /**
     * Draw grid using pre-rendered static SVG files
     * PERFORMANCE: Static SVG files are cached by browser
     *
     * @param isDark - Whether to use dark mode grid
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
            this.canvas.setBackgroundImage(img, this.canvas.renderAll.bind(this.canvas), {
                scaleX: 1,
                scaleY: 1,
                originX: 'left',
                originY: 'top',
            });

            const endTime = performance.now();
            console.log(`[GridManager] ✅ Grid loaded from static SVG in ${(endTime - startTime).toFixed(2)}ms (${isDark ? 'dark' : 'light'} mode)`);

            if (this.statusCallback) {
                this.statusCallback('Grid enabled');
            }
        }, { crossOrigin: 'anonymous' });
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
            this.canvas.backgroundColor = bgColor;
            this.canvas.renderAll();
        });

        // Legacy cleanup: Remove any old Fabric.js grid objects (for backwards compatibility)
        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            if (obj.id === 'grid-line' || obj.id === 'column-guide') {
                this.canvas.remove(obj);
            }
        });

        console.log('[GridManager] Grid cleared');
    }

    /**
     * Toggle grid visibility
     */
    public toggleGrid(): void {
        this.gridEnabled = !this.gridEnabled;

        if (this.gridEnabled) {
            // Determine current theme for grid
            const savedTheme = localStorage.getItem('canvas-theme') || localStorage.getItem('scitex-theme-preference') || 'dark';
            const isDark = savedTheme === 'dark';
            this.drawGrid(isDark);
            console.log('[GridManager] Grid enabled');
        } else {
            this.clearGrid();
            if (this.statusCallback) {
                this.statusCallback('Grid disabled');
            }
            console.log('[GridManager] Grid disabled');
        }
    }

    /**
     * Check if grid is currently enabled
     * @returns true if grid is enabled
     */
    public isGridEnabled(): boolean {
        return this.gridEnabled;
    }

    /**
     * Enable grid
     */
    public enableGrid(): void {
        if (!this.gridEnabled) {
            this.toggleGrid();
        }
    }

    /**
     * Disable grid
     */
    public disableGrid(): void {
        if (this.gridEnabled) {
            this.toggleGrid();
        }
    }
}
