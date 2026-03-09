/**
 * File Export Manager
 * Handles export operations (PNG, TIFF, SVG)
 */

export class FileExport {
    private canvas: any;
    private gridEnabled: boolean;
    private canvasManager: any;
    private updateStatus: (message: string) => void;
    private getCSRFToken: () => string;

    constructor(
        canvas: any,
        options: {
            gridEnabled?: boolean;
            canvasManager?: any;
            updateStatus: (message: string) => void;
            getCSRFToken: () => string;
        }
    ) {
        this.canvas = canvas;
        this.gridEnabled = options.gridEnabled || false;
        this.canvasManager = options.canvasManager;
        this.updateStatus = options.updateStatus;
        this.getCSRFToken = options.getCSRFToken;
    }

    /**
     * Export canvas as PNG with white background
     */
    public exportPNG(): void {
        if (!this.canvas) return;

        // Save current background
        const originalBg = this.canvas.backgroundColor;
        const gridWasEnabled = this.gridEnabled;

        // Force white background for export
        this.canvas.setBackgroundColor('#ffffff', () => {
            if (gridWasEnabled) {
                this.canvasManager?.clearGrid();
            }

            // Export at high quality with WHITE background
            const dataURL = this.canvas!.toDataURL({
                format: 'png',
                quality: 1.0,
                multiplier: 1,
            });

            // Restore original background
            this.canvas!.setBackgroundColor(originalBg as string, () => {
                if (gridWasEnabled) {
                    this.canvasManager?.drawGrid();
                }
                this.canvas!.renderAll();
            });

            // Trigger download
            const link = document.createElement('a');
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            link.download = `figure_${timestamp}.png`;
            link.href = dataURL;
            link.click();

            this.updateStatus('Exported as PNG (white background)');
        });
    }

    /**
     * Export canvas as TIFF (300 DPI)
     */
    public async exportTIFF(): Promise<void> {
        if (!this.canvas) return;

        const originalBg = this.canvas.backgroundColor;
        const gridWasEnabled = this.gridEnabled;

        this.canvas.setBackgroundColor('#ffffff', () => {
            if (gridWasEnabled) {
                this.canvasManager?.clearGrid();
            }

            // Export at actual size (300 DPI already embedded in canvas)
            const dataURL = this.canvas!.toDataURL({
                format: 'png',
                quality: 1.0,
                multiplier: 1,
            });

            // Restore original background
            this.canvas!.setBackgroundColor(originalBg as string, () => {
                if (gridWasEnabled) {
                    this.canvasManager?.drawGrid();
                }
                this.canvas!.renderAll();
            });

            // Convert to TIFF via backend
            this.updateStatus('Converting to TIFF...');
            this.convertPNGtoTIFF(dataURL);
        });
    }

    /**
     * Convert PNG data URL to TIFF via backend
     */
    private async convertPNGtoTIFF(pngDataURL: string): Promise<void> {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            const filename = `figure_${timestamp}_300dpi.tiff`;

            const response = await fetch('/vis/api/convert/png-to-tiff/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    image_data: pngDataURL,
                    filename: filename,
                }),
            });

            if (response.ok) {
                // Download the TIFF file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                link.click();
                window.URL.revokeObjectURL(url);

                this.updateStatus('Exported as TIFF (300 DPI, LZW compression)');
                console.log('[FileExport] TIFF exported successfully');
            } else {
                const errorData = await response.json();
                this.updateStatus(`TIFF export failed: ${errorData.error || 'Unknown error'}`);
                console.error('[FileExport] TIFF conversion failed:', errorData);
            }
        } catch (error) {
            console.error('[FileExport] TIFF conversion error:', error);
            this.updateStatus('Error exporting TIFF');
        }
    }

    /**
     * Export canvas as SVG
     */
    public exportSVG(): void {
        if (!this.canvas) return;

        // Save current background
        const originalBg = this.canvas.backgroundColor;
        const gridWasEnabled = this.gridEnabled;

        // Force white background for export
        this.canvas.setBackgroundColor('#ffffff', () => {
            if (gridWasEnabled) {
                this.canvasManager?.clearGrid();
            }

            const svg = this.canvas!.toSVG();

            // Restore original background
            this.canvas!.setBackgroundColor(originalBg as string, () => {
                if (gridWasEnabled) {
                    this.canvasManager?.drawGrid();
                }
                this.canvas!.renderAll();
            });

            const blob = new Blob([svg], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);

            const link = document.createElement('a');
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            link.download = `figure_${timestamp}.svg`;
            link.href = url;
            link.click();

            URL.revokeObjectURL(url);
            this.updateStatus('Exported as SVG (white background)');
        });
    }

    /**
     * Set grid enabled state
     */
    public setGridEnabled(enabled: boolean): void {
        this.gridEnabled = enabled;
    }
}
