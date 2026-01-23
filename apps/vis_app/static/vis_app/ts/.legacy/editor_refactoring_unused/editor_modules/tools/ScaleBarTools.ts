/**
 * Scale Bar Tools
 * Tools for adding scale bars and measurement indicators
 */

import { JournalPreset } from '../types.ts';

export class ScaleBarTools {
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
}
