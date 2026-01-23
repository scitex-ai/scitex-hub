/**
 * Advanced Scientific Annotations
 * Complex annotation tools like overlapping rectangles and column references
 */

import { JournalPreset } from '../types';
import { unitToPx } from '../utils/geometry';

export class AdvancedAnnotations {
    private canvas: any;
    private getCurrentPreset: () => JournalPreset | null;
    private updateStatus: (message: string) => void;
    private scientificColors: any;

    constructor(
        canvas: any,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            updateStatus: (message: string) => void;
            scientificColors: any;
        }
    ) {
        this.canvas = canvas;
        this.getCurrentPreset = options.getCurrentPreset;
        this.updateStatus = options.updateStatus;
        this.scientificColors = options.scientificColors;
    }

    /**
     * Add overlapping reference rectangles for size comparison
     */
    public addReferenceRectangles(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const fontSize = preset?.font_size_pt || 10;
        const fontFamily = preset?.font_family || 'Arial';
        const dpi = preset?.dpi || 300;

        const rects = [
            { widthMm: 50, heightMm: 35, color: 'rgba(50, 200, 50, 0.3)', label: 'Width 50 mm' },
            { widthMm: 40, heightMm: 28, color: 'rgba(255, 50, 50, 0.3)', label: 'Width 40 mm' },
            { widthMm: 30, heightMm: 21, color: 'rgba(0, 100, 255, 0.3)', label: 'Width 30 mm' }
        ];

        const objects: any[] = [];

        rects.forEach((rectSpec, index) => {
            const widthPx = unitToPx(rectSpec.widthMm, dpi, 'mm');
            const heightPx = unitToPx(rectSpec.heightMm, dpi, 'mm');

            const rect = new (window as any).fabric.Rect({
                left: 0,
                top: 0,
                width: widthPx,
                height: heightPx,
                fill: rectSpec.color,
                stroke: 'transparent',
                strokeWidth: 0,
            });

            const labelXOffset = widthPx + 5;
            const label = new (window as any).fabric.Text(rectSpec.label, {
                left: labelXOffset,
                top: 0 + (index * fontSize * 1.5),
                fontSize: fontSize * 1.2,
                fontFamily: fontFamily,
                fill: '#000000',
            });

            objects.push(rect, label);
        });

        const group = new (window as any).fabric.Group(objects, {
            left: 50,
            top: 50,
            selectable: true,
            evented: true,
        });

        this.canvas.add(group);
        this.canvas.bringToFront(group);
        this.canvas.setActiveObject(group);
        this.canvas.renderAll();
        this.updateStatus('Reference rectangles added (30mm, 40mm, 50mm)');
    }

    /**
     * Add column width ruler guides
     */
    public addColumnWidthRuler(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const fontSize = preset?.font_size_pt || 10;
        const fontFamily = preset?.font_family || 'Arial';
        const dpi = preset?.dpi || 300;

        const heightMm = 10;
        const columns = [
            { widthMm: 180, color: 'rgba(0, 128, 192, 0.2)', label: '2.0 Col (180mm)' },
            { widthMm: 135, color: 'rgba(0, 128, 192, 0.3)', label: '1.5 Col (135mm)' },
            { widthMm: 90,  color: 'rgba(0, 128, 192, 0.4)', label: '1.0 Col (90mm)' },
            { widthMm: 45,  color: 'rgba(0, 128, 192, 0.5)', label: '0.5 Col (45mm)' }
        ];

        const objects: any[] = [];

        columns.forEach((col, index) => {
            const widthPx = unitToPx(col.widthMm, dpi, 'mm');
            const heightPx = unitToPx(heightMm, dpi, 'mm');

            const rect = new (window as any).fabric.Rect({
                left: 0,
                top: 0,
                width: widthPx,
                height: heightPx,
                fill: col.color,
                stroke: 'transparent',
                strokeWidth: 0,
            });

            const label = new (window as any).fabric.Text(col.label, {
                left: widthPx + 5,
                top: 0 + (index * fontSize * 1.5),
                fontSize: fontSize * 1.2,
                fontFamily: fontFamily,
                fill: '#000000',
            });

            objects.push(rect, label);
        });

        const group = new (window as any).fabric.Group(objects, {
            left: 50,
            top: 50,
            selectable: true,
            evented: true,
        });

        this.canvas.add(group);
        this.canvas.bringToFront(group);
        this.canvas.setActiveObject(group);
        this.canvas.renderAll();
        this.updateStatus('Column width guides added (0.5, 1.0, 1.5, 2.0)');
    }

    /**
     * Add column width reference rectangle
     */
    public addColumnReference(type: '0.5' | 'single' | '1.5' | 'double'): void {
        if (!this.canvas) return;

        const mmToPx = 11.811;
        const heights = 60;
        const widths = {
            '0.5': 45,
            'single': 90,
            '1.5': 135,
            'double': 180,
        };

        const opacities = {
            '0.5': 1.0,
            'single': 0.8,
            '1.5': 0.6,
            'double': 0.4,
        };

        const widthMm = widths[type];
        const opacity = opacities[type];

        const rect = new (window as any).fabric.Rect({
            left: 100,
            top: 100,
            width: widthMm * mmToPx,
            height: heights * mmToPx,
            fill: `rgba(0,128,192,${opacity * 0.2})`,
            stroke: `rgba(0,128,192,${opacity})`,
            strokeWidth: 2,
            selectable: true,
            evented: true,
        });

        const label = new (window as any).fabric.Text(`${widthMm}mm (${type} col)`, {
            left: 5,
            top: 5,
            fontSize: 8,
            fontFamily: 'Arial',
            fill: this.scientificColors.blue,
            selectable: false,
        });

        const group = new (window as any).fabric.Group([rect, label], {
            selectable: true,
            hasControls: true,
        });

        this.canvas.add(group);
        this.canvas.bringToFront(group);
        this.canvas.setActiveObject(group);
        this.canvas.renderAll();
        this.updateStatus(`${type} column reference added (${widthMm}mm)`);
    }
}
