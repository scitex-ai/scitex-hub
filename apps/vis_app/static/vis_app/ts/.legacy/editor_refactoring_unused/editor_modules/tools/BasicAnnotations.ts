/**
 * Basic Scientific Annotations
 * Tools for simple scientific annotations like significance markers and scale bars
 */

import { JournalPreset } from '../types';

export class BasicAnnotations {
    private canvas: any;
    private getCurrentPreset: () => JournalPreset | null;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            updateStatus: (message: string) => void;
        }
    ) {
        this.canvas = canvas;
        this.getCurrentPreset = options.getCurrentPreset;
        this.updateStatus = options.updateStatus;
    }

    /**
     * Add significance marker (asterisks)
     */
    public addSignificance(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const fontSize = preset?.font_size_pt || 10;
        const fontFamily = preset?.font_family || 'Arial';

        const stars = new (window as any).fabric.Text('***', {
            left: 150,
            top: 50,
            fontSize: fontSize * 2.5,
            fontFamily: fontFamily,
            fill: '#000000',
            fontWeight: 'bold',
            selectable: true,
            evented: true,
        });

        this.canvas.add(stars);
        this.canvas.bringToFront(stars);
        this.canvas.setActiveObject(stars);
        this.canvas.renderAll();
        this.updateStatus('Significance marker added (p < 0.001)');
    }

    /**
     * Add scientific notation symbol
     */
    public addScientificNotation(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const fontSize = preset?.font_size_pt || 10;
        const fontFamily = preset?.font_family || 'Arial';

        const notation = new (window as any).fabric.Text('×10⁻³', {
            left: 150,
            top: 50,
            fontSize: fontSize * 2,
            fontFamily: fontFamily,
            fill: '#000000',
            selectable: true,
            evented: true,
        });

        this.canvas.add(notation);
        this.canvas.bringToFront(notation);
        this.canvas.setActiveObject(notation);
        this.canvas.renderAll();
        this.updateStatus('Scientific notation added (×10⁻³)');
    }

    /**
     * Add scale bar with label
     */
    public addScaleBar(): void {
        if (!this.canvas) return;

        const preset = this.getCurrentPreset();
        const fontSize = preset?.font_size_pt || 12;
        const fontFamily = preset?.font_family || 'Arial';
        const lineWidth = preset?.line_width_pt || 0.5;

        const barLength = 100;
        const line = new (window as any).fabric.Line([0, 0, barLength, 0], {
            stroke: '#000000',
            strokeWidth: lineWidth * 4,
        });

        const text = new (window as any).fabric.Text('100 μm', {
            fontSize: fontSize * 1.5,
            fontFamily: fontFamily,
            fill: '#000000',
            left: 0,
            top: 12,
        });

        const scaleBar = new (window as any).fabric.Group([line, text], {
            left: this.canvas.getWidth() - 150,
            top: this.canvas.getHeight() - 80,
            selectable: true,
            evented: true,
        });

        this.canvas.add(scaleBar);
        this.canvas.bringToFront(scaleBar);
        this.canvas.setActiveObject(scaleBar);
        this.canvas.renderAll();
        this.updateStatus('Scale bar added (adjust length as needed)');
    }

    /**
     * Add reference rectangle for size comparison
     */
    public addReferenceRect(size: 'small' | 'medium' | 'large', scientificColors: any): void {
        if (!this.canvas) return;

        const mmToPx = 11.811;
        const sizes = {
            small: { width: 30, height: 30 },
            medium: { width: 40, height: 40 },
            large: { width: 50, height: 50 },
        };

        const sizeInMm = sizes[size];
        const rect = new (window as any).fabric.Rect({
            left: 100,
            top: 100,
            width: sizeInMm.width * mmToPx,
            height: sizeInMm.height * mmToPx,
            fill: 'rgba(0,128,192,0.15)',
            stroke: scientificColors.blue,
            strokeWidth: 2,
            strokeDashArray: [5, 3],
            selectable: true,
            evented: true,
        });

        const label = new (window as any).fabric.Text(`${sizeInMm.width}×${sizeInMm.height}mm`, {
            left: 5,
            top: 5,
            fontSize: 8,
            fontFamily: 'Arial',
            fill: scientificColors.blue,
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
        this.updateStatus(`${size.charAt(0).toUpperCase() + size.slice(1)} reference added (${sizeInMm.width}×${sizeInMm.height}mm)`);
    }
}
