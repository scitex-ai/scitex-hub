/**
 * Grid Manager
 * Coordinates grid display and ruler rendering
 */

import { RulerUnit, JournalPreset } from '../types';
import { GridRenderer } from './GridRenderer.ts';

export class GridManager {
    private canvas: any;
    private gridSize: number;
    private gridEnabled: boolean = true;
    private rulerVisible: boolean = true;
    private gridRenderer: GridRenderer;
    private getCurrentPreset: () => JournalPreset | null;

    constructor(
        canvas: any,
        gridSize: number,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            darkCanvasMode?: boolean;
            rulerVisible?: boolean;
            rulerUnit?: RulerUnit;
        }
    ) {
        this.canvas = canvas;
        this.gridSize = gridSize;
        this.getCurrentPreset = options.getCurrentPreset;
        this.rulerVisible = options.rulerVisible !== false;
        this.gridRenderer = new GridRenderer(canvas, gridSize, {
            getCurrentPreset: options.getCurrentPreset,
            darkCanvasMode: options.darkCanvasMode,
            rulerUnit: options.rulerUnit,
        });
    }

    /**
     * Draw grid on canvas
     */
    public drawGrid(): void {
        this.gridRenderer.drawGrid();
    }

    /**
     * Clear grid from canvas
     */
    public clearGrid(): void {
        this.gridRenderer.clearGrid();
    }

    /**
     * Toggle rulers visibility
     */
    public toggleRulers(): void {
        const rulersArea = document.querySelector('.vis-rulers-area');
        if (rulersArea) {
            if (this.rulerVisible) {
                rulersArea.classList.remove('rulers-hidden');
                this.drawRulers();
            } else {
                rulersArea.classList.add('rulers-hidden');
            }
        }
    }

    /**
     * Draw all rulers
     */
    public drawRulers(): void {
        if (!this.canvas || !this.rulerVisible) return;

        // Preserve scroll position
        const scrollX = window.scrollX || window.pageXOffset;
        const scrollY = window.scrollY || window.pageYOffset;

        const preset = this.getCurrentPreset();
        const dpi = preset?.dpi || 300;
        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();

        this.gridRenderer.drawHorizontalRuler(canvasWidth, dpi);
        this.gridRenderer.drawVerticalRuler(canvasHeight, dpi);
        this.drawHorizontalBottomRuler(canvasWidth, dpi);
        this.drawVerticalRightRuler(canvasHeight, dpi);

        // Restore scroll position
        window.scrollTo(scrollX, scrollY);
    }

    /**
     * Draw horizontal bottom ruler
     */
    private drawHorizontalBottomRuler(width: number, dpi: number): void {
        const svg = document.getElementById('ruler-horizontal-bottom');
        if (!svg) return;

        // Simplified bottom ruler
        svg.innerHTML = '';
        const rulerHeight = 30;
        svg.setAttribute('width', width.toString());
        svg.setAttribute('height', rulerHeight.toString());
    }

    /**
     * Draw vertical right ruler
     */
    private drawVerticalRightRuler(height: number, dpi: number): void {
        const svg = document.getElementById('ruler-vertical-right');
        if (!svg) return;

        // Simplified right ruler
        svg.innerHTML = '';
        const rulerWidth = 30;
        svg.setAttribute('width', rulerWidth.toString());
        svg.setAttribute('height', height.toString());
    }

    // Getters and setters
    public setDarkMode(dark: boolean): void {
        this.gridRenderer.setDarkMode(dark);
    }

    public setRulerUnit(unit: RulerUnit): void {
        this.gridRenderer.setRulerUnit(unit);
    }

    public setRulerVisible(visible: boolean): void {
        this.rulerVisible = visible;
    }

    public setGridSize(size: number): void {
        this.gridSize = size;
        this.gridRenderer.setGridSize(size);
    }
}
