/**
 * ExportManager - Handles canvas export functionality
 *
 * Responsibilities:
 * - Export canvas as PNG with high quality
 * - Export canvas as SVG (vector format)
 * - Export canvas as PDF (requires jsPDF library)
 *
 * All exports use timestamp-based filenames and clean up resources
 */

export class ExportManager {
    /**
     * Create a new ExportManager
     * @param canvas - Fabric.js canvas instance
     * @param statusCallback - Optional callback for status messages
     */
    constructor(
        private canvas: any,
        private statusCallback?: (message: string) => void
    ) {}

    /**
     * Export canvas as PNG with high quality
     * Uses 2x multiplier for better resolution
     */
    public exportAsPng(): void {
        if (!this.canvas) {
            console.error('[ExportManager] Canvas not available');
            return;
        }

        const dataUrl = this.canvas.toDataURL({
            format: 'png',
            quality: 1,
            multiplier: 2  // 2x resolution for better quality
        });

        const link = document.createElement('a');
        link.download = `figure-${Date.now()}.png`;
        link.href = dataUrl;
        link.click();

        if (this.statusCallback) {
            this.statusCallback('Exported as PNG');
        }

        console.log('[ExportManager] Exported as PNG');
    }

    /**
     * Export canvas as SVG (vector format)
     * SVG preserves scalability for publications
     */
    public exportAsSvg(): void {
        if (!this.canvas) {
            console.error('[ExportManager] Canvas not available');
            return;
        }

        const svg = this.canvas.toSVG();
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.download = `figure-${Date.now()}.svg`;
        link.href = url;
        link.click();

        // Clean up the object URL to prevent memory leaks
        URL.revokeObjectURL(url);

        if (this.statusCallback) {
            this.statusCallback('Exported as SVG');
        }

        console.log('[ExportManager] Exported as SVG');
    }

    /**
     * Export canvas as PDF (requires jsPDF library)
     * PDF dimensions match canvas size for scientific publications
     */
    public exportAsPdf(): void {
        if (!this.canvas) {
            console.error('[ExportManager] Canvas not available');
            return;
        }

        // Check if jsPDF is available
        const jsPDF = (window as any).jspdf?.jsPDF || (window as any).jsPDF;
        if (!jsPDF) {
            console.warn('[ExportManager] jsPDF not available');
            if (this.statusCallback) {
                this.statusCallback('PDF export requires jsPDF library');
            }
            return;
        }

        // Convert canvas to high-quality PNG data URL
        const dataUrl = this.canvas.toDataURL({
            format: 'png',
            quality: 1,
            multiplier: 2  // 2x resolution for better quality
        });

        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();

        // Create PDF with canvas dimensions (in mm)
        // 1px = 0.264583mm at 96 DPI
        const pxToMm = 0.264583;
        const pdfWidth = canvasWidth * pxToMm;
        const pdfHeight = canvasHeight * pxToMm;

        const pdf = new jsPDF({
            orientation: pdfWidth > pdfHeight ? 'landscape' : 'portrait',
            unit: 'mm',
            format: [pdfWidth, pdfHeight]
        });

        pdf.addImage(dataUrl, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save(`figure-${Date.now()}.pdf`);

        if (this.statusCallback) {
            this.statusCallback('Exported as PDF');
        }

        console.log('[ExportManager] Exported as PDF');
    }

    /**
     * Export canvas with custom filename
     * @param filename - Custom filename (without extension)
     * @param format - Export format (png, svg, or pdf)
     */
    public exportWithFilename(filename: string, format: 'png' | 'svg' | 'pdf'): void {
        if (!this.canvas) {
            console.error('[ExportManager] Canvas not available');
            return;
        }

        switch (format) {
            case 'png':
                this.exportAsPngWithFilename(filename);
                break;
            case 'svg':
                this.exportAsSvgWithFilename(filename);
                break;
            case 'pdf':
                this.exportAsPdfWithFilename(filename);
                break;
        }
    }

    /**
     * Export as PNG with custom filename
     */
    private exportAsPngWithFilename(filename: string): void {
        const dataUrl = this.canvas.toDataURL({
            format: 'png',
            quality: 1,
            multiplier: 2
        });

        const link = document.createElement('a');
        link.download = `${filename}.png`;
        link.href = dataUrl;
        link.click();

        if (this.statusCallback) {
            this.statusCallback(`Exported as ${filename}.png`);
        }
    }

    /**
     * Export as SVG with custom filename
     */
    private exportAsSvgWithFilename(filename: string): void {
        const svg = this.canvas.toSVG();
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.download = `${filename}.svg`;
        link.href = url;
        link.click();

        URL.revokeObjectURL(url);

        if (this.statusCallback) {
            this.statusCallback(`Exported as ${filename}.svg`);
        }
    }

    /**
     * Export as PDF with custom filename
     */
    private exportAsPdfWithFilename(filename: string): void {
        const jsPDF = (window as any).jspdf?.jsPDF || (window as any).jsPDF;
        if (!jsPDF) {
            console.warn('[ExportManager] jsPDF not available');
            return;
        }

        const dataUrl = this.canvas.toDataURL({
            format: 'png',
            quality: 1,
            multiplier: 2
        });

        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();

        const pxToMm = 0.264583;
        const pdfWidth = canvasWidth * pxToMm;
        const pdfHeight = canvasHeight * pxToMm;

        const pdf = new jsPDF({
            orientation: pdfWidth > pdfHeight ? 'landscape' : 'portrait',
            unit: 'mm',
            format: [pdfWidth, pdfHeight]
        });

        pdf.addImage(dataUrl, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save(`${filename}.pdf`);

        if (this.statusCallback) {
            this.statusCallback(`Exported as ${filename}.pdf`);
        }
    }
}
