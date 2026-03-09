/**
 * Grid Renderer
 * Handles grid drawing on canvas
 */

import { RulerUnit, JournalPreset } from '../types';
import { RulerDrawer } from './RulerDrawer';

export class GridRenderer {
    private canvas: any;
    private gridSize: number;
    private darkCanvasMode: boolean = false;
    private rulerDrawer: RulerDrawer;
    private getCurrentPreset: () => JournalPreset | null;

    constructor(
        canvas: any,
        gridSize: number,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            darkCanvasMode?: boolean;
            rulerUnit?: RulerUnit;
        }
    ) {
        this.canvas = canvas;
        this.gridSize = gridSize;
        this.getCurrentPreset = options.getCurrentPreset;
        this.darkCanvasMode = options.darkCanvasMode || false;
        this.rulerDrawer = new RulerDrawer(options.rulerUnit);
    }

    /**
     * Draw grid on canvas
     */
    public drawGrid(): void {
        if (!this.canvas) return;

        const width = this.canvas.getWidth();
        const height = this.canvas.getHeight();

        // Clear existing grid
        this.clearGrid();

        const gridColor = this.darkCanvasMode ? '#404040' : '#e5e5e5';
        const columnLineColor = '#0080c0';

        const mmToPx = 11.811;
        const columnPositions = [45, 90, 135]; // 0.5, 1.0, 1.5 columns (in mm)

        // Draw vertical grid lines
        for (let i = 0; i <= width / this.gridSize; i++) {
            const x = i * this.gridSize;
            const line = new (window as any).fabric.Line([x, 0, x, height], {
                stroke: gridColor,
                strokeWidth: i % 5 === 0 ? 1 : 0.5,
                selectable: false,
                evented: false,
                hoverCursor: 'default',
                excludeFromExport: true,
            });
            line.set('id', 'grid-line');
            this.canvas.add(line);
            this.canvas.sendToBack(line);
        }

        // Draw horizontal grid lines
        for (let i = 0; i <= height / this.gridSize; i++) {
            const y = i * this.gridSize;
            const line = new (window as any).fabric.Line([0, y, width, y], {
                stroke: gridColor,
                strokeWidth: i % 5 === 0 ? 1 : 0.5,
                selectable: false,
                evented: false,
                hoverCursor: 'default',
                excludeFromExport: true,
            });
            line.set('id', 'grid-line');
            this.canvas.add(line);
            this.canvas.sendToBack(line);
        }

        // Draw column position guidelines
        columnPositions.forEach(mmPos => {
            const x = mmPos * mmToPx;
            if (x <= width) {
                const line = new (window as any).fabric.Line([x, 0, x, height], {
                    stroke: columnLineColor,
                    strokeWidth: 1.5,
                    strokeDashArray: [10, 5],
                    selectable: false,
                    evented: false,
                    hoverCursor: 'default',
                    excludeFromExport: true,
                    opacity: 0.4,
                });
                line.set('id', 'grid-line');
                this.canvas.add(line);
                this.canvas.sendToBack(line);
            }
        });

        this.canvas.renderAll();
    }

    /**
     * Clear grid from canvas
     */
    public clearGrid(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            if (obj.id === 'grid-line') {
                this.canvas.remove(obj);
            }
        });
        this.canvas.renderAll();
    }

    /**
     * Draw horizontal ruler
     */
    public drawHorizontalRuler(width: number, dpi: number): void {
        this.rulerDrawer.drawHorizontalRuler(width, dpi);
    }

    /**
     * Draw vertical ruler
     */
    public drawVerticalRuler(height: number, dpi: number): void {
        this.rulerDrawer.drawVerticalRuler(height, dpi);
    }

    // Getters and setters
    public setDarkMode(dark: boolean): void {
        this.darkCanvasMode = dark;
    }

    public setRulerUnit(unit: RulerUnit): void {
        this.rulerDrawer.setRulerUnit(unit);
    }

    public setGridSize(size: number): void {
        this.gridSize = size;
    }
}
