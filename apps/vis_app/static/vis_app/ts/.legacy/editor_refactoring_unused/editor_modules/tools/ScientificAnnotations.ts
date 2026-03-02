/**
 * Scientific Annotations
 * Coordinates basic and advanced scientific annotation tools
 */

import { JournalPreset } from '../types';
import { BasicAnnotations } from './BasicAnnotations';
import { AdvancedAnnotations } from './AdvancedAnnotations';

export class ScientificAnnotations {
    private basicAnnotations: BasicAnnotations;
    private advancedAnnotations: AdvancedAnnotations;
    private scientificColors: any;

    constructor(
        canvas: any,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            updateStatus: (message: string) => void;
            scientificColors: any;
        }
    ) {
        this.scientificColors = options.scientificColors;
        this.basicAnnotations = new BasicAnnotations(canvas, {
            getCurrentPreset: options.getCurrentPreset,
            updateStatus: options.updateStatus,
        });
        this.advancedAnnotations = new AdvancedAnnotations(canvas, options);
    }

    /**
     * Add significance marker (asterisks)
     */
    public addSignificance(): void {
        this.basicAnnotations.addSignificance();
    }

    /**
     * Add scientific notation symbol
     */
    public addScientificNotation(): void {
        this.basicAnnotations.addScientificNotation();
    }

    /**
     * Add scale bar with label
     */
    public addScaleBar(): void {
        this.basicAnnotations.addScaleBar();
    }

    /**
     * Add overlapping reference rectangles for size comparison
     */
    public addReferenceRectangles(): void {
        this.advancedAnnotations.addReferenceRectangles();
    }

    /**
     * Add column width ruler guides
     */
    public addColumnWidthRuler(): void {
        this.advancedAnnotations.addColumnWidthRuler();
    }

    /**
     * Add reference rectangle for size comparison
     */
    public addReferenceRect(size: 'small' | 'medium' | 'large'): void {
        this.basicAnnotations.addReferenceRect(size, this.scientificColors);
    }

    /**
     * Add column width reference rectangle
     */
    public addColumnReference(type: '0.5' | 'single' | '1.5' | 'double'): void {
        this.advancedAnnotations.addColumnReference(type);
    }
}
