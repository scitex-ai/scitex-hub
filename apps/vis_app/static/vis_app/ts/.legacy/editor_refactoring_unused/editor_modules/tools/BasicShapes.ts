/**
 * Basic Shapes
 * Tools for creating basic geometric shapes and text
 */

import { JournalPreset } from '../types';

export class BasicShapes {
    private canvas: any;
    private getCurrentPreset: () => JournalPreset | null;
    private getCurrentColor: () => string;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            getCurrentColor: () => string;
            updateStatus: (message: string) => void;
        }
    ) {
        this.canvas = canvas;
        this.getCurrentPreset = options.getCurrentPreset;
        this.getCurrentColor = options.getCurrentColor;
        this.updateStatus = options.updateStatus;
    }

    /**
     * Add text element to canvas
     */
    public addText(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const fontSize = preset?.font_size_pt || 12;
        const fontFamily = preset?.font_family || 'Arial';

        const text = new (window as any).fabric.IText('Double-click to edit', {
            left: 100,
            top: 100,
            fontSize: fontSize * 2,
            fontFamily: fontFamily,
            fill: '#000000',
            selectable: true,
            evented: true,
        });

        this.canvas.add(text);
        this.canvas.bringToFront(text);
        this.canvas.setActiveObject(text);
        this.canvas.renderAll();
        this.updateStatus('Text added - Double-click to edit');
    }

    /**
     * Add rectangle
     */
    public addRectangle(fillColor: string, description: string): void {
        if (!this.canvas) return;

        const rect = new (window as any).fabric.Rect({
            left: 100,
            top: 100,
            width: 150,
            height: 100,
            fill: fillColor,
            stroke: fillColor === '#ffffff' ? '#cccccc' : 'none',
            strokeWidth: 1,
            strokeDashArray: fillColor === '#ffffff' ? [3, 3] : [],
            selectable: true,
            evented: true,
        });

        this.canvas.add(rect);
        this.canvas.bringToFront(rect);
        this.canvas.setActiveObject(rect);
        this.canvas.renderAll();
        this.updateStatus(description + ' added');
    }

    /**
     * Add line
     */
    public addLine(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const lineWidth = preset?.line_width_pt || 0.5;
        const color = this.getCurrentColor();

        const line = new (window as any).fabric.Line([50, 50, 200, 50], {
            stroke: color,
            strokeWidth: lineWidth * 4,
            selectable: true,
            evented: true,
        });

        this.canvas.add(line);
        this.canvas.bringToFront(line);
        this.canvas.setActiveObject(line);
        this.canvas.renderAll();
        this.updateStatus('Line added');
    }

    /**
     * Add circle
     */
    public addCircle(): void {
        if (!this.canvas) return;

        const color = this.getCurrentColor();
        const circle = new (window as any).fabric.Circle({
            radius: 50,
            fill: color,
            left: 100,
            top: 100,
            selectable: true,
            evented: true,
        });

        this.canvas.add(circle);
        this.canvas.bringToFront(circle);
        this.canvas.setActiveObject(circle);
        this.canvas.renderAll();
        this.updateStatus('Circle added');
    }

    /**
     * Add triangle
     */
    public addTriangle(): void {
        if (!this.canvas) return;

        const color = this.getCurrentColor();
        const triangle = new (window as any).fabric.Triangle({
            width: 100,
            height: 100,
            fill: color,
            left: 100,
            top: 100,
            selectable: true,
            evented: true,
        });

        this.canvas.add(triangle);
        this.canvas.bringToFront(triangle);
        this.canvas.setActiveObject(triangle);
        this.canvas.renderAll();
        this.updateStatus('Triangle added');
    }

    /**
     * Add diamond (rotated square)
     */
    public addDiamond(): void {
        if (!this.canvas) return;

        const color = this.getCurrentColor();
        const diamond = new (window as any).fabric.Rect({
            width: 80,
            height: 80,
            fill: color,
            left: 100,
            top: 100,
            angle: 45,
            selectable: true,
            evented: true,
        });

        this.canvas.add(diamond);
        this.canvas.bringToFront(diamond);
        this.canvas.setActiveObject(diamond);
        this.canvas.renderAll();
        this.updateStatus('Diamond added');
    }

    /**
     * Add arrow
     */
    public addArrow(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const lineWidth = preset?.line_width_pt || 0.5;

        const startX = 50;
        const startY = 50;
        const endX = 200;
        const endY = 50;

        const line = new (window as any).fabric.Line([startX, startY, endX, endY], {
            stroke: '#000000',
            strokeWidth: lineWidth * 4,
        });

        const headLength = 15;
        const angle = Math.atan2(endY - startY, endX - startX);

        const arrowHead = new (window as any).fabric.Triangle({
            left: endX,
            top: endY,
            width: headLength,
            height: headLength,
            fill: '#000000',
            angle: (angle * 180 / Math.PI) + 90,
            originX: 'center',
            originY: 'center',
        });

        const arrow = new (window as any).fabric.Group([line, arrowHead], {
            left: 100,
            top: 100,
            selectable: true,
            evented: true,
        });

        this.canvas.add(arrow);
        this.canvas.bringToFront(arrow);
        this.canvas.setActiveObject(arrow);
        this.canvas.renderAll();
        this.updateStatus('Arrow added');
    }
}
