/**
 * Significance Markers
 * Tools for adding statistical significance and scientific notation markers
 */

import { JournalPreset } from '../types';

export class SignificanceMarkers {
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
}
