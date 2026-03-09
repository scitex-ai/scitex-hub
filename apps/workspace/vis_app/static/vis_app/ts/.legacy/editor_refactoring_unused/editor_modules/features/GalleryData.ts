/**
 * Gallery Data Manager
 * Handles plot template data loading and filtering
 */

declare const fabric: any;

export class GalleryData {
    private galleryPlotData: any = null;

    // Callbacks for editor integration
    private updateStatusCallback?: (message: string) => void;
    private getCanvasCallback?: () => any;
    private saveHistoryCallback?: () => void;

    constructor(callbacks: {
        updateStatus?: (message: string) => void;
        getCanvas?: () => any;
        saveHistory?: () => void;
    }) {
        this.updateStatusCallback = callbacks.updateStatus;
        this.getCanvasCallback = callbacks.getCanvas;
        this.saveHistoryCallback = callbacks.saveHistory;
    }

    /**
     * Load plot templates JSON from server
     */
    public async loadPlotTemplates(): Promise<any> {
        if (this.galleryPlotData) {
            return this.galleryPlotData;
        }

        try {
            const response = await fetch('/static/vis_app/img/plot_gallery/plot_templates.json');
            if (!response.ok) {
                console.error('[GalleryData] Failed to load plot templates');
                return null;
            }

            this.galleryPlotData = await response.json();
            console.log('[GalleryData] Plot templates loaded');
            return this.galleryPlotData;
        } catch (error) {
            console.error('[GalleryData] Error loading plot templates:', error);
            return null;
        }
    }

    /**
     * Get plot data
     */
    public getPlotData(): any {
        return this.galleryPlotData;
    }

    /**
     * Filter plot types by category
     */
    public filterByCategory(category: string): [string, any][] {
        if (!this.galleryPlotData) return [];

        return Object.entries(this.galleryPlotData.plot_types).filter(
            ([_, data]: [string, any]) => data.category === category
        );
    }

    /**
     * Group plots by base type for dropdowns
     */
    public groupPlotsByType(): Record<string, any[]> {
        if (!this.galleryPlotData) return {};

        const plotGroups: Record<string, any[]> = {
            line: [],
            scatter: [],
            bar: [],
            histogram: [],
            box: [],
            violin: [],
            heatmap: []
        };

        // Categorize all plots
        Object.entries(this.galleryPlotData.plot_types).forEach(([key, plot]: [string, any]) => {
            // Match plot to group based on name/type
            if (key.includes('line') || key.includes('errorbar') || key.includes('shaded')) {
                plotGroups.line.push({ key, ...plot });
            } else if (key.includes('scatter')) {
                plotGroups.scatter.push({ key, ...plot });
            } else if (key.includes('bar') || key.includes('barh')) {
                plotGroups.bar.push({ key, ...plot });
            } else if (key.includes('hist')) {
                plotGroups.histogram.push({ key, ...plot });
            } else if (key.includes('box')) {
                plotGroups.box.push({ key, ...plot });
            } else if (key.includes('violin')) {
                plotGroups.violin.push({ key, ...plot });
            } else if (key.includes('heatmap') || key.includes('imshow') || key.includes('contour')) {
                plotGroups.heatmap.push({ key, ...plot });
            }
        });

        return plotGroups;
    }

    /**
     * Add a plot image to canvas from gallery
     */
    public addPlotToCanvas(plotType: string): void {
        if (!this.galleryPlotData) return;

        const data = this.galleryPlotData.plot_types[plotType];
        const canvas = this.getCanvasCallback?.();
        if (!data || !canvas) return;

        // Get the image URL
        const imgUrl = `/static/vis_app/img/plot_gallery/${data.category}/${data.thumbnail}`;

        // Load image and add to canvas
        fabric.Image.fromURL(imgUrl, (img: any) => {
            const currentCanvas = this.getCanvasCallback?.();
            if (!currentCanvas) return;

            // Scale image to fit canvas nicely (max 500px width)
            const maxWidth = 500;
            if (img.width && img.width > maxWidth) {
                img.scaleToWidth(maxWidth);
            }

            // Center on canvas
            img.set({
                left: (currentCanvas.width || 0) / 2 - (img.getScaledWidth() || 0) / 2,
                top: (currentCanvas.height || 0) / 2 - (img.getScaledHeight() || 0) / 2,
            });

            currentCanvas.add(img);
            currentCanvas.setActiveObject(img);
            currentCanvas.renderAll();
            this.saveHistoryCallback?.();

            this.updateStatusCallback?.(`Added ${data.name} to canvas`);
            console.log(`[GalleryData] Added plot to canvas: ${plotType}`);
        });
    }

    /**
     * Get plot info by type
     */
    public getPlotInfo(plotType: string): any {
        if (!this.galleryPlotData) return null;
        return this.galleryPlotData.plot_types[plotType];
    }
}
