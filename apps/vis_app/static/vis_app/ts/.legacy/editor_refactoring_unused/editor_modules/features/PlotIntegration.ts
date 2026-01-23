/**
 * PlotIntegration - Manages plot gallery and plot insertion
 *
 * Responsibilities:
 * - Setup plot gallery panel
 * - Handle plot selection and insertion
 * - Coordinate plot file uploads
 * - Interface between plot backend and canvas
 *
 * Note: This is a lightweight coordinator. Complex plot rendering
 * logic remains in the main editor until further refactoring.
 */

export interface PlotData {
    type: string;
    data: any;
    options?: any;
}

export class PlotIntegration {
    constructor(
        private canvas: any,
        private onPlotAdd?: (plotData: PlotData) => void,
        private statusCallback?: (message: string) => void
    ) {}

    /**
     * Setup plot gallery panel
     */
    public async setupGalleryPanel(): Promise<void> {
        console.log('[PlotIntegration] Setting up plot gallery panel');

        try {
            // Load plot templates
            const response = await fetch('/static/vis_app/data/plot-templates.json');
            const templates = await response.json();

            const gallery = document.getElementById('plot-gallery');
            if (!gallery) return;

            // Clear existing content
            gallery.innerHTML = '';

            // Create plot thumbnails
            templates.plots.forEach((plot: any) => {
                const item = this.createPlotThumbnail(plot);
                gallery.appendChild(item);
            });

            console.log(`[PlotIntegration] Loaded ${templates.plots.length} plot templates`);
        } catch (error) {
            console.error('[PlotIntegration] Failed to load plot templates:', error);
            if (this.statusCallback) {
                this.statusCallback('Failed to load plot templates');
            }
        }
    }

    /**
     * Setup plot file upload handler
     */
    public setupPlotFileUpload(): void {
        const uploadBtn = document.getElementById('plot-upload-btn');
        const fileInput = document.getElementById('plot-file-input') as HTMLInputElement;

        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                const files = (e.target as HTMLInputElement).files;
                if (files && files.length > 0) {
                    this.handlePlotFileUpload(files[0]);
                }
            });

            console.log('[PlotIntegration] Plot file upload initialized');
        }
    }

    /**
     * Add plot to canvas
     */
    public addPlotToCanvas(plotData: PlotData, plotType: string): void {
        if (!this.canvas) {
            console.error('[PlotIntegration] Canvas not available');
            return;
        }

        console.log(`[PlotIntegration] Adding ${plotType} plot to canvas`);

        if (this.onPlotAdd) {
            this.onPlotAdd(plotData);
        }

        if (this.statusCallback) {
            this.statusCallback(`${plotType} plot added to canvas`);
        }
    }

    /**
     * Update canvas reference
     */
    public setCanvas(canvas: any): void {
        this.canvas = canvas;
    }

    /**
     * Create plot thumbnail element
     */
    private createPlotThumbnail(plot: any): HTMLElement {
        const item = document.createElement('div');
        item.className = 'plot-gallery-item';
        item.dataset.plotType = plot.type;

        // Thumbnail image
        const img = document.createElement('img');
        img.src = plot.thumbnail || '/static/vis_app/images/plot-placeholder.png';
        img.alt = plot.name;
        img.className = 'plot-thumbnail';

        // Plot name label
        const label = document.createElement('div');
        label.className = 'plot-label';
        label.textContent = plot.name;

        item.appendChild(img);
        item.appendChild(label);

        // Click handler
        item.addEventListener('click', () => {
            this.handlePlotSelection(plot);
        });

        // Hover effects
        item.addEventListener('mouseenter', () => {
            item.classList.add('hovered');
        });

        item.addEventListener('mouseleave', () => {
            item.classList.remove('hovered');
        });

        return item;
    }

    /**
     * Handle plot selection from gallery
     */
    private handlePlotSelection(plot: any): void {
        console.log('[PlotIntegration] Plot selected:', plot.type);

        const plotData: PlotData = {
            type: plot.type,
            data: plot.defaultData || {},
            options: plot.defaultOptions || {}
        };

        this.addPlotToCanvas(plotData, plot.name);
    }

    /**
     * Handle plot file upload
     */
    private async handlePlotFileUpload(file: File): Promise<void> {
        console.log('[PlotIntegration] Uploading plot file:', file.name);

        try {
            const formData = new FormData();
            formData.append('plot_file', file);

            const response = await fetch('/vis/api/upload-plot/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result = await response.json();
            console.log('[PlotIntegration] Plot uploaded successfully:', result);

            if (this.statusCallback) {
                this.statusCallback('Plot uploaded successfully');
            }

            // Refresh gallery if needed
            await this.setupGalleryPanel();

        } catch (error) {
            console.error('[PlotIntegration] Plot upload failed:', error);
            if (this.statusCallback) {
                this.statusCallback('Plot upload failed');
            }
        }
    }

    /**
     * Get CSRF token for POST requests
     */
    private getCSRFToken(): string {
        const token = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
        return token ? token.value : '';
    }
}
